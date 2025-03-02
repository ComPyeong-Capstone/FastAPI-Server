# 사용자의 입력을 통해 부분 영상 생성 및 반환
from fastapi import APIRouter
from typing import List
import requests
import os

router = APIRouter()

# 환경 변수에서 API 키 로드
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

# Runway API 호출 함수
def generate_video(image_url: str, subtitle: str):
    prompt = f'"{subtitle}" 내용을 표현하는 5초짜리 애니메이션 영상 생성해줘'
    
    response = requests.post(
        "https://api.runwayml.com/v1/generate-video",
        json={
            "text": prompt,
            "image": image_url,
            "api_key": RUNWAY_API_KEY,
            "duration": 5  # 5초짜리 영상 생성
        }
    ).json()

    return response.get("video_url")

# FastAPI 엔드포인트
@router.post("/")
async def generate_partial_videos(images: List[str], subtitles: List[str]):
    if not (6 <= len(images) <= 12 and 6 <= len(subtitles) <= 12):
        return {"error": "이미지와 자막 개수는 6~12개여야 합니다."}

    video_urls = []
    for image, subtitle in zip(images, subtitles):
        video_url = generate_video(image, subtitle)
        video_urls.append(video_url)

    return {"video_urls": video_urls}
