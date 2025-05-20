# 사용자의 입력을 통해 자막과 이미지 생성 및 반환
from fastapi import APIRouter
from pydantic import BaseModel
import openai
import os
import requests
from dotenv import load_dotenv
router = APIRouter()
import httpx
import asyncio

# 환경 변수에서 API 키 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")
MAX_RETRIES = 2

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
You are an AI system that generates highly detailed image prompts for generative models like Stable Diffusion.

Your task is to generate exactly {len(subtitles)} distinct and vivid image descriptions. 
Each description must directly match the meaning and tone of each subtitle listed below.

📌 Strict Output Rules:
- Return exactly {len(subtitles)} lines.
- Each line must correspond to one subtitle.
- Do NOT use numbers, bullet points, or labels.
- Do NOT include the original subtitles.
- Each line must be a standalone English prompt optimized for image generation.
- Do NOT include any extra explanation or formatting.

Subtitles:
{text}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You generate English image prompts for subtitles used in AI video generation."},
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = response.choices[0].message.content.strip()
    generated_prompts = [line.strip() for line in raw_output.split("\n") if line.strip()]

    # ✅ 보정: GPT가 줄 수보다 적게 반환했을 때 기본 이미지 프롬프트로 채움
    if len(generated_prompts) < len(subtitles):
        print(f"⚠️ 생성된 프롬프트 개수 부족: {len(generated_prompts)} / 기대: {len(subtitles)}")
        for _ in range(len(subtitles) - len(generated_prompts)):
            generated_prompts.append("A generic cinematic frame with abstract colors and soft lighting.")

    # ✅ 보정: GPT가 잘못해서 너무 많이 반환한 경우도 잘라냄

    print("📸 생성된 이미지 프롬프트:", generated_prompts)

    return generated_prompts[:len(subtitles)]

# 영상 생성 실패 시 재생성 시도 함수
async def generate_one_image(prompt: str, index: int):
    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
    headers = {
        "Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}",
        "Accept": "image/*",
    }
    data = {
        "model": "sd3.5-large-turbo",
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "output_format": "jpeg",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, files={"none": ""}, data=data)

            if response.status_code == 200:
                filename = os.path.join("images", f"generated_image_{index+1}.jpeg")
                with open(filename, "wb") as f:
                    f.write(response.content)

                image_url = f"http://{SERVER_HOST}:8000/{filename.replace(os.sep, '/')}"
                print(f"✅ [{index+1}] 이미지 저장 완료 (시도 {attempt+1})")
                return image_url
            else:
                print(f"❌ [{index+1}] 실패 (시도 {attempt+1}): {response.status_code} - {response.text}")
                await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ [{index+1}] 예외 발생 (시도 {attempt+1}): {e}")
            await asyncio.sleep(1)

    print(f"❌ [{index+1}] 최종 실패: {prompt}")
    return None


async def generate_images(subtitles):
    if not os.path.exists("images"):
        os.makedirs("images")

    translated_subtitles = await asyncio.to_thread(translate_to_english, subtitles)
    image_prompts = await asyncio.to_thread(generate_image_prompt, translated_subtitles)

    tasks = [
        generate_one_image(prompt, i)
        for i, prompt in enumerate(image_prompts[:12])
    ]
    image_urls = await asyncio.gather(*tasks)
    return image_urls

# ✅ FastAPI 엔드포인트 (Request Body 사용)
@router.post("/")
async def generate_material(request: MaterialRequest):
    print("\n🚀 OpenAI 대본 생성 시작!")
    subtitles = await asyncio.to_thread(generate_script, request.title, request.duration)

    print("\n✅ 생성된 대본:", subtitles)  # 🚀 OpenAI에서 받은 대본 확인

    image_urls = []
    print("\n🚀 이미지 생성 시작!")
    image_urls = await generate_images(subtitles)

    print("\n✅ 생성된 이미지 URL:", image_urls)  # 🚀 이미지 URL 확인

    # ✅ 최종 반환되는 JSON 데이터 확인
    response_data = {"subtitles": subtitles, "image_urls": image_urls}
    print("\n✅ 최종 반환 값:", response_data)

    return response_data

# 자막 생성 약 15초, 영문 변환 약 5초, 프롬프트 생성 약 10초, 이미지 하나 생성 약 3.5초
