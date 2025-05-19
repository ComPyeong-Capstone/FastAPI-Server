from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from uuid import uuid4
import cv2
import os
import io
import asyncio

router = APIRouter()

async def save_temp_video(upload_file: UploadFile) -> str:
    contents = await upload_file.read()
    video_path = f"/tmp/{uuid4().hex}.mp4"
    with open(video_path, "wb") as f:
        f.write(contents)
    return video_path

def extract_thumbnail(video_path: str):
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    os.remove(video_path)
    if not success:
        raise HTTPException(status_code=400, detail="Video read failed")
    _, encoded = cv2.imencode(".jpg", frame)
    return encoded

@router.post("/generate/thumbnail")
async def generate_thumbnail(video: UploadFile = File(...)):
    video_path = await save_temp_video(video)
    encoded = await asyncio.to_thread(extract_thumbnail, video_path)
    return StreamingResponse(io.BytesIO(encoded.tobytes()), media_type="image/jpeg")

