# backend/app/api/v1/endpoints/files.py
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

router = APIRouter()

# Create a temporary directory for uploads
TEMP_UPLOAD_DIR = Path("./temp_uploads")
TEMP_UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", status_code=201)
async def upload_file(file: UploadFile = File(...)):
    """
    Handles file uploads (e.g., CSVs, images).
    - Scans for viruses (placeholder)
    - Stores file temporarily
    - Returns file metadata
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # In a real app, you would add a virus scan here.
    # For now, we trust the upload.

    try:
        # Save the file to a temporary location
        file_location = TEMP_UPLOAD_DIR / file.filename
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        return {
            "message": f"File '{file.filename}' uploaded successfully.",
            "filename": file.filename,
            "content_type": file.content_type,
            "temp_path": str(file_location)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")