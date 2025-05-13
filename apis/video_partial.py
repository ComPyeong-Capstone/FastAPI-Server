import time
import base64
from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import os
import requests
import openai
from runwayml import RunwayML  # ✅ Runway API 클라이언트 사용
from pydantic import BaseModel
import shutil

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")

# Runway 클라이언트 초기화
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
client = RunwayML(api_key=RUNWAY_API_KEY)

class VideoRequest(BaseModel):
    images: List[str]
    subtitles: List[str]

class SingleVideoRequest(BaseModel):
    image: str
    subtitle: str
    number: int

# GPT에 이미지와 자막을 전달해 프롬프트 생성
def generate_prompt_from_image_and_subtitle(image_path: str, subtitle: str) -> str:
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are an AI prompt engineer for cinematic video generation.\n"
                            f"Given the image above and the subtitle below, create a vivid, cinematic prompt "
                            "for a Runway Gen-3 video. Use one or two sentences, under 50 words, describing the scene visually.\n\n"
                            f"Subtitle: {subtitle}"
                            f"Only respond in English."
                        )
                    }
                ]
            }
        ],
        max_tokens=200
    )

    prompt = response.choices[0].message.content.strip()
    print(f"\n🖼️ Generated prompt for image + subtitle:\n{prompt}")
    return prompt


# Runway API 호출 함수
def generate_video(image_filename: str, subtitle: str, number: int = None):
    # 이미지 파일을 Base64로 인코딩
    image_path = os.path.join("images", image_filename)
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    task = client.image_to_video.create(
        model='gen3a_turbo',  # ✅ 최신 모델 사용
        prompt_image=f"data:image/png;base64,{base64_image}",
        prompt_text= subtitle,
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
        video_url = task_status.output[0]
        print(f"Task completed successfully! Video URL: {video_url}")

        if number is not None:
            base_name = f"generated_video_{number}"
        else:
            filename_without_ext, _ = os.path.splitext(image_filename)
            base_name = f"generated_{filename_without_ext}_AI"

        save_path = os.path.join("videos", f"{base_name}.mp4")
        ext = ".mp4"

        save_path = os.path.join("videos", f"{base_name}{ext}")

        # i = 1
        # save_path = os.path.join("videos", f"{base_name}_{i}{ext}")
        # while os.path.exists(save_path):
        #     i += 1
        #     save_path = os.path.join("videos", f"{base_name}_{i}{ext}")
        
        download_video(video_url, save_path)

        return f"http://{SERVER_HOST}:8000/{save_path}"
    else:
        print("Task failed. No video generated.")
        print("Task status info:", task_status.dict())  # 전체 상태를 보기 위해 추가
        print("Reason:", getattr(task_status, "status_reason", "No reason provided"))
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
async def generate_partial_videos(request: VideoRequest):
    video_urls = []

    for image_filename, subtitle in zip(request.images, request.subtitles):
        image_path = os.path.join("images", image_filename)
        prompt = generate_prompt_from_image_and_subtitle(image_path, subtitle)
        video_url = generate_video(image_filename, prompt)
        video_urls.append(video_url)

    return {"video_urls": video_urls}
# 영상 하나 약 30초

@router.post("/single")
async def generate_single_video(request: SingleVideoRequest):
    image_path = os.path.join("images", request.image)
    prompt = generate_prompt_from_image_and_subtitle(image_path, request.subtitle)
    video_url = generate_video(request.image, prompt, request.number)
    return {"video_url": video_url}

@router.post("/upload-images")
async def upload_images_and_generate(
    subtitles: List[str] = Form(...),
    files: List[UploadFile] = File(...)
):

    video_urls = []

    for idx, (file, subtitle) in enumerate(zip(files, subtitles), start=1):
        ext = os.path.splitext(file.filename)[-1]
        filename = f"user_image_{idx}{ext}"
        image_path = os.path.join("images", filename)

        with open(image_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        prompt = generate_prompt_from_image_and_subtitle(image_path, subtitle)
        video_url = generate_video(filename, prompt, idx)

        video_urls.append(video_url)

    return {"video_urls": video_urls}
