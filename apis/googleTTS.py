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


def text_to_speech_with_poping(text_list):
    """
    텍스트 리스트를 받아 TTS 오디오 파일 생성 + 단어별 타이밍 분석 (poping 스타일)
    반환: (TTS 파일 경로, 모든 단어 타이밍 리스트)
    """
    if not isinstance(text_list, list):
        raise ValueError("입력은 리스트 형식이어야 합니다.")

    combined_audio = AudioSegment.silent(duration=0)
    start_time = 0  # milliseconds
    interval = 5000  # 5초 간격
    all_word_timings = []

    for idx, text in enumerate(text_list):
        # TTS 생성
        tts_data = generate_tts(text)
        merged_temp_path = os.path.join(output_folder, f"temp_merged_{idx}.mp3")
        with open(merged_temp_path, "wb") as f:
            f.write(tts_data)

        tts_audio = AudioSegment.from_mp3(merged_temp_path)

        # Whisper 분석
        word_timings = analyze_audio_words_with_whisper(merged_temp_path)

        # 🔧 start_time 보정은 오디오 결합 전에 적용해야 정확
        adjusted_word_timings = []
        for w in word_timings:
            adjusted_word_timings.append({
                "word": w["word"],
                "start": round(w["start"] + start_time / 1000, 2),
                "end": round(w["end"] + start_time / 1000, 2)
            })

        all_word_timings.append(adjusted_word_timings)

        # 디버깅 출력
        print(f"\n🧾 [인덱스 {idx}] 보정된 단어 타이밍:")
        for word_info in adjusted_word_timings:
            print(f"🗣 {word_info['word']} | ⏱ {word_info['start']}s ~ {word_info['end']}s | 길이: {round(word_info['end'] - word_info['start'], 2)}s")

        # 무음 gap 삽입
        silent_gap = AudioSegment.silent(duration=max(0, start_time - len(combined_audio)))
        if start_time >= 5000:
            silent_gap += AudioSegment.silent(duration=500)

        combined_audio += silent_gap + tts_audio

        # start_time 갱신은 마지막에!
        start_time += interval

        os.remove(merged_temp_path)

    # 최종 길이 정리
    final_length_ms = ((len(combined_audio) + 4999) // 5000) * 5000
    if len(combined_audio) < final_length_ms:
        combined_audio += AudioSegment.silent(duration=final_length_ms - len(combined_audio))

    output_file = os.path.join(output_folder, get_next_filename())
    combined_audio.export(output_file, format="mp3")
    print(f"✅ Poping 스타일 TTS 음성 파일이 생성되었습니다: {output_file}")

    return output_file, all_word_timings



# Whisper 모델을 통해 오디오의 앞부분 duration과 각 타이밍을 분석하고 출력하는 함수
def analyze_audio_with_whisper(audio_file):
    model = whisper.load_model("base") #whisper model : tiny, base, small, medium, large
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



def analyze_audio_words_with_whisper(audio_file):
    """
    🔍 주어진 오디오 파일을 Whisper로 분석해서
    단어 단위 (word-level)로 (단어, 시작시간, 끝시간) 정보를 리스트로 반환하는 함수.

    Args:
        audio_file (str): 분석할 오디오 파일 경로 (.mp3)

    Returns:
        List[dict]: 각 단어별 정보 리스트
            예: [{"word": "Hello", "start": 0.5, "end": 0.8}, ...]
    """

    # Whisper 모델 로드 (medium 모델 사용)
    model = whisper.load_model("base")  #whisper model : tiny, base, small, medium, large

    # 오디오를 word timestamps 옵션을 켜고 변환
    result = model.transcribe(audio_file, word_timestamps=True)

    word_timings = []

    # Whisper 결과 중 segments를 순회
    for segment in result["segments"]:
        if "words" in segment:
            for word_info in segment["words"]:
                word = word_info.get("word", "").strip()
                start = round(word_info.get("start", 0), 2)
                end = round(word_info.get("end", 0), 2)
                word_timings.append({
                    "word": word,
                    "start": start,
                    "end": end
                })

    return word_timings




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



# 1. 테스트할 문장
# text = "코드를 작성할 때 주석을 충분히 달지 않는 실수를 종종 합니다."

# # 2. TTS 생성
# tts_data = generate_tts(text)

# # mp3 파일로 저장
# test_audio_path = os.path.join(output_folder, "test_tts.mp3")
# with open(test_audio_path, "wb") as f:
#     f.write(tts_data)

# # 3. 단어별 읽는 시간 분석
# word_timings = analyze_audio_words_with_whisper(test_audio_path)

# # 4. 결과 출력
# for info in word_timings:
#     print(f"🗣 단어: {info['word']} | 시작: {info['start']}s | 끝: {info['end']}s | 길이: {round(info['end'] - info['start'], 2)}s")
