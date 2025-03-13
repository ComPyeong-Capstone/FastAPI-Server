# 사용자의 입력을 통해 영상 합치기 / 음악, 자막, tts 입히기 작업을 진행해 최종 결과물 영상을 반환
from fastapi import APIRouter
from typing import List
import os
import requests
import base64
import json
from pydantic import BaseModel
from moviepy.editor import CompositeAudioClip
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip
from apis import googleTTS as tts

router = APIRouter()

class FinalVideoRequest(BaseModel):
    videos: List[str]
    subtitles: List[str]
    music_url: str




# 최종 비디오 생성 함수
def create_final_video(video_filenames: List[str], subtitles: List[str], music_url: str):
    video_clips = []

    tts_audio_path = tts.text_to_speech(subtitles)

    FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"  # ✅ 한글 폰트 지원
    FONT_SIZE = 50
    TEXT_COLOR = "white"
    TEXT_BOX_HEIGHT = 100  # 자막 높이 조절
    SUBTITLE_Y_POSITION = -150  # 하단에서 150px 위 (음.. 너가 원하면 조정 가능!)

    # 비디오 다운로드 및 VideoFileClip 변환
    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")
        
        # 비디오 클립 생성
        clip = VideoFileClip(video_path)

        # 자막 텍스트 생성
        subtitle_text = subtitles[idx]  # ✅ 각 영상마다 자막 하나씩 대응
        subtitle = (
            TextClip(
                subtitle_text,
                fontsize=FONT_SIZE,
                color=TEXT_COLOR,
                font=FONT_PATH,
                size=(clip.w, TEXT_BOX_HEIGHT + 50),  # ✅ 자막 박스 가로 크기와 높이
                method='caption'  # ✅ 자동 줄바꿈 지원 (긴 문장 대응)
            )
            .set_position(("center", clip.h + SUBTITLE_Y_POSITION))  # ✅ 위치 설정
            .set_duration(clip.duration)  # ✅ 클립 길이 동안 자막 유지
        )

        # 자막을 비디오에 합성
        video_with_subtitle = CompositeVideoClip([clip, subtitle])

        video_clips.append(video_with_subtitle)

    # ✅ 모든 비디오 클립 이어 붙이기
    final_video = concatenate_videoclips(video_clips, method="compose")

    # ✅ 배경음악 로드
    music_path = os.path.join("music", music_url)
    bgm_audio = AudioFileClip(music_path).volumex(0.2)  # 배경음 줄이기

    # ✅ TTS 로드
    tts_audio = AudioFileClip(tts_audio_path)

    # ✅ 두 오디오를 합침
    combined_audio = CompositeAudioClip([bgm_audio, tts_audio]).set_duration(final_video.duration)

    # ✅ 최종 오디오 삽입
    final_video_with_bgm = final_video.set_audio(combined_audio)

    # ✅ 최종 비디오 저장 (videos 폴더에 저장)
    if not os.path.exists("videos"):
        os.makedirs("videos")

    output_filename = "final_video.mp4"
    output_path = os.path.join("videos", output_filename)

    final_video_with_bgm.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast")

    return output_filename

# FastAPI 엔드포인트
@router.post("/")
async def generate_final_video(request: FinalVideoRequest):

    final_video = create_final_video(
        request.videos,
        request.subtitles,
        request.music_url
    )

    final_video_path = f"http://127.0.0.1:8000/videos/{final_video}"
    return {"final_video_url": final_video_path}
