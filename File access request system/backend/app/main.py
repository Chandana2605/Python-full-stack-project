from fastapi import FastAPI
from app.seed import seed_data
from app.routers import files, access_requests, permissions

app = FastAPI(title="Secure File Access System (MongoDB)")

seed_data()

app.include_router(files.router)
app.include_router(access_requests.router)
app.include_router(permissions.router)
