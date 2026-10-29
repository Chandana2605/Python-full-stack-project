from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from ...core.security import decode_token
from ...db.mongo import get_database
from ...exceptions.http_exceptions import bad_request_exception, forbidden_exception, unauthorized_exception
from ...models.candidate import CandidateOut
from ...models.user import ResendInvitationRequest, UserCreate, UserOut, UserProvisionResponse, UserUpdate
from ...services.auth_service import AuthService
from ...services.user_service import UserService, serialize_document
from ...utils.excel_parser import parse_excel_file

router = APIRouter(prefix="/users", tags=["Users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_service() -> UserService:
    return UserService(get_database())


def get_auth_service() -> AuthService:
    return AuthService(get_database())


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
    except (JWTError, KeyError) as exc:
        raise unauthorized_exception("Invalid or expired token") from exc

    user = await get_database().users.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("is_active", True):
        raise unauthorized_exception("User is inactive or missing")
    return serialize_document(user)


def require_roles(*roles: str):
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise forbidden_exception("You do not have permission to access this resource")
        return current_user

    return dependency


@router.post("", response_model=UserProvisionResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: dict = Depends(require_roles("admin")),
    service: UserService = Depends(get_user_service),
) -> UserProvisionResponse:
    user = await service.create_user_record(payload, current_user["id"])
    return await service.send_invitation_for_user(
        user_id=user.id,
        temporary_password=payload.temporary_password,
        triggered_by=current_user["id"],
        action="user_created",
    )


@router.get("", response_model=list[UserOut])
async def list_users(
    _: dict = Depends(require_roles("admin")),
    service: UserService = Depends(get_user_service),
) -> list[UserOut]:
    return await service.list_users()


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _: dict = Depends(require_roles("admin")),
    service: UserService = Depends(get_user_service),
) -> UserOut:
    return await service.update_user(user_id, payload)


@router.post("/{user_id}/resend-invitation", response_model=UserProvisionResponse)
async def resend_user_invitation(
    user_id: str,
    payload: ResendInvitationRequest,
    current_user: dict = Depends(require_roles("admin")),
    service: UserService = Depends(get_user_service),
) -> UserProvisionResponse:
    return await service.resend_invitation(user_id, payload.temporary_password, current_user["id"])


@router.post("/master-database/upload", response_model=list[CandidateOut], status_code=status.HTTP_201_CREATED)
async def upload_master_database(
    year: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("admin")),
) -> list[CandidateOut]:
    records = parse_excel_file(await file.read(), ["name", "college", "email", "percentage"])
    db = get_database()
    now = datetime.now(timezone.utc)
    created_candidates: list[CandidateOut] = []

    for row in records:
        email = (row.get("email") or "").strip().lower()
        if not email:
            raise bad_request_exception("Candidate email is required in master upload")
        document = {
            "year": year,
            "name": row.get("name"),
            "college": row.get("college"),
            "email": email,
            "percentage": row.get("percentage"),
            "phase": None,
            "batch_id": None,
            "status": "master_imported",
            "offer_accepted": False,
            "source": "master_database",
            "created_at": now,
            "updated_at": now,
        }
        await db.candidates.update_one({"year": year, "email": email}, {"$set": document}, upsert=True)
        candidate = await db.candidates.find_one({"year": year, "email": email})
        created_candidates.append(CandidateOut(**serialize_document(candidate)))
        await db.audit_logs.insert_one(
            {
                "entity_type": "candidate",
                "entity_id": str(candidate["_id"]),
                "action": "master_import",
                "message": f"Candidate loaded into master database for year {year}",
                "created_by": current_user["id"],
                "created_at": now,
            }
        )
    return created_candidates


@router.get("/roles")
async def list_roles(_: dict = Depends(require_roles("admin", "program_manager"))) -> list[dict]:
    roles = await get_database().roles.find().sort("name", 1).to_list(length=50)
    return [serialize_document(role) for role in roles]


@router.get("/me")
async def read_me(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user
