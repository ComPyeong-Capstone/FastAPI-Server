import time
import base64
from fastapi import APIRouter
from typing import List
import os
from runwayml import RunwayML  # ✅ Runway API 클라이언트 사용

router = APIRouter()

# 환경 변수에서 API 키 로드
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

# Runway 클라이언트 초기화
client = RunwayML(api_key=RUNWAY_API_KEY)

# Runway API 호출 함수
def generate_video(image_path: str, subtitle: str):
    """
    주어진 이미지와 자막을 기반으로 Runway API를 사용해 5초짜리 영상을 생성하는 함수.
    """
    
    # 이미지 파일을 Base64로 인코딩
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    # Image-to-Video 작업 생성
    print(f"Creating video generation task for: {subtitle}")
    
    task = client.image_to_video.create(
        model='gen3a_turbo',  # ✅ 최신 모델 사용
        prompt_image=f"data:image/png;base64,{base64_image}",
        prompt_text=subtitle,
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
        print(f"Task completed successfully! Video URL: {task_status.output[0]}")
        return task_status.output[0]  # ✅ 생성된 영상 URL 반환
    else:
        print("Task failed. No video generated.")
        return None

# FastAPI 엔드포인트
@router.post("/")
async def generate_partial_videos(images: List[str], subtitles: List[str]):
    """
    여러 개의 이미지와 자막을 받아 각 자막에 맞는 5초짜리 영상을 생성 후 반환하는 API 엔드포인트.
    """
    
    video_urls = []
    for image, subtitle in zip(images, subtitles):
        video_url = generate_video(image, subtitle)
        video_urls.append(video_url)

    return {"video_urls": video_urls}
