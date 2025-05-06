# 사용자의 입력을 통해 자막과 이미지 생성 및 반환
from fastapi import APIRouter
from pydantic import BaseModel
import openai
import os
import requests
from typing import List
from dotenv import load_dotenv
router = APIRouter()

# 환경 변수에서 API 키 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ 요청 데이터 모델 정의
class MaterialRequest(BaseModel):
    title: str
    duration: int

# OpenAI API 호출 함수
def generate_script(title: str, duration: int):
    segments = duration // 5  # 5초에 1개씩 자막 생성
    prompt = f"""
        아래 주제에 맞는 유튜브 숏폼 영상 스크립트를 작성해.
        주제: "{title}"
        
        절대적인 작성 규칙
        1. 총 {segments}개의 문장으로 구성되어야 한다. 
        2. 각 문장은 반드시 13개의 단어로 이루어져야 한다.
        3. 이 규칙을 어기면 결과는 실패한 것으로 간주한다.
        4. 문장마다 줄바꿈(엔터)을 넣어서 각 문장이 줄바꿈으로 구분되게 한다.
        5. 빈 줄은 절대 추가하지 않는다.

        문장 스타일 규칙
        1. 영상은 시청자의 관심을 끌 수 있는 오프닝 질문이나 상황으로 시작한다.
        2. 주제에 따라 핵심 아이디어나 사례를 자연스럽게 설명한다..
        - 단순 나열은 피하고, 각 아이디어가 이어지도록 작성한다..
        - 숫자나 목록 형식(1., 2., 3.)은 사용하지 말고, 설명하는 형식(첫 번째, 두 번째, 세 번째)으로 작성한다..
        3. 영상 마지막은 시청자의 참여를 유도하는 콜투액션이나 긍정적인 응원의 멘트로 마무리한다.
        """.strip()
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "너는 숏폼 영상 대본을 생성하는 전문가야."},
                  {"role": "user", "content": prompt}],
    )
    
    # ✅ 응답 텍스트 줄바꿈 기준으로 자르기
    raw_script = response.choices[0].message.content.split("\n")

    # ✅ 각 문장 앞뒤 공백 제거 + 빈 문장 제거
    clean_script = [sentence.strip() for sentence in raw_script if sentence.strip()]

    # ✅ 필요한 문장 개수만 반환
    return clean_script[:segments]

# ✅ 전체 subtitles 리스트를 한 번에 번역
def translate_to_english(text_list: list):
    text = "\n".join(text_list)  # 리스트를 하나의 문자열로 변환
    prompt = f"Translate the following Korean text into natural English:\n\n{text}"
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a professional Korean-to-English translator."},
                  {"role": "user", "content": prompt}],
    )
    
    translated_text = response.choices[0].message.content.strip()
    translated_subtitles = translated_text.split("\n")

    return translated_subtitles

# ✅ 대본을 기반으로 이미지 생성을 위한 프롬프트 생성 함수
def generate_image_prompt(subtitles):
    text = "\n".join(subtitles)
    prompt = f"""
        Generate a suitable image description for each of the following subtitles. 
        The description should be highly detailed and optimized for AI-based image generation. 
        Do not include the original subtitles in the response—only provide the descriptions.

        Subtitles:
        {text}

        Output:
        - You must generate exactly {len(subtitles)} image descriptions.
        - Each description must be on a separate line.
        - Ensure the descriptions are vivid, creative, and directly relevant to the subtitle.
        - Do not include any extra text or formatting.
        """.strip()
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are an AI that generates highly detailed image descriptions for Stable Diffusion."},
                  {"role": "user", "content": prompt}],
    )

    # ✅ 빈 문자열 제거하여 프롬프트 정리
    generated_prompts = [p.strip() for p in response.choices[0].message.content.strip().split("\n") if p.strip()]

    return generated_prompts

# Stable Diffusion API 호출 함수
def generate_images(subtitles):
    image_urls = []
    max_images = 12

    if not os.path.exists("images"):
        os.makedirs("images")

    # ✅ 현재 이미지 개수 기준으로 고유 번호 시작점 계산
    # existing_images = [f for f in os.listdir("images") if f.endswith(".jpeg")]
    # start_index = len(existing_images)

    translated_subtitles = translate_to_english(subtitles)
    image_prompts = generate_image_prompt(translated_subtitles)

    for i, prompt in enumerate(image_prompts[:max_images]):
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}",
                "Accept": "image/*",
            },
            files={"none": ""},
            data={
                "model": "sd3.5-large-turbo",
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "output_format": "jpeg",
            },
        )

        if response.status_code == 200:
            image_filename = os.path.join("images", f"generated_image_{i+1}.jpeg")
            # unique_index = start_index + i
            # image_filename = os.path.join("images", f"generated_image_{unique_index}.jpeg")

            with open(image_filename, "wb") as img_file:
                img_file.write(response.content)

            image_url = f"http://{SERVER_HOST}:8000/{image_filename.replace(os.sep, '/')}"
            image_urls.append(image_url)

            print(f"✅ 이미지 저장 완료: {image_filename}")
        else:
            print(f"❌ 이미지 생성 실패: {response.status_code} - {response.text}")
            image_urls.append(None)

    return image_urls


# ✅ FastAPI 엔드포인트 (Request Body 사용)
@router.post("/")
async def generate_material(request: MaterialRequest):
    print("\n🚀 OpenAI 대본 생성 시작!")
    subtitles = generate_script(request.title, request.duration)

    print("\n✅ 생성된 대본:", subtitles)  # 🚀 OpenAI에서 받은 대본 확인

    image_urls = []
    print("\n🚀 이미지 생성 시작!")
    image_urls = generate_images(subtitles)

    print("\n✅ 생성된 이미지 URL:", image_urls)  # 🚀 이미지 URL 확인

    # ✅ 최종 반환되는 JSON 데이터 확인
    response_data = {"subtitles": subtitles, "image_urls": image_urls}
    print("\n✅ 최종 반환 값:", response_data)

    return response_data

# 자막 생성 약 15초, 영문 변환 약 5초, 프롬프트 생성 약 10초, 이미지 하나 생성 약 3.5초
