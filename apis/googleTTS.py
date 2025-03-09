import requests
import json
import base64
import os

# 🔹 API 키 (Google Cloud에서 발급한 키 입력!)
API_KEY = os.getenv("GOOGLE_TTS_API_KEY")

# 🔹 API 요청 URL (API 키 포함)
url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

# 🔹 요청할 텍스트 및 음성 설정
data = {
    "input": {"text": "안녕하세요! 구글 TTS API를 사용해 보세요."},
    "voice": {
        "languageCode": "ko-KR",
        "name": "ko-KR-Wavenet-B",  # 여성 음성 (남성: ko-KR-Wavenet-C)
        "ssmlGender": "NEUTRAL"
    },
    "audioConfig": {
        "audioEncoding": "MP3",
        "speakingRate": 1.25  # 속도 1.25배 증가
    }
}

# 🔹 API 요청 보내기
response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data))

# 🔹 응답 확인
if response.status_code == 200:
    response_data = response.json()
    audio_content = response_data["audioContent"]

    # 🔹 음성 파일 저장
    output_file = "tts_output.mp3"
    with open(output_file, "wb") as f:
        f.write(base64.b64decode(audio_content))
    print(f"✅ TTS 음성 파일이 생성되었습니다: {output_file}")

else:
    print(f"❌ 오류 발생: {response.text}")
