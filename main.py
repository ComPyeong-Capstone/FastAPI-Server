from fastapi import FastAPI, Request
from apis import ai_material, video_partial, video_final, thumbnail, image_partial, get_music
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os

load_dotenv()
SERVER_HOST = os.getenv("SERVER_HOST")

app = FastAPI(title="AI Video Generation API")
templates = Jinja2Templates(directory="templates")

# CORS 설정 (프론트엔드에서 API 호출 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 특정 도메인만 허용하려면 ["https://example.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/music", StaticFiles(directory="music"), name="music")

# API 라우터 등록
app.include_router(ai_material.router, prefix="/generate/material", tags=["AI_Image"])
app.include_router(video_partial.router, prefix="/generate/video/partial", tags=["Video"])
app.include_router(video_final.router, prefix="/generate/video/final", tags=["Video"])
app.include_router(thumbnail.router)
app.include_router(image_partial.router, prefix="/generate/material", tags=["AI_Image"])
app.include_router(get_music.router, tags=["Music"]) 

@app.get("/")
async def root():
    return {"message": "Welcome to AI Video Generation API"}

@app.get("/login", response_class=HTMLResponse)
async def serve_login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "kakao_js_key": os.getenv("KAKAO_JS_KEY"),
        "kakao_rest_api_key": os.getenv("KAKAO_REST_API_KEY"),
        "kakao_redirect_uri": os.getenv("KAKAO_REDIRECT_URI"),
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=8000, reload=True)
