import time
import base64
from fastapi import APIRouter
from typing import List
import os
import requests
from runwayml import RunwayML  # ✅ Runway API 클라이언트 사용

router = APIRouter()

# 환경 변수에서 API 키 로드
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

# Runway 클라이언트 초기화
client = RunwayML(api_key=RUNWAY_API_KEY)

# Runway API 호출 함수
def generate_video(image_filename: str, subtitle: str, index: int):
    # 이미지 파일을 Base64로 인코딩
    image_path = os.path.join("images", image_filename)
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")
    task = client.image_to_video.create(
        model='gen3a_turbo',  # ✅ 최신 모델 사용
        prompt_image=f"data:image/png;base64,{base64_image}",
        prompt_text=f"Create a cinematic animation that visually represents {subtitle}, inspired by the given image.",
        duration=5,  # ✅ 5초짜리 영상 생성
        ratio="768:1280",  # ✅ 기본 비율 설정
    )

    # 생성된 작업 ID
    task_id = task.id
    print(f"Task ID: {task_id}")

    # 작업 상태 확인
    print("Waiting for the task to complete...")
    while True:
        task_status = client.tasks.retrieve(task_id)  # ✅ 작업 상태 확인
        print(f"Current status: {task_status.status}")
        if task_status.status in ['SUCCEEDED', 'FAILED']:
            break
        time.sleep(10)  # ✅ 10초 대기 후 다시 확인

    # 작업 결과 반환
    if task_status.status == 'SUCCEEDED':
        video_url = task_status.output[0]  # ✅ 영상 URL 가져오기
        print(f"Task completed successfully! Video URL: {video_url}")

        # ✅ 영상 다운로드 후 저장
        video_filename = f"videos/generated_{image_filename}.mp4"  # ✅ 저장될 파일명
        download_video(video_url, video_filename)

        return f"http://127.0.0.1:8000/{video_filename}"
    else:
        print("Task failed. No video generated.", task_status.error)
        return None

# ✅ 영상 다운로드 함수
def download_video(video_url: str, save_path: str):
    print(f"Downloading video from: {video_url}")
    
    response = requests.get(video_url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=1024):
                video_file.write(chunk)
        print(f"✅ Video saved: {save_path}")
    else:
        print(f"❌ Failed to download video: {video_url}")

# FastAPI 엔드포인트
@router.post("/")
async def generate_partial_videos(images: List[str], subtitles: List[str]):
    video_urls = []
    for index, (image, subtitle) in enumerate(zip(images, subtitles)):
        video_url = generate_video(image, subtitle, index)
        video_urls.append(video_url)

    return {"video_urls": video_urls}

# 영상 하나 약 30초