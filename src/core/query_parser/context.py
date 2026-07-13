"""Build ConversationContext from chat history."""
from __future__ import annotations

from typing import Any

from .schema import ConversationContext, QueryPlan, TurnSummary


def _plan_from_metadata(content: dict[str, Any] | None) -> QueryPlan | None:
    if not isinstance(content, dict):
        return None
    raw = content.get("query_plan")
    if not isinstance(raw, dict):
        return None
    try:
        return QueryPlan.model_validate(raw)
    except Exception:
        return None


def build_conversation_context(
    *,
    domain_key: str,
    document_language: str,
    chat_messages: list[Any] | None,
    context_turn_window: int = 4,
) -> ConversationContext:
    """Extract current_entity and recent turns from prior parse metadata."""
    turns: list[TurnSummary] = []
    current_entity: str | None = None

    messages = list(chat_messages or [])
    user_assistant_pairs: list[tuple[Any, Any | None]] = []
    pending_user = None
    for message in messages:
        role = getattr(message, "role", None) or (message.get("role") if isinstance(message, dict) else None)
        content = getattr(message, "content", None) or (message.get("content") if isinstance(message, dict) else None)
        if not isinstance(content, dict):
            content = {"text": str(content or "")}
        if role and str(role).lower() in {"user", "human"}:
            pending_user = content
        elif role and str(role).lower() in {"assistant", "ai", "bot"} and pending_user is not None:
            user_assistant_pairs.append((pending_user, content))
            pending_user = None

    if pending_user is not None:
        user_assistant_pairs.append((pending_user, None))

    for user_content, assistant_content in user_assistant_pairs[-context_turn_window:]:
        user_text = str(user_content.get("text") or "")
        canonical_query = None
        query_plan = None
        if isinstance(assistant_content, dict):
            canonical_query = assistant_content.get("canonical_query")
            query_plan = _plan_from_metadata(assistant_content)
        turns.append(
            TurnSummary(
                user_text=user_text,
                canonical_query=canonical_query,
                query_plan=query_plan,
            )
        )
        if query_plan and query_plan.entity and not query_plan.needs_clarification:
            current_entity = query_plan.entity

    return ConversationContext(
        current_entity=current_entity,
        recent_turns=turns,
        document_language=document_language,
        project_domain=domain_key,
    )
