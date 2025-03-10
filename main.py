from fastapi import FastAPI
from apis import ai_material, video_partial, video_final
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AI Video Generation API")

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

# API 라우터 등록
app.include_router(ai_material.router, prefix="/generate/material", tags=["AI_Image"])
app.include_router(video_partial.router, prefix="/generate/video/partial", tags=["Video"])
app.include_router(video_final.router, prefix="/generate/video/final", tags=["Video"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Video Generation API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
