"""
services/FieldRegistry.py — Field Pack Loader & Profile Builder
================================================================
.NET Equivalent: a singleton IFieldRegistry service.

Loads YAML field packs from `src/fields/{domain_key}/` once at startup
, validates them against Pydantic schemas (NFR-005), and builds a
runtime `FieldProfile` by merging:

    generic pack (base)  ⊎  domain pack  ⊎  project.config_json (DB snapshot)

Runtime NEVER re-reads YAML per request — the DB snapshot
(`projects.config_json`) is the source of truth at request time (FR-005).

"""
from __future__ import annotations

import logging
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from models.enums.DomainKeyEnum import DomainKeyEnum
from core.context_builder.config import (
    ContextBuilderConfig,
    resolve_context_builder_config,
)
from fields.schemas import (
    ChunkingProfile,
    DomainMeta,
    FieldRegistryProfile,
    MetadataProfile,
    ParserProfile,
    ProjectDefaults,
    PromptBundle,
    RetrievalProfile,
    StructuralProfile,
)

logger = logging.getLogger("uvicorn.error")

_FIELDS_DIR = Path(__file__).resolve().parent.parent / "fields"

# Module file names required/optional per pack (contract field-registry-api.md).
_REQUIRED_MODULES = ("domain", "chunking", "retrieval", "chunk_metadata")
_OPTIONAL_MODULES = ("structural_split",)
# fields.yaml is optional: generic packs ship an empty no-op profile, and the
# field-aware retrieval path simply resolves no concept when absent.
_FIELDS_FILE = "fields.yaml"
_PROJECT_DEFAULTS_FILE = "project.defaults.yaml"
_PROJECT_USERS_FILE = "project_users.yaml"
_PROMPTS_SUBDIR = "prompts"
_CONFIG_JSON_MAX_BYTES = 32 * 1024


@dataclass(frozen=True)
class FieldPack:
    """A loaded, validated field pack (immutable runtime view)."""

    key: str
    label: str
    languages: list[str]
    chunking: ChunkingProfile
    retrieval: RetrievalProfile
    structural: StructuralProfile
    metadata: MetadataProfile
    project_defaults: dict[str, Any]
    prompts: PromptBundle
    parser: ParserProfile = field(default_factory=ParserProfile)
    field_registry: FieldRegistryProfile = field(default_factory=FieldRegistryProfile)


@dataclass
class FieldProfile:
    """Merged runtime view passed to the core pipeline.

    Precedence (spec FR-009): generic < domain pack < project.config_json.
    Prompt text overrides are resolved separately against project_prompts.
    """

    domain_key: str
    chunking: ChunkingProfile
    retrieval: RetrievalProfile
    structural: StructuralProfile
    metadata: MetadataProfile
    config: dict[str, Any] = field(default_factory=dict)
    prompts: PromptBundle = field(default_factory=PromptBundle)
    parser_profile: ParserProfile = field(default_factory=ParserProfile)
    field_registry: FieldRegistryProfile = field(default_factory=FieldRegistryProfile)
    _compiled_structural_patterns: Any = None

    def chunking_strategy_for(self, file_ext: str) -> str:
        return self.chunking.for_extension(file_ext)

    @property
    def structural_patterns(self):
        """Lazy-compiled StructuralPatterns from this profile's structural_split YAML."""
        from core.structural.engine import compile_structural_patterns

        if self._compiled_structural_patterns is None:
            self._compiled_structural_patterns = compile_structural_patterns(self.structural)
        return self._compiled_structural_patterns

    @property
    def is_exhaustive(self) -> bool:
        return False


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    """Recursive dict merge; override wins. Lists are replaced, not concatenated."""
    if not override:
        return deepcopy(base)
    merged = deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


