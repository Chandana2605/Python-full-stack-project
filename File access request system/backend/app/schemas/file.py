from pydantic import BaseModel

# Input when admin creates a file
class FileCreate(BaseModel):
    filename: str
    description: str

# Output when files are listed
class FileResponse(BaseModel):
    id: str
    filename: str
    description: str
