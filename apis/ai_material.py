# 사용자의 입력을 통해 자막과 이미지 생성 및 반환
from fastapi import APIRouter
from pydantic import BaseModel
import openai
import os
import requests

router = APIRouter()

# 환경 변수에서 API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ 요청 데이터 모델 정의
class MaterialRequest(BaseModel):
    title: str
    duration: int

# OpenAI API 호출 함수
def generate_script(title: str, duration: int):
    segments = duration // 5  # 5초에 1개씩 자막 생성
    prompt = f"""
    {title} 주제에 맞는 숏폼 대본을 생성해줘. 총 {segments}개의 문장으로 구성되어야 하고, 각 문장은 반드시 12개의 단어로 이루어져야 해. 번호 없이 문장만 출력해줘.
    """.strip()
    #12개 단어로 구성된 문장을 1.15 속도로 했을 때 5초에 가깝게 생성
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "너는 숏폼 영상 대본을 생성하는 전문가야."},
                  {"role": "user", "content": prompt}],
    )
    
    # ✅ OpenAI 응답에서 텍스트 추출 후 줄바꿈 기준으로 리스트로 변환
    raw_script = response.choices[0].message.content.split("\n")
    return raw_script[:segments]

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
    max_images = 2

    if not os.path.exists("images"):
        os.makedirs("images")

    # ✅ 전체 문장을 번역 (무조건 실행)
    translated_subtitles = translate_to_english(subtitles)

    # ✅ 이미지 프롬프트 생성
    image_prompts = generate_image_prompt(translated_subtitles)

    for i, prompt in enumerate(image_prompts[:max_images]):  # ✅ for 루프 추가

        # ✅ API 요청
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}",
                "Accept": "image/*",  # 이미지 바이너리 데이터 받기
            },
            files={"none": ""},  # ✅ Multipart 형식 충족을 위해 필요
            data={
                "model": "sd3.5-large-turbo",
                "prompt": prompt,  # ✅ 번역된 프롬프트 사용
                "aspect_ratio": "9:16",
                "output_format": "jpeg",
            },
        )

        # ✅ 응답 확인 후 저장
        if response.status_code == 200:
            image_filename = f"images/generated_image_{i}.jpeg"
            with open(image_filename, "wb") as img_file:
                img_file.write(response.content)  # ✅ Base64 디코딩 불필요
            image_urls.append(f"http://127.0.0.1:8000/images/generated_image_{i}.jpeg")
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

    print("\n🚀 이미지 생성 시작!")
    image_urls = generate_images(subtitles)

    print("\n✅ 생성된 이미지 URL:", image_urls)  # 🚀 이미지 URL 확인

    # ✅ 최종 반환되는 JSON 데이터 확인
    response_data = {"subtitles": subtitles, "image_urls": image_urls}
    print("\n✅ 최종 반환 값:", response_data)

    return response_data

# 자막 생성 약 10초, 영문 변환 약 5초, 프롬프트 생성 약 10초, 이미지 하나 생성 약 3.5초