class FieldRegistry:
    """Singleton registry of loaded field packs.

    Instantiate once in `main.py` startup (like `get_settings`). Cached in
    memory; reload only when explicitly requested.
    """

    def __init__(self, fields_dir: Path | None = None) -> None:
        self._fields_dir = Path(fields_dir) if fields_dir else _FIELDS_DIR
        self._packs: dict[str, FieldPack] = {}
        self._registry_meta: dict[str, dict[str, Any]] = {}
        self._default_key: str = DomainKeyEnum.GENERIC.value
        self._project_users: dict[str, list[str]] = {}
        self._lock = threading.Lock()
        self._loaded = False

    # ---- loading ----

    def load(self) -> "FieldRegistry":
        """Load registry.yaml + all packs. Idempotent and thread-safe."""
        with self._lock:
            if self._loaded:
                return self
            self._load_registry_file()
            for key in self._registry_meta:
                self._packs[key] = self._load_pack(key)
            self.load_project_users()
            self._loaded = True
            logger.info(
                "FieldRegistry loaded %d packs: %s",
                len(self._packs),
                ", ".join(sorted(self._packs)),
            )
            return self

    def reload(self) -> "FieldRegistry":
        """Force a full reload (dev helper; not on the hot path)."""
        with self._lock:
            self._packs.clear()
            self._registry_meta.clear()
            self._loaded = False
        return self.load()

    def _load_registry_file(self) -> None:
        registry_path = self._fields_dir / "registry.yaml"
        if not registry_path.exists():
            raise FileNotFoundError(f"Field registry file not found: {registry_path}")

        with registry_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        self._default_key = str(data.get("default", DomainKeyEnum.GENERIC.value))
        fields = data.get("fields") or []
        if not fields:
            raise ValueError("registry.yaml declares no fields")

        for entry in fields:
            key = str(entry.get("key", "")).strip().lower()
            if not key:
                raise ValueError("registry.yaml entry missing 'key'")
            self._registry_meta[key] = {
                "label": str(entry.get("label", key)),
            }

        # Validate registry keys ⊆ enum.
        enum_values = set(DomainKeyEnum.values())
        unknown = set(self._registry_meta) - enum_values
        if unknown:
            raise ValueError(
                f"registry.yaml references unknown domain keys not in DomainKeyEnum: {sorted(unknown)}"
            )

        if self._default_key not in self._registry_meta:
            raise ValueError(
                f"registry default '{self._default_key}' is not a registered field"
            )

    def _load_pack(self, key: str) -> FieldPack:
        pack_dir = self._fields_dir / key
        if not pack_dir.is_dir():
            raise FileNotFoundError(f"Field pack directory missing: {pack_dir}")

        domain = self._load_yaml_model(pack_dir / "domain.yaml", DomainMeta)
        if domain.key != key:
            raise ValueError(
                f"Pack '{key}' domain.yaml declares key='{domain.key}' (mismatch)"
            )

        chunking = self._load_yaml_model(pack_dir / "chunking.yaml", ChunkingProfile)
        retrieval = self._load_yaml_model(pack_dir / "retrieval.yaml", RetrievalProfile)
        metadata = self._load_yaml_model(pack_dir / "chunk_metadata.yaml", MetadataProfile)

        structural = StructuralProfile()
        structural_path = pack_dir / "structural_split.yaml"
        if structural_path.exists():
            structural = self._load_yaml_model(structural_path, StructuralProfile)

        project_defaults = self._load_project_defaults(pack_dir)
        prompts = self._load_prompts(pack_dir)
        parser = self._load_parser(pack_dir)
        field_registry = self._load_field_registry(pack_dir)

        return FieldPack(
            key=key,
            label=domain.label or self._registry_meta.get(key, {}).get("label", key),
            languages=list(domain.languages),
            chunking=chunking,
            retrieval=retrieval,
            structural=structural,
            metadata=metadata,
            project_defaults=project_defaults,
            prompts=prompts,
            parser=parser,
            field_registry=field_registry,
        )

    @staticmethod
    def _load_yaml_model(path: Path, model_cls: type) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Required field module missing: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return model_cls.model_validate(data)

    @staticmethod
    def _load_project_defaults(pack_dir: Path) -> dict[str, Any]:
        path = pack_dir / _PROJECT_DEFAULTS_FILE
        if not path.exists():
            return {"version": 1}
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        ProjectDefaults.model_validate(data)  # validate, allow extra keys
        return data

    @staticmethod
    def _load_prompts(pack_dir: Path) -> PromptBundle:
        prompts_dir = pack_dir / _PROMPTS_SUBDIR
        prompts: dict[str, str] = {}
        welcomes: dict[str, str] = {}
        if not prompts_dir.is_dir():
            return PromptBundle(prompts=prompts, welcomes=welcomes)
        for path in sorted(prompts_dir.glob("system_*.txt")):
            # system_ar.txt → "ar"
            stem = path.stem
            lang = stem.replace("system_", "", 1).lower()[:2]
            if lang:
                prompts[lang] = path.read_text(encoding="utf-8")
        for path in sorted(prompts_dir.glob("welcome_*.txt")):
            lang = path.stem.replace("welcome_", "", 1).lower()[:2]
            if lang:
                welcomes[lang] = path.read_text(encoding="utf-8").strip()
        return PromptBundle(prompts=prompts, welcomes=welcomes)

    @staticmethod
    def _load_parser(pack_dir: Path) -> ParserProfile:
        path = pack_dir / "parser.yaml"
        if not path.exists():
            return ParserProfile()
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return ParserProfile.model_validate(data)

    @staticmethod
    def _load_field_registry(pack_dir: Path) -> FieldRegistryProfile:
        """Load fields.yaml → FieldRegistryProfile (optional; empty = no-op)."""
        path = pack_dir / _FIELDS_FILE
        if not path.exists():
            return FieldRegistryProfile()
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return FieldRegistryProfile.model_validate(data)

    # ---- public API ----

    @property
    def default_key(self) -> str:
        return self._default_key

    def list_fields(self) -> list[dict[str, str]]:
        """Return registered field summaries (for `available_domains` in API)."""
        return [
            {"key": key, "label": self._registry_meta.get(key, {}).get("label", key)}
            for key in self._registry_meta
        ]

    def get_pack(self, domain_key: str | DomainKeyEnum) -> FieldPack:
        if not self._loaded:
            self.load()
        key = domain_key.value if isinstance(domain_key, DomainKeyEnum) else str(domain_key)
        pack = self._packs.get(key)
        if pack is not None:
            return pack
        logger.warning("Unknown domain_key '%s' — falling back to '%s'", key, self._default_key)
        return self._packs[self._default_key]

    def load_project_defaults(self, domain_key: str | DomainKeyEnum) -> dict[str, Any]:
        """Read `fields/{domain}/project.defaults.yaml` → dict."""
        return deepcopy(self.get_pack(domain_key).project_defaults)

    def load_context_builder_config(
        self,
        domain_key: str | DomainKeyEnum,
        project_overrides: dict[str, Any] | None = None,
    ) -> ContextBuilderConfig:
        """Resolve Context Builder config: generic < domain < project.config_json."""
        key = domain_key.value if isinstance(domain_key, DomainKeyEnum) else str(domain_key)
        overrides = _deep_merge(
            self.get_pack(self._default_key).project_defaults,
            self.get_pack(key).project_defaults,
        )
        if project_overrides:
            overrides = _deep_merge(overrides, project_overrides)
        return resolve_context_builder_config(key, overrides)

    def load_project_users(self) -> dict[str, list[str]]:
        """Load and validate `fields/project_users.yaml`.

        Returns a mapping of user_id → list of domain_keys.
        Validates that every domain_key is a registered field pack key.
        """
        path = self._fields_dir / _PROJECT_USERS_FILE
        if not path.exists():
            logger.warning("project_users.yaml not found — no user-project assignments")
            return {}

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        users = data.get("users") or {}
        if not isinstance(users, dict):
            raise ValueError("project_users.yaml: 'users' must be a dict")

        enum_values = set(DomainKeyEnum.values())
        result: dict[str, list[str]] = {}
        for user_id, domains in users.items():
            if not isinstance(domains, list):
                raise ValueError(
                    f"project_users.yaml: user '{user_id}' must map to a list of domain keys"
                )
            for dk in domains:
                dk_str = str(dk)
                if dk_str not in enum_values:
                    raise ValueError(
                        f"project_users.yaml: unknown domain_key '{dk_str}' for user '{user_id}'"
                    )
            result[str(user_id)] = [str(d) for d in domains]

        self._project_users = result
        logger.info(
            "project_users loaded: %d users, domains=%s",
            len(result),
            {uid: dks for uid, dks in result.items()},
        )
        return result

    def get_user_domains(self, user_id: str) -> list[str]:
        """Return the list of domain_keys assigned to a user from project_users.yaml.

        Returns an empty list if the user has no assignments.
        """
        return list(self._project_users.get(user_id, []))

    def get_domain_user_ids(self, domain_key: str) -> list[str]:
        """Return all user_ids assigned to a given domain_key from project_users.yaml."""
        return [
            uid for uid, domains in self._project_users.items()
            if domain_key in domains
        ]

    def build_profile(
        self,
        domain_key: str | DomainKeyEnum,
        project_overrides: dict[str, Any] | None = None,
        *,
        language: str = "en",
        prompt_text: str | None = None,
    ) -> FieldProfile:
        """Merge generic + domain pack + project.config_json overrides.

        Precedence (FR-009): generic < domain < project.config_json.
        """
        domain = self.get_pack(domain_key)
        generic = self.get_pack(self._default_key)

        # Per-module deep merge so project overrides only win on conflicting keys.
        chunking = self._merge_chunking(generic, domain, project_overrides)
        retrieval = self._merge_retrieval(generic, domain, project_overrides)
        structural = self._merge_structural(generic, domain, project_overrides)
        metadata = domain.metadata or generic.metadata
        config = _deep_merge(domain.project_defaults, project_overrides or None)

        # Prompt bundle: project_prompts override wins over pack default.
        prompts = PromptBundle(
            prompts=dict(domain.prompts.prompts),
            welcomes=dict(domain.prompts.welcomes),
        )
        if prompt_text:
            prompts.prompts[language.lower()[:2]] = prompt_text

        field_registry = self._merge_field_registry(generic, domain, project_overrides)

        parser_profile = self._merge_parser(generic, domain, project_overrides)
        if not parser_profile.allowed_fields:
            parser_profile = parser_profile.model_copy(
                update={"allowed_fields": [c.concept for c in field_registry.concepts]}
            )

        return FieldProfile(
            domain_key=domain.key,
            chunking=chunking,
            retrieval=retrieval,
            structural=structural,
            metadata=metadata,
            config=config,
            prompts=prompts,
            parser_profile=parser_profile,
            field_registry=field_registry,
        )

    def _merge_field_registry(
        self,
        generic: FieldPack,
        domain: FieldPack,
        overrides: dict[str, Any] | None,
    ) -> FieldRegistryProfile:
        """Merge generic < domain < project.config_json field_registry.

        Generic packs declare no concepts; domain packs declare the full
        synonym map. A project may override (e.g. add a concept, change the
        entity hint) via projects.config_json["retrieval"]["field_registry"].
        """
        merged = _deep_merge(
            generic.field_registry.model_dump(),
            domain.field_registry.model_dump(),
        )
        if overrides and isinstance(overrides.get("retrieval"), dict):
            retrieval_override = overrides["retrieval"]
            if isinstance(retrieval_override.get("field_registry"), dict):
                merged = _deep_merge(
                    merged, retrieval_override["field_registry"]
                )
        return FieldRegistryProfile.model_validate(merged)

    def _merge_parser(
        self,
        generic: FieldPack,
        domain: FieldPack,
        overrides: dict[str, Any] | None,
    ) -> ParserProfile:
        merged = _deep_merge(
            generic.parser.model_dump(),
            domain.parser.model_dump(),
        )
        if overrides and isinstance(overrides.get("parser"), dict):
            merged = _deep_merge(merged, overrides["parser"])
        return ParserProfile.model_validate(merged)

    # ---- per-module merge helpers ----

    def _merge_chunking(
        self,
        generic: FieldPack,
        domain: FieldPack,
        overrides: dict[str, Any] | None,
    ) -> ChunkingProfile:
        merged = _deep_merge(
            generic.chunking.model_dump(),
            domain.chunking.model_dump(),
        )
        if overrides and isinstance(overrides.get("chunking"), dict):
            merged = _deep_merge(merged, overrides["chunking"])
        return ChunkingProfile.model_validate(merged)

    def _merge_retrieval(
        self,
        generic: FieldPack,
        domain: FieldPack,
        overrides: dict[str, Any] | None,
    ) -> RetrievalProfile:
        merged = _deep_merge(
            generic.retrieval.model_dump(),
            domain.retrieval.model_dump(),
        )
        if overrides and isinstance(overrides.get("retrieval"), dict):
            merged = _deep_merge(merged, overrides["retrieval"])
        return RetrievalProfile.model_validate(merged)

    def _merge_structural(
        self,
        generic: FieldPack,
        domain: FieldPack,
        overrides: dict[str, Any] | None,
    ) -> StructuralProfile:
        merged = _deep_merge(
            generic.structural.model_dump(),
            domain.structural.model_dump(),
        )
        if overrides and isinstance(overrides.get("structural_split"), dict):
            merged = _deep_merge(merged, overrides["structural_split"])
        return StructuralProfile.model_validate(merged)


# ---- module-level singleton (mirrors helpers/config.get_settings) ----

_registry_instance: FieldRegistry | None = None


def get_field_registry() -> FieldRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FieldRegistry().load()
    return _registry_instance


def validate_config_json_size(config_json: Any) -> None:
    """Enforce the 32KB config_json cap (data-model.md rule 2)."""
    import json

    encoded = json.dumps(config_json or {}, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > _CONFIG_JSON_MAX_BYTES:
        raise ValueError(
            f"config_json exceeds {_CONFIG_JSON_MAX_BYTES} bytes "
            f"({len(encoded.encode('utf-8'))} bytes)"
        )
