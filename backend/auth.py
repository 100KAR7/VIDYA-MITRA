from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.errors import AuthenticationError


class AuthManager:
    def __init__(self, secret_key: str, salt: str = "vidya-mitra-auth"):
        self.serializer = URLSafeTimedSerializer(secret_key=secret_key, salt=salt)

    def issue_token(self, user: dict) -> str:
        payload = {
            "user_id": user["user_id"],
            "display_name": user["display_name"],
            "role": user["role"],
        }
        return self.serializer.dumps(payload)

    def verify_token(self, token: str, max_age_seconds: int) -> dict:
        try:
            payload = self.serializer.loads(token, max_age=max_age_seconds)
        except SignatureExpired as exc:
            raise AuthenticationError("Your session expired. Please sign in again.") from exc
        except BadSignature as exc:
            raise AuthenticationError("Access token is invalid.") from exc

        if not isinstance(payload, dict) or "user_id" not in payload or "role" not in payload:
            raise AuthenticationError("Access token payload is invalid.")
        return payload
