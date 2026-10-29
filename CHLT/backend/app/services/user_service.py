from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..core.security import get_password_hash
from ..exceptions.http_exceptions import bad_request_exception, conflict_exception, not_found_exception
from ..models.user import UserCreate, UserOut, UserProvisionResponse, UserUpdate
from .email_service import EmailService
from ..utils.password import validate_password_strength


def serialize_document(document: dict) -> dict:
    serialized = {}
    for key, value in document.items():
        if isinstance(value, ObjectId):
            serialized["id" if key == "_id" else key] = str(value)
        else:
            serialized[key] = value
    return serialized


class UserService:
    def __init__(self, db):
        self.db = db
        self.email_service = EmailService()

    async def create_user_record(self, payload: UserCreate, created_by: str) -> UserOut:
        if payload.role == "admin":
            raise bad_request_exception("Admin users are seeded through configuration only")

        validate_password_strength(payload.temporary_password)
        now = datetime.now(timezone.utc)
        document = {
            "name": payload.name,
            "email": payload.email.lower(),
            "employee_id": payload.employee_id,
            "role": payload.role,
            "password_hash": get_password_hash(payload.temporary_password),
            "force_password_change": True,
            "is_active": True,
            "invitation_email_sent": False,
            "invitation_sent_at": None,
            "invitation_last_attempt_at": None,
            "invitation_last_error": None,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.db.users.insert_one(document)
        except DuplicateKeyError as exc:
            raise conflict_exception("User with same email or employee ID already exists") from exc

        created = await self.db.users.find_one({"_id": result.inserted_id})
        await self.db.audit_logs.insert_one(
            {
                "entity_type": "user",
                "entity_id": str(created["_id"]),
                "action": "user_created",
                "message": f"User created with role {created['role']}.",
                "created_by": created_by,
                "created_at": now,
            }
        )
        return UserOut(**serialize_document(created))

    async def send_invitation_for_user(
        self,
        *,
        user_id: str,
        temporary_password: str,
        triggered_by: str,
        action: str,
    ) -> UserProvisionResponse:
        validate_password_strength(temporary_password)
        user = await self.db.users.find_one({"_id": self._oid(user_id)})
        if not user:
            raise not_found_exception("User not found")
        if user["role"] == "admin":
            raise bad_request_exception("Admin invitation email is not supported through this endpoint")

        if action == "invitation_resent":
            now = datetime.now(timezone.utc)
            await self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "password_hash": get_password_hash(temporary_password),
                        "force_password_change": True,
                        "invitation_email_sent": False,
                        "invitation_sent_at": None,
                        "invitation_last_error": None,
                        "updated_at": now,
                    }
                },
            )
            user = await self.db.users.find_one({"_id": user["_id"]})

        invitation_status, user_out = await self._trigger_invitation(
            user_document=user,
            temporary_password=temporary_password,
            triggered_by=triggered_by,
            action=action,
        )
        return UserProvisionResponse(
            user=user_out,
            invitation_email_sent=invitation_status["sent"],
            invitation_message=invitation_status["message"],
        )

    async def create_user(self, payload: UserCreate, created_by: str) -> UserProvisionResponse:
        user = await self.create_user_record(payload, created_by)
        return await self.send_invitation_for_user(
            user_id=user.id,
            temporary_password=payload.temporary_password,
            triggered_by=created_by,
            action="user_created",
        )

    async def list_users(self) -> list[UserOut]:
        users = await self.db.users.find().sort("created_at", -1).to_list(length=500)
        return [UserOut(**serialize_document(user)) for user in users]

    async def update_user(self, user_id: str, payload: UserUpdate) -> UserOut:
        update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
        if not update_data:
            raise bad_request_exception("No update fields provided")

        update_data["updated_at"] = datetime.now(timezone.utc)
        result = await self.db.users.update_one({"_id": self._oid(user_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise not_found_exception("User not found")

        updated = await self.db.users.find_one({"_id": self._oid(user_id)})
        return UserOut(**serialize_document(updated))

    async def resend_invitation(self, user_id: str, temporary_password: str, triggered_by: str) -> UserProvisionResponse:
        return await self.send_invitation_for_user(
            user_id=user_id,
            temporary_password=temporary_password,
            triggered_by=triggered_by,
            action="invitation_resent",
        )

    async def test_email_connection(self, recipient_email: str, triggered_by: str) -> dict:
        now = datetime.now(timezone.utc)
        email_status = await self.email_service.send_test_email(recipient_email)
        await self.db.audit_logs.insert_one(
            {
                "entity_type": "email",
                "entity_id": recipient_email,
                "action": "smtp_test",
                "message": email_status["message"],
                "created_by": triggered_by,
                "created_at": now,
            }
        )
        return {
            "connection_ok": email_status["sent"],
            "email_sent": email_status["sent"],
            "message": email_status["message"],
        }

    @staticmethod
    def _oid(value: str) -> ObjectId:
        try:
            return ObjectId(value)
        except Exception as exc:
            raise bad_request_exception("Invalid identifier") from exc

    @staticmethod
    def _role_label(role: str) -> str:
        mapping = {
            "admin": "L&D Manager",
            "batch_owner": "Batch Owner",
            "program_manager": "Program Manager",
        }
        return mapping.get(role, role)

    async def _trigger_invitation(
        self,
        *,
        user_document: dict,
        temporary_password: str,
        triggered_by: str,
        action: str,
    ) -> tuple[dict, UserOut]:
        now = datetime.now(timezone.utc)
        invitation_status = await self.email_service.send_user_invitation(
            recipient_name=user_document["name"],
            recipient_email=user_document["email"],
            temporary_password=temporary_password,
            role_label=self._role_label(user_document["role"]),
        )
        update_data = {
            "invitation_email_sent": invitation_status["sent"],
            "invitation_last_attempt_at": now,
            "invitation_last_error": None if invitation_status["sent"] else invitation_status["message"],
            "updated_at": now,
        }
        if invitation_status["sent"]:
            update_data["invitation_sent_at"] = now

        await self.db.users.update_one({"_id": user_document["_id"]}, {"$set": update_data})
        refreshed = await self.db.users.find_one({"_id": user_document["_id"]})
        user = UserOut(**serialize_document(refreshed))
        await self.db.audit_logs.insert_one(
            {
                "entity_type": "user",
                "entity_id": user.id,
                "action": action,
                "message": invitation_status["message"],
                "created_by": triggered_by,
                "created_at": now,
            }
        )
        return invitation_status, user
