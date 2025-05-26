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
import asyncio

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")

# 🎨 스타일 리스트
STYLE_OPTIONS = [
    "cyberpunk", "anime-style exaggeration", "watercolor dreamscape", "glitchcore",
    "vaporwave", "surrealism", "neon noir", "kaleidoscopic burst", "pixel art chaos"
]

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
async def generate_prompt_from_image_and_subtitle(image_path: str, subtitle: str) -> str:
    base64_image = await asyncio.to_thread(lambda: base64.b64encode(open(image_path, "rb").read()).decode("utf-8"))

    # 1️⃣ 스타일 선택
    style_selection_prompt = f"""
    You are an AI assistant.
    Analyze the image and subtitle below, and select the most visually appropriate artistic style for cinematic video generation.
    Only return the name of the style from this list:

    {', '.join(STYLE_OPTIONS)}.

    Here is how to decide:
    - If the image feels peaceful, minimal, or dreamlike → 'watercolor dreamscape'
    - If chaotic, glitchy, or stressful → 'glitchcore' or 'cyberpunk'
    - If colorful and symmetric like a visual burst → 'kaleidoscopic burst'
    - If expressive, funny, or energetic → 'anime-style exaggeration'
    - If it resembles low-res games or old tech → 'pixel art chaos'
    - If it has a nostalgic, 90s retro vibe → 'vaporwave'
    - If it shows surreal, illogical, or dreamlike visuals → 'surrealism'
    - If it’s dark, cinematic, with neon lighting → 'neon noir'

    Subtitle: {subtitle}    
    """.strip()

    style_response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": style_selection_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                    {"type": "text", "text": f"Subtitle: {subtitle}"}
                ]
            }
        ],
        max_tokens=10
    )

    selected_style = style_response.choices[0].message.content.strip()
    print(f"\n🎨 Selected style: {selected_style}")

    # 2️⃣ 스타일 기반 최종 프롬프트 생성
    cinematic_prompt = f"""
    You are an AI prompt engineer for Runway Gen-3.

    Given the image and subtitle, write a cinematic video prompt (1–2 sentences, max 50 words) that:
    - Describes key objects or characters visible in the image
    - Makes those subjects perform noticeable, exaggerated **physical actions** (e.g., running, jumping, collapsing, dancing, reacting)
    - Avoids camera-only movement. Emphasize subject-driven motion instead.
    - Conveys the emotion or context implied by the subtitle

    End the prompt with: in a {selected_style} style.

    Only return the prompt text.
    """.strip()

    final_response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": cinematic_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                    {"type": "text", "text": f"Subtitle: {subtitle}"}
                ]
            }
        ],
        max_tokens=200
    )

    prompt = final_response.choices[0].message.content.strip()
    print(f"\n🖼️ Generated prompt for image + subtitle:\n{prompt}")
    return prompt


