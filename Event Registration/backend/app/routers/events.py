from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventCreate,EventResponse
from app.core.deps import get_current_user,require_admin

router=APIRouter(
    prefix="/events",
    tags=["events"]
)

@router.get("",response_model=list[EventResponse])
def get_events(
    db: Session=Depends(get_db),
    current_user=Depends(get_current_user)
):
    events=db.query(Event).all()
    return events

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(require_admin)
):
    new_event = Event(
        event_name=event_in.event_name,
        date=event_in.date,
        location=event_in.location,
        created_by=current_admin.id   
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

    
@router.put("/{event_id}",response_model=EventResponse)
def update_event(
    event_id:int,
    event_in:EventCreate,
    db:Session=Depends(get_db),
    current_admin=Depends(require_admin)
):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    event.event_name=event_in.event_name
    event.date=event_in.date
    event.location=event_in.location
    db.commit()
    db.refresh(event)
    return event
    
@router.delete("/{event_id}",status_code=status.HTTP_200_OK)
def delete_event(
    event_id:int,
    db:Session=Depends(get_db),
    current_admin=Depends(require_admin)
):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    db.delete(event)
    db.commit()
    return{"message":"Event deleted successsfully!"}
    
    