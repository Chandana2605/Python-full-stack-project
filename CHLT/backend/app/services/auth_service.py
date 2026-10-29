from datetime import datetime, timezone

from bson import ObjectId

from ..core.security import create_access_token, get_password_hash, verify_password
from ..exceptions.http_exceptions import bad_request_exception, unauthorized_exception
from ..models.user import LoginRequest, LoginResponse, PasswordChangeRequest, UserOut
from .user_service import serialize_document
from ..utils.password import validate_password_strength


class AuthService:
    def __init__(self, db):
        self.db = db

    async def login(self, email: str, password: str) -> LoginResponse:
        user = await self.db.users.find_one({"email": email.lower()})
        if not user or not user.get("is_active", True):
            raise unauthorized_exception("Invalid credentials")
        if not verify_password(password, user["password_hash"]):
            raise unauthorized_exception("Invalid credentials")

        token = create_access_token(subject=str(user["_id"]), role=user["role"])
        return LoginResponse(
            access_token=token,
            role=user["role"],
            must_change_password=user["force_password_change"],
            user=UserOut(**serialize_document(user)),
        )

    async def change_password(self, user_id: str, payload: PasswordChangeRequest) -> dict:
        user = await self.db.users.find_one({"_id": self._oid(user_id)})
        if not user:
            raise unauthorized_exception("User not found")
        if not verify_password(payload.current_password, user["password_hash"]):
            raise bad_request_exception("Current password is incorrect")

        validate_password_strength(payload.new_password)
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "password_hash": get_password_hash(payload.new_password),
                    "force_password_change": False,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return {"message": "Password updated successfully"}

    @staticmethod
    def _oid(value: str) -> ObjectId:
        try:
            return ObjectId(value)
        except Exception as exc:
            raise bad_request_exception("Invalid identifier") from exc
