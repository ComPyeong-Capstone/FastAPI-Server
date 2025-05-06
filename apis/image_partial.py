from fastapi import APIRouter
from pydantic import BaseModel
import openai
import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY")
SERVER_HOST = os.getenv("SERVER_HOST")

router = APIRouter()
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class PromptRequest(BaseModel):
    text: str
    number: int

def convert_to_prompt(subtitle: str) -> str:
    prompt = f"""
        Generate a vivid, highly detailed image description based on the following subtitle.
        The description should be optimized for Stable Diffusion image generation.
        Do not repeat the subtitle—just return a creative, cinematic visual description.

        Subtitle:
        {subtitle}

        Output:
        - Exactly 1 detailed image description.
        - Only return the description text (no list numbers, no extra formatting).
        - Make the description imaginative, visual, and directly related to the subtitle.
    """.strip()
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are an AI that generates highly detailed image descriptions for Stable Diffusion."},
                  {"role": "user", "content": prompt}],
    )

    result_lines = [line.strip() for line in response.choices[0].message.content.strip().split("\n") if line.strip()]
    return result_lines[0]

def generate_image(prompt: str, number: int) -> str:
    if not os.path.exists("images"):
        os.makedirs("images")

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
        image_filename = f"generated_image_{number}.jpeg"
        image_path = os.path.join("images", image_filename)
        with open(image_path, "wb") as f:
            f.write(response.content)

        image_url = f"http://{SERVER_HOST}:8000/images/{image_filename}"
        return image_url
    else:
        raise Exception(f"Image generation failed: {response.status_code} - {response.text}")

@router.post("/image")
async def generate_single_image(request: PromptRequest):
    print(f"📝 입력 문장: {request.text}")

    prompt = convert_to_prompt(request.text)
    print(f"🎨 변환된 프롬프트: {prompt}")

    image_url = generate_image(prompt, request.number)
    print(f"✅ 생성된 이미지 URL: {image_url}")

    return {"image_url": image_url}