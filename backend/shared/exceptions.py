class BAAcceleratorException(Exception):
    """Base exception for all system-related errors."""
    pass

class LowConfidenceError(BAAcceleratorException):
    """Raised when an LLM agent generates output below the confidence threshold."""
    def __init__(self, message: str, confidence_score: float):
        super().__init__(message)
        self.confidence_score = confidence_score

class MaxRetriesError(BAAcceleratorException):
    """Raised when the agent pipeline exceeds the maximum allowable iterations for retry logic."""
    pass

class TemplateNotFoundError(BAAcceleratorException):
    """Raised when a specified Jinja prompt template is missing."""
    pass

class ConnectorAuthError(BAAcceleratorException):
    """Raised when credential validation fails for third-party ingestion source connectors."""
    pass

class ExportError(BAAcceleratorException):
    """Raised when output generation or push to third-party endpoints fails."""
    pass

# INTEGRATION NOTE
# All custom exceptions are centralized here to allow components to handle exceptions safely
# without creating circular dependencies. Do not import connector logic or LLM classes here.