# Runway API 호출 함수
async def generate_video(image_filename: str, subtitle: str, number: int = None):
    # 이미지 파일을 Base64로 인코딩
    image_path = os.path.join("images", image_filename)
    base64_image = await asyncio.to_thread(lambda: base64.b64encode(open(image_path, "rb").read()).decode("utf-8"))

    task = await asyncio.to_thread(
        client.image_to_video.create,
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
        task_status = await asyncio.to_thread(client.tasks.retrieve, task_id)
        print(f"Current status: {task_status.status}")
        if task_status.status in ['SUCCEEDED', 'FAILED']:
            break
        await asyncio.sleep(10)

# 작업 결과 반환
    if task_status.status == 'SUCCEEDED':
        video_url = task_status.output[0]
        print(f"Task completed successfully! Video URL: {video_url}")

        videos_dir = "videos"
        ext = ".mp4"

        # 🔢 요청번호 관리
        request_counter_path = os.path.join(videos_dir, "request_counter.txt")
        if not os.path.exists(request_counter_path):
            current_request_number = 1
        else:
            with open(request_counter_path, "r") as f:
                current_request_number = int(f.read().strip())
            current_request_number += 1
            if current_request_number > 20:
                current_request_number = 1

        # 🔄 삭제 정책
        if current_request_number == 10:
            delete_range = range(11, 21)
        elif current_request_number == 20:
            delete_range = range(1, 11)
        else:
            delete_range = []

        for filename in os.listdir(videos_dir):
            for req_num in delete_range:
                prefix = f"generated_video_{req_num:02d}_"
                if filename.startswith(prefix) and filename.endswith(ext):
                    os.remove(os.path.join(videos_dir, filename))
                    print(f"🗑️ Deleted old file: {filename}")

        # 요청번호 저장
        with open(request_counter_path, "w") as f:
            f.write(str(current_request_number))

        # 🎥 영상번호 자동 부여 (01 ~ 12 중에서 비어있는 것)
        for i in range(1, 100):  # 최대 99개까지 시도 (안전장치)
            video_number = f"{i:02d}"
            filename = f"generated_video_{current_request_number:02d}_{video_number}{ext}"
            save_path = os.path.join(videos_dir, filename)
            if not os.path.exists(save_path):
                break

        print(f"💾 Saving video as: {save_path}")
        await download_video(video_url, save_path)

        return f"http://{SERVER_HOST}:8000/{save_path}"

    else:
        print("Task failed. No video generated.")
        print("Task status info:", task_status.dict())  # 전체 상태를 보기 위해 추가
        print("Reason:", getattr(task_status, "status_reason", "No reason provided"))
        return None

# ✅ 영상 다운로드 함수
async def download_video(video_url: str, save_path: str):
    print(f"Downloading video from: {video_url}")
    
    response = await asyncio.to_thread(requests.get, video_url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=1024):
                video_file.write(chunk)
        print(f"✅ Video saved: {save_path}")
    else:
        print(f"❌ Failed to download video: {video_url}")

runway_semaphore = asyncio.Semaphore(3)

async def generate_video_with_semaphore(image_filename: str, prompt: str, number: int = None):
    async with runway_semaphore:
        return await generate_video(image_filename, prompt, number)

# FastAPI 엔드포인트
@router.post("/")
async def generate_partial_videos(request: VideoRequest):
    video_urls = []

    # 1. 프롬프트를 비동기로 먼저 병렬 생성
    prompt_tasks = [
        generate_prompt_from_image_and_subtitle(os.path.join("images", image_filename), subtitle)
        for image_filename, subtitle in zip(request.images, request.subtitles)
    ]
    prompts = await asyncio.gather(*prompt_tasks)

#    2. 이후 runway에 동시 요청
    video_tasks = [
        generate_video_with_semaphore(image_filename, prompt, idx)
        for idx, (image_filename, prompt) in enumerate(zip(request.images, prompts), start=1)
    ]
    video_urls = await asyncio.gather(*video_tasks)
    return {"video_urls": video_urls}
# 영상 하나 약 30초

@router.post("/single")
async def generate_single_video(request: SingleVideoRequest):
    image_path = os.path.join("images", request.image)
    prompt = await generate_prompt_from_image_and_subtitle(image_path, request.subtitle)
    video_url = await generate_video(request.image, prompt, request.number)
    return {"video_url": video_url}

@router.post("/upload-images")
async def upload_images_and_generate(
    subtitles: List[str] = Form(...),
    files: List[UploadFile] = File(...)
):
    # 1. 이미지 저장
    image_filenames = []
    for idx, file in enumerate(files, start=1):
        ext = os.path.splitext(file.filename)[-1]
        filename = f"user_image_{idx}{ext}"
        image_path = os.path.join("images", filename)

        with open(image_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        image_filenames.append(filename)

    # 2. 프롬프트 병렬 생성
    prompt_tasks = [
        generate_prompt_from_image_and_subtitle(os.path.join("images", filename), subtitle)
        for filename, subtitle in zip(image_filenames, subtitles)
    ]
    prompts = await asyncio.gather(*prompt_tasks)

    # 3. Runway 병렬 요청 (최대 3개 동시에 진행)
    video_tasks = [
        generate_video_with_semaphore(filename, prompt, idx)
        for idx, (filename, prompt) in enumerate(zip(image_filenames, prompts), start=1)
    ]
    video_urls = await asyncio.gather(*video_tasks)

    return {"video_urls": video_urls}
