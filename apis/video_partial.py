import time
import base64
from fastapi import APIRouter
from typing import List
import os
import requests
import openai
from runwayml import RunwayML  # ✅ Runway API 클라이언트 사용
from pydantic import BaseModel

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")

# Runway 클라이언트 초기화
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
client = RunwayML(api_key=RUNWAY_API_KEY)

class VideoRequest(BaseModel):
    images: List[str]
    subtitles: List[str]

def generate_prompt(subtitles: List[str]) -> List[str]:
    
    # 1. GPT를 통한 프롬프트 생성 방법
    subtitles_list = "\n".join([f"- {subtitle}" for subtitle in subtitles])

    prompt_for_gpt = f"""
    You are an AI prompt engineer for a high-energy, fast-paced, visually explosive video generation model like Runway Gen-3.

    Given the subtitles below, create thrilling, action-packed, and highly energetic prompts for short-form vertical videos.

    Each prompt should:
    - Be a single dynamic scene (no multiple time jumps)
    - Feature intense motion, rapid actions, strong emotional expressions
    - Use advanced camera movements like whip pan, snap zoom, rapid dolly, handheld shake
    - Include bold lighting like strobe, neon glow, dynamic shadows, sparks, or digital glitch effects
    - Optionally include sci-fi or futuristic visuals: holographic interfaces, particle explosions, AI overlays
    - Avoid static or calm scenes
    - No numbering, no extra commentary — just one descriptive sentence per subtitle

    Subtitles:
    {subtitles_list}
    """.strip()

    response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt_for_gpt}],
    )

    generated_prompt = response.choices[0].message.content.strip()
    prompts = generated_prompt.split('\n')
    cleaned_prompts = [
        line.split('. ', 1)[1] if '. ' in line else line 
        for line in prompts if line.strip() != ''
    ]

    # # 2. 단순하게 제작한 프롬프트
    # # 한글 자막 리스트를 하나의 문자열로 합치기
    # joined_subtitles = "\n".join(subtitles)

    # # GPT에게 자연스럽고 시각적인 영어로 번역 요청
    # prompt = f"""
    # Translate the following Korean subtitles into natural and vivid English.
    # ⚠️ Return only the translated lines, without any numbering, bullet points, or explanations.
    # ⚠️ Do NOT add headers like 'Subtitles in English:' — just return one line per subtitle.

    # Korean Subtitles:
    # {joined_subtitles}
    # """.strip()

    # response = openai_client.chat.completions.create(
    #     model="gpt-4-turbo",
    #     messages=[
    #         {"role": "system", "content": "You are a professional translator for AI video generation."},
    #         {"role": "user", "content": prompt}
    #     ],
    # )

    # # 응답을 줄 단위로 나누고 정리
    # translated_lines = [
    #     line.strip()
    #     for line in response.choices[0].message.content.strip().split("\n")
    #     if line.strip()
    # ]

    # # 최종 프롬프트 생성
    # cleaned_prompts = [f"Create a cinematic video for the scene: {line}" for line in translated_lines]

    print("✅ Generated prompts list:")
    for idx, prompt in enumerate(cleaned_prompts):
        print(f"{idx + 1}: {prompt}")

    return cleaned_prompts

# Runway API 호출 함수
def generate_video(image_filename: str, subtitle: str):
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

        filename_without_ext, _ = os.path.splitext(image_filename)

        # 고유한 파일 이름 생성
        base_name = f"generated_{filename_without_ext}_AI"
        ext = ".mp4"
        i = 1
        save_path = os.path.join("videos", f"{base_name}_{i}{ext}")
        while os.path.exists(save_path):
            i += 1
            save_path = os.path.join("videos", f"{base_name}_{i}{ext}")
        download_video(video_url, save_path)

        return f"http://127.0.0.1:8000/{save_path}"
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
    prompts = generate_prompt(request.subtitles)

    video_urls = []
    for image, prompt in zip(request.images, prompts):
        video_url = generate_video(image, prompt)
        video_urls.append(video_url)

    return {"video_urls": video_urls}

# 영상 하나 약 30초