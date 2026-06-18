"""Cortex AI service package.

The package intentionally keeps AI/RAG correctness in deterministic, testable
domain code. FastAPI is only an optional transport adapter.
"""

from .core.models import DEFAULT_OWNER_ID
from .secondbrain.service import SecondBrainService

__all__ = ["DEFAULT_OWNER_ID", "SecondBrainService"]
