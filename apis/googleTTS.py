import requests
import json
import base64
import os
import whisper
from pydub import AudioSegment

# 🔹 Google Cloud API 키
GOOGLE_TTS_API_KEY = ""

# 🔹 API 요청 URL
url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"

# 🔹 TTS 음성이 저장될 폴더 경로
output_folder = os.path.expanduser("~/Desktop/FASTAPI-SERVER/TTSfile")

# 폴더가 없으면 생성
os.makedirs(output_folder, exist_ok=True)

def get_next_filename():
    """
    현재 폴더에 저장된 TTS 파일 목록을 확인하고,
    'tts_output_X.mp3' 형식의 파일명을 자동으로 증가시켜 반환하는 함수
    """
    existing_files = [f for f in os.listdir(output_folder) if f.startswith("tts_output") and f.endswith(".mp3")]
    numbers = [
        int(f.replace("tts_output_", "").replace(".mp3", ""))
        for f in existing_files if f.replace("tts_output_", "").replace(".mp3", "").isdigit()
    ]
    next_number = max(numbers) + 1 if numbers else 1
    return f"tts_output_{next_number}.mp3"

def generate_tts(text):
    """
    Google Cloud Text-to-Speech API를 사용하여 입력된 텍스트를 음성 데이터(MP3)로 변환하는 함수.
    변환된 오디오 데이터를 반환한다.
    """
    voice_name = "ko-KR-Wavenet-C"
    data = {
        "input": {"text": text},
        "voice": {
            "languageCode": "ko-KR",
            "name": voice_name,
            "ssmlGender": "MALE"
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 1.25
        }
    }
    response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
    
    if response.status_code == 200:
        response_data = response.json()
        audio_content = response_data["audioContent"]
        return base64.b64decode(audio_content)
    else:
        print(f"❌ 오류 발생: {response.text}")
        return None



def text_to_speech(text_list):
    """
    입력된 문장 리스트를 개별적으로 TTS 변환한 후,
    각 문장의 시작 시간을 5초 간격으로 맞춰 하나의 오디오 파일로 합치는 함수.
    """
    if not isinstance(text_list, list):
        raise ValueError("입력은 리스트 형식이어야 합니다.")
    
    combined_audio = AudioSegment.silent(duration=0)  # 최종 오디오 파일 (초기 무음 상태)
    start_time = 0  # 문장별 시작 시간 (밀리초 단위)
    interval = 5000  # 각 문장이 시작하는 간격 (5초 = 5000ms)
    
    for idx, text in enumerate(text_list):
        print(f"🔹 {idx * 5}초에 시작할 문장: {text}")
        
        audio_data = generate_tts(text)  # TTS 변환 실행
        if audio_data:
            temp_audio_path = os.path.join(output_folder, f"temp_tts_{idx}.mp3")
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            tts_audio = AudioSegment.from_mp3(temp_audio_path)  # 생성된 오디오 파일 로드
            
            # 현재 문장이 정확히 start_time에 시작되도록 공백 추가
            silent_gap = AudioSegment.silent(duration=max(0, start_time - len(combined_audio)))
            combined_audio += silent_gap + tts_audio
            
            start_time += interval  # 다음 문장 시작 시점 업데이트 (5초 추가)
            os.remove(temp_audio_path)  # 임시 파일 삭제
    
    output_file = os.path.join(output_folder, get_next_filename())
    combined_audio.export(output_file, format="mp3")  # 최종 음성 파일 저장
    print(f"✅ TTS 음성 파일이 생성되었습니다: {output_file}")
    
    analyze_audio_with_whisper(output_file)  # Whisper 분석 실행



def analyze_audio_with_whisper(audio_file):
    """
    Whisper 모델을 사용하여 생성된 음성 파일을 분석하고,
    음성 내 각 문장의 시작 및 끝 시간을 터미널에 출력하는 함수.
    """
    model = whisper.load_model("medium")
    result = model.transcribe(audio_file, word_timestamps=True)
    
    print("\n🔍 [Whisper 분석 결과] 🔍")
    print(f"🎵 파일명: {audio_file}\n")
    
    for segment in result["segments"]:
        start_time = round(segment["start"], 2)
        end_time = round(segment["end"], 2)
        text = segment["text"]
        print(f"⏱ {start_time}초 ~ {end_time}초: {text}")
    
    print("\n" + "-" * 50 + "\n")

# 🔹 테스트 실행
subtitles = [
    "코드를 작성할 때 주석을 충분히 달지 않는 실수를 종종 합니다.",
    "변수명을 명확하지 않게 지어서 나중에 혼란을 겪게 되죠.",
    "백업 없이 중요한 코드를 수정하는 경우가 많습니다.",
    "에러 메시지를 제대로 읽지 않고 넘어가는 경우도 흔해요."
]

subtitles2 = [
    "동해물과 백두산이 마르고 닳도록.",
    "하느님이 보우하사 우리나라 만세.",
    "무궁화 삼천리 화려강산",
    "대한사람 대한으로 길이 보전하세"
]

text_to_speech(subtitles)
text_to_speech(subtitles2)
