"""Scientific experience adaptation. Not a scientific authority."""
from .core import (RecordError, validate_case, validate_lesson, review_lesson,
                   retrieve_guidance, validate_feedback)

__version__ = "0.1.0"
__all__ = ["RecordError", "validate_case", "validate_lesson",
           "review_lesson", "retrieve_guidance", "validate_feedback"]
