"""Domain-level errors for the Phase 2 Training Core."""


class TrainingCoreError(Exception):
    """Base class for deterministic Training Core failures."""


class DuplicateIdentifierError(TrainingCoreError):
    """Raised when a catalog contains the same identifier more than once."""


class MissingReferenceError(TrainingCoreError):
    """Raised when a module references a Case absent from the Case catalog."""


class EvidenceNotFoundError(TrainingCoreError):
    """Raised when a requested Evidence ID is not present in the Session Case."""
