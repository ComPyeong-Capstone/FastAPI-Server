import requests
import json
import base64
import os
import whisper
from pydub import AudioSegment
from dotenv import load_dotenv
import time
# .env 파일 로드
load_dotenv()

# 🔹 Google Cloud API 키
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY")

# 🔹 API 요청 URL
url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"

# 🔹 TTS 음성이 저장될 폴더 경로
output_folder = os.path.expanduser("music")

# 폴더가 없으면 생성
os.makedirs(output_folder, exist_ok=True)

def get_next_filename():
    # 현재 폴더에 저장된 TTS 파일 목록을 확인하고,
    # 'tts_output_X.mp3' 형식의 파일명을 자동으로 증가시켜 반환하는 함수

    existing_files = [f for f in os.listdir(output_folder) if f.startswith("tts_output") and f.endswith(".mp3")]
    numbers = [
        int(f.replace("tts_output_", "").replace(".mp3", ""))
        for f in existing_files if f.replace("tts_output_", "").replace(".mp3", "").isdigit()
    ]
    next_number = max(numbers) + 1 if numbers else 1
    return f"tts_output_{next_number}.mp3"

def generate_tts(text):
    
    # Google Cloud Text-to-Speech API를 사용하여 입력된 텍스트를 음성 데이터(MP3)로 변환하는 함수.
    # 변환된 오디오 데이터를 반환한다.
    
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



# 문장을 단어 기준으로 앞/뒤로 분리하는 함수 (홀수는 앞부분이 더 많게)
def split_sentence(sentence):
    words = sentence.strip().split()
    mid = (len(words) + 1) // 2
    return ' '.join(words[:mid]), ' '.join(words[mid:])

# 메인 함수: 입력된 문자열 리스트를 TTS로 변환 후 합치고 duration 배열 반환
def text_to_speech(text_list):
    if not isinstance(text_list, list):
        raise ValueError("입력은 리스트 형식이어야 합니다.")
    
    combined_audio = AudioSegment.silent(duration=0)
    start_time = 0
    interval = 5000
    front_durations = []  # 각 앞부분의 duration 저장

    for idx, text in enumerate(text_list):
        # 문장 분리
        front_part, back_part = split_sentence(text)

        # 앞부분 TTS 생성 및 분석
        front_tts_data = generate_tts(front_part)
        front_temp_path = os.path.join(output_folder, f"temp_front_{idx}.mp3")
        with open(front_temp_path, "wb") as f:
            f.write(front_tts_data)

        front_duration = analyze_audio_with_whisper(front_temp_path)
        front_durations.append(front_duration)

        # 분리된 두 부분을 다시 합쳐서 최종 TTS 생성
        merged_text = front_part + " " + back_part
        merged_tts_data = generate_tts(merged_text)

        merged_temp_path = os.path.join(output_folder, f"temp_merged_{idx}.mp3")
        with open(merged_temp_path, "wb") as f:
            f.write(merged_tts_data)

        tts_audio = AudioSegment.from_mp3(merged_temp_path)

        # 시작 시간 맞추기 위한 무음 추가
        silent_gap = AudioSegment.silent(duration=max(0, start_time - len(combined_audio)))
        if start_time >= 5000:
            silent_gap += AudioSegment.silent(duration=500)

        # 최종 오디오에 추가
        combined_audio += silent_gap + tts_audio
        start_time += interval

        # 임시 파일 정리
        os.remove(front_temp_path)
        os.remove(merged_temp_path)

    # 전체 길이를 5초 단위로 맞추기
    final_length_ms = ((len(combined_audio) + 4999) // 5000) * 5000
    if len(combined_audio) < final_length_ms:
        padding_duration = final_length_ms - len(combined_audio)
        combined_audio += AudioSegment.silent(duration=padding_duration)

    # 최종 파일 저장
    output_file = os.path.join(output_folder, get_next_filename())
    combined_audio.export(output_file, format="mp3")
    print(f"✅ TTS 음성 파일이 생성되었습니다: {output_file}")

    # 파일 경로와 앞부분 duration 배열 반환
    return output_file, front_durations


# Whisper 모델을 통해 오디오의 앞부분 duration과 각 타이밍을 분석하고 출력하는 함수
def analyze_audio_with_whisper(audio_file):
    model = whisper.load_model("medium")
    result = model.transcribe(audio_file, word_timestamps=True)

    print(f"\n🔍 [Whisper 분석 결과: {audio_file}] 🔍")
    for idx, segment in enumerate(result["segments"]):
        start = round(segment["start"], 2)
        end = round(segment["end"], 2)
        text = segment["text"]
        print(f"⏱ 세그먼트 {idx}: {start}s ~ {end}s | 텍스트: {text}")

    first_segment = result["segments"][0]
    duration = round(first_segment["end"] - first_segment["start"], 2)
    return duration


# 🔹 테스트 실행
# subtitles = [
#     "코드를 작성할 때 주석을 충분히 달지 않는 실수를 종종 합니다.",
#     "변수명을 명확하지 않게 지어서 나중에 혼란을 겪게 되죠.",
#     "백업 없이 중요한 코드를 수정하는 경우가 많습니다.",
#     "에러 메시지를 제대로 읽지 않고 넘어가는 경우도 흔해요."
# ]

# subtitles2 = [
#     "동해물과 백두산이 마르고 닳도록.",
#     "하느님이 보우하사 우리나라 만세.",
#     "무궁화 삼천리 화려강산",
#     "대한사람 대한으로 길이 보전하세"
# ]

# text_to_speech(subtitles)
# text_to_speech(subtitles2)


# {
#   "videos": ["video1.mp4", "video2.mp4"],
#   "subtitles": [
#     "코드를 작성할 때 주석을 충분히 달지 않는 실수를 종종 합니다.",
#     "변수명을 명확하지 않게 지어서 나중에 혼란을 겪게 되죠."],
#   "music_url": "bgm_01.mp3"
# }
