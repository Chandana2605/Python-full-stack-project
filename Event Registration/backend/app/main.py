from fastapi import FastAPI
from app.database import engine,Base
from app.models import user,event,registration
from app.seed import seed_admin
from app.routers import auth,events,registrations
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(registrations.router)
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    seed_admin()