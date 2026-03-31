class APIError(Exception):
    status_code = 400
    code = "api_error"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code or self.status_code
        self.code = code or self.code
        self.details = details or {}

    def to_dict(self) -> dict:
        payload = {"error": self.message, "code": self.code}
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(APIError):
    status_code = 400
    code = "validation_error"


class AuthenticationError(APIError):
    status_code = 401
    code = "authentication_required"


class AuthorizationError(APIError):
    status_code = 403
    code = "forbidden"


class NotFoundError(APIError):
    status_code = 404
    code = "not_found"


class ConflictError(APIError):
    status_code = 409
    code = "conflict"


class ServiceUnavailableError(APIError):
    status_code = 503
    code = "service_unavailable"
