from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

router = APIRouter()
load_dotenv()
SERVER_HOST = os.getenv("SERVER_HOST")

@router.get("/music/previews")
async def list_preview_music():
    base_url = "http://{SERVER_HOST}:8000/music"
    previews = [
        {"title": "딸기맛 사이다", "url": f"{base_url}/bgm_01.mp3"},
        # {"title": "Ambient Texture", "url": f"{base_url}/preview2.mp3"},
        # {"title": "Electronic Beat", "url": f"{base_url}/preview3.mp3"},
        # {"title": "Ambient Texture", "url": f"{base_url}/preview4.mp3"},
        # {"title": "Electronic Beat", "url": f"{base_url}/preview5.mp3"}
    ]
    return JSONResponse(content={"previews": previews})
