"""Second Brain domain package.

The package intentionally keeps AI/RAG correctness in deterministic, testable
domain code. FastAPI is only an optional transport adapter.
"""

from .models import DEFAULT_OWNER_ID
from .service import SecondBrainService

__all__ = ["DEFAULT_OWNER_ID", "SecondBrainService"]

