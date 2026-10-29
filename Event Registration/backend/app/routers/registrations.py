from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.registration import Registration
from app.models.event import Event
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.core.deps import get_current_user, require_admin


router = APIRouter(
    prefix="/registrations",
    tags=["registrations"]
)

@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_registration(
    registration_in: RegistrationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can register for events"
        )

    event = db.query(Event).filter(Event.id == registration_in.event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    existing = db.query(Registration).filter(
        Registration.user_id == current_user.id,
        Registration.event_id == registration_in.event_id,
        Registration.status == "Registered"
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already registered for this event"
        )

    registration = Registration(
        attendee_name=registration_in.attendee_name,
        user_id=current_user.id,
        event_id=registration_in.event_id,
        status="Registered"
    )

    db.add(registration)
    db.commit()
    db.refresh(registration)

    return registration


@router.put("/{registration_id}/cancel",response_model=RegistrationResponse)
def cancel_registration(
    registration_id:int,
    db:Session=Depends(get_db),
    current_user=Depends(get_current_user)
):
    registration=db.query(Registration).filter(Registration.id==registration_id).first()
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found"
        )
    if registration.user_id!=current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to cancel this registration"
        )
    if registration.status!="Registered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registation is already cancelled"
        )
    registration.status="Cancelled"
    db.commit()
    db.refresh(registration)
    return registration

@router.get("/my", response_model=list[RegistrationResponse])
def get_my_registrations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can view their registrations"
        )

    return db.query(Registration).filter(
        Registration.user_id == current_user.id
    ).all()


@router.get("",response_model=list[RegistrationResponse])
def get_all_registrations(
    event_id:int|None=None,
    db:Session=Depends(get_db),
    current_admin=Depends(require_admin)
):
    query=db.query(Registration)
    if event_id is not None:
        query=query.filter(Registration.event_id==event_id)
    registrations=query.all()
    return registrations
    