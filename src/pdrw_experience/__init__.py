"""Scientific experience adapter, not a scientific authority."""
from .core import (RecordError, validate_case, validate_lesson, review_lesson,
                   retrieve_guidance, validate_feedback)
from .mirror_adapter import load_mirror, preview_mirror, convert_mirror

__version__ = "0.2.0a1"
__all__ = [
    "RecordError", "validate_case", "validate_lesson", "review_lesson",
    "retrieve_guidance", "validate_feedback", "load_mirror",
    "preview_mirror", "convert_mirror",
]
