# 사용자의 입력을 통해 자막과 이미지 생성 및 반환
from fastapi import APIRouter
import openai
import requests
import os

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")

# OpenAI API 호출 함수
def generate_script(title: str, duration: int):
    segments = duration // 5  # 5초에 1개씩 자막 생성
    prompt = f"""
    주제: {title}
    설명: 이 주제에 대해 {segments}개의 핵심적인 내용을 설명하는 영상 대본을 생성해줘.
    각 대본은 1개의 문장으로 표현되며, 영상이 5초마다 한 개의 문장을 보여줄 거야.
    """.strip()
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}],
        api_key=OPENAI_API_KEY
    )
    
    script = response["choices"][0]["message"]["content"].split("\n")
    return script[:segments]  # 5초에 1개씩 잘라서 반환

# Stable Diffusion API 호출 함수
def generate_images(subtitles):
    image_urls = []
    for subtitle in subtitles:
        prompt = f'"{subtitle}"에 어울리는 이미지 생성해줘'
        response = requests.post(
            "https://api.stablediffusion.com/v1/generate",
            json={"prompt": prompt, "api_key": STABLE_DIFFUSION_API_KEY}
        ).json()
        image_url = response.get("image_url")
        image_urls.append(image_url)
    
    return image_urls

# FastAPI 엔드포인트
@router.post("/")
async def generate_material(title: str, duration: int):
    subtitles = generate_script(title, duration)  # 자막 생성
    image_urls = generate_images(subtitles)  # 이미지 생성
    
    return {"subtitles": subtitles, "image_urls": image_urls}
