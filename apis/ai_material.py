# 사용자의 입력을 통해 자막과 이미지 생성 및 반환
from fastapi import APIRouter
import openai
import requests
import os
import base64

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")

# OpenAI API 호출 함수
def generate_script(title: str, duration: int):
    segments = duration // 5  # 5초에 1개씩 자막 생성
    prompt = f"""
    {title} 주제에 맞는 숏폼 대본을 생성해줘. 총 {segments}개의 문장으로 구성되어야 하고, 각 문장은 반드시 12개의 단어로 이루어져야 해.
    """.strip()
    #12개 단어로 구성된 문장을 1.15 속도로 했을 때 5초에 가깝게 생성
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "너는 숏폼 영상 대본을 생성하는 전문가야."},
                  {"role": "user", "content": prompt}],
        api_key=OPENAI_API_KEY
    )
    
    script = response["choices"][0]["message"]["content"].split("\n")

     # 정확히 12단어만 포함된 문장만 필터링
    clean_script = []
    for sentence in script:
        words = sentence.split()
        if len(words) == 12:
            clean_script.append(sentence)
    
    return clean_script[:segments]  

# Stable Diffusion API 호출 함수
def generate_images(subtitles):
    image_urls = []

    for subtitle in subtitles:
        prompt = f"{subtitle}에 어울리는 이미지 생성"

        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}",
                "accept": "application/json"  # Base64로 받기 위해 JSON 응답 요청
            },
            data={
                "model": "sd3.5-large-turbo",  # ✅ Stable Diffusion 3.5 Large Turbo 사용
                "prompt": prompt,
                "output_format": "jpeg",  # PNG도 가능
                "aspect_ratio": "9:16",  # ✅ 비율 설정 가능
                "seed": 0,  # 랜덤 시드 (고정하면 동일한 이미지 생성)
                "cfg_scale": 7,  # 프롬프트 반영 강도 (1~10)
            }
        )

        # 응답 처리 (Base64 인코딩된 이미지 받기)
        if response.status_code == 200:
            image_data = response.json().get("image")
            if image_data:
                image_filename = f"./generated_image_{subtitles.index(subtitle)}.jpeg"
                with open(image_filename, "wb") as img_file:
                    img_file.write(base64.b64decode(image_data.split(",")[1]))  # Base64 디코딩 후 저장
                image_urls.append(image_filename)
            else:
                image_urls.append(None)
        else:
            print(f"이미지 생성 실패: {response.status_code} - {response.text}")
            image_urls.append(None)

    return image_urls

# FastAPI 엔드포인트
@router.post("/")
async def generate_material(title: str, duration: int):
    subtitles = generate_script(title, duration)  # 자막 생성
    image_urls = generate_images(subtitles)  # 이미지 생성
    
    return {"subtitles": subtitles, "image_urls": image_urls}
