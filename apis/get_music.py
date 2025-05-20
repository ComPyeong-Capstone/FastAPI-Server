from fastapi import APIRouter
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

router = APIRouter()
load_dotenv()
SERVER_HOST = os.getenv("SERVER_HOST")

@router.get("/previews")
async def list_preview_music():
    base_url = f"http://{SERVER_HOST}:8000/music"
    previews = [
        {"title": "Strawberry Cider", "url": f"{base_url}/bgm_01.mp3"},
        {"title": "White Color", "url": f"{base_url}/bgm_02.mp3"},
        {"title": "Blue Jacket", "url": f"{base_url}/bgm_03.mp3"},
        {"title": "Cute Puppy", "url": f"{base_url}/bgm_04.mp3"},
        {"title": "Big Cafe", "url": f"{base_url}/bgm_05.mp3"},
        {"title": "Spider", "url": f"{base_url}/bgm_06.mp3"},
        {"title": "Smiley composure", "url": f"{base_url}/bgm_07.mp3"},
        {"title": "Murder In My Mind", "url": f"{base_url}/bgm_08.mp3"},
    ]
    return JSONResponse(content={"previews": previews})
