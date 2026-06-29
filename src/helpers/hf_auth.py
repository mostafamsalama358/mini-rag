import logging
import os

logger = logging.getLogger(__name__)
_configured = False


def configure_hf_from_settings(settings) -> None:
    global _configured
    if _configured:
        return

    hf_home = getattr(settings, "HF_HOME", None)
    if hf_home:
        os.environ.setdefault("HF_HOME", hf_home)

    token = getattr(settings, "HF_TOKEN", None)
    if token:
        os.environ["HF_TOKEN"] = token
        try:
            from huggingface_hub import login

            login(token=token, add_to_git_credential=False)
            logger.info("Hugging Face authentication configured")
        except Exception as exc:
            logger.warning("Hugging Face login failed: %s", exc)
    else:
        logger.warning(
            "HF_TOKEN is not set; model downloads may be slower or rate-limited"
        )

    _configured = True
