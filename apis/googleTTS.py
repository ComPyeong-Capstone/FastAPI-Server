import os
from google.cloud import texttospeech
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/whdtn/Desktop/compyeong-capstone-c40d6f9bab98.json"

def text_to_speech(text, output_file=os.path.expanduser("~/Desktop/FASTAPI-SERVER/TTSfile/tts_output.mp3")):
    try:
        # 클라이언트 생성
        client = texttospeech.TextToSpeechClient()

        # 요청 설정
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Wavenet-B",   #ko-KR-Wavenet-B 여자, ko-KR-Wavenet-C 남자  
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate = 1.25
            )

        # API 호출
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # 파일 저장
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            print(f"✅ 파일이 바탕화면에 저장됨: {output_file}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

# 실행
text_to_speech("안녕하세요! 구글 TTS API를 사용해 보세요.")
