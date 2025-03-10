import requests
import json
import base64
import os

# 🔹 Google Cloud API 키
GOOGLE_TTS_API_KEY = ""

# 🔹 API 요청 URL
url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"

# 🔹 tts 음성이 저장될 폴더 경로
output_folder = os.path.expanduser("~/Desktop/FASTAPI-SERVER/TTSfile")

# 폴더가 없으면 생성
os.makedirs(output_folder, exist_ok=True)

def get_next_filename():
    #파일 순번을 자동 증가시키기 위한 함수
    existing_files = [f for f in os.listdir(output_folder) if f.startswith("tts_output") and f.endswith(".mp3")]
    numbers = [
        int(f.replace("tts_output_", "").replace(".mp3", ""))
        for f in existing_files if f.replace("tts_output_", "").replace(".mp3", "").isdigit()
    ]
    next_number = max(numbers) + 1 if numbers else 1
    return f"tts_output_{next_number}.mp3"

def text_to_speech(text):
    #TTS 변환 및 파일 저장 함수

    # 🔹 text가 리스트면 하나의 문자열로 변환
    if isinstance(text, list):
        text = " ".join(text)

    # 🔹 남성 음성으로 고정
    voice_name = "ko-KR-Wavenet-C"

    # 🔹 요청할 데이터 설정
    data = {
        "input": {"text": text},
        "voice": {
            "languageCode": "ko-KR",
            "name": voice_name,
            "ssmlGender": "MALE"
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

        # 🔹 파일 이름 생성 및 저장
        output_file = os.path.join(output_folder, get_next_filename())

        with open(output_file, "wb") as f:
            f.write(base64.b64decode(audio_content))
        print(f"✅ TTS 음성 파일이 생성되었습니다: {output_file}")

    else:
        print(f"❌ 오류 발생: {response.text}")

# 🔹 테스트 실행
subtitles = [
    "코드를 작성할 때 주석을 충분히 달지 않는 실수를 종종 합니다.",
    "변수명을 명확하지 않게 지어서 나중에 혼란을 겪게 되죠.",
    "백업 없이 중요한 코드를 수정하는 경우가 많습니다.",
    "에러 메시지를 제대로 읽지 않고 넘어가는 경우도 흔해요."
]

text_to_speech(subtitles)
text_to_speech(subtitles)
