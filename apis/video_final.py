# 사용자의 입력을 통해 영상 합치기 / 음악, 자막, tts 입히기 작업을 진행해 최종 결과물 영상을 반환
from fastapi import APIRouter
from typing import List
import os
from pydantic import BaseModel
from moviepy.editor import CompositeAudioClip
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip
from apis import googleTTS as tts
from apis import create_subtitle
router = APIRouter()

class FinalVideoRequest(BaseModel):
    videos: List[str]
    subtitles: List[str]
    music_url: str
    font_path: str
    font_effect: str
    font_color: str
    subtitle_y_position: int

# 최종 비디오 생성 함수
def create_final_video(video_filenames: List[str], 
                       subtitles: List[str], 
                       music_url: str,
                       font_path: str,
                       font_effect: str,
                       font_color: str,
                       subtitle_y_position: int):

    font_size = 30
    video_clips = []
    if(font_effect == "poping"):
        tts_audio_path, durations = tts.text_to_speech_with_poping(subtitles)
        video_clips = create_subtitle.create_video_with_word_subtitles(video_filenames, subtitles, durations,font_path, font_size, font_color, subtitle_y_position)
    elif font_effect == "split":
        tts_audio_path, durations = tts.text_to_speech(subtitles)
        video_clips = create_subtitle.create_video_with_split_subtitles(video_filenames, subtitles, durations, font_path, font_size, font_color, subtitle_y_position)


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
    base_filename = "final_video"
    ext = ".mp4"
    i = 1
    while os.path.exists(os.path.join("videos", f"{base_filename}_{i}{ext}")):
        i += 1
    output_filename = f"{base_filename}_{i}{ext}"
    output_path = os.path.join("videos", output_filename)

    final_video_with_bgm.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast")

    return output_filename

# FastAPI 엔드포인트
@router.post("/")
async def generate_final_video(request: FinalVideoRequest):

    final_video = create_final_video(
        request.videos,
        request.subtitles,
        request.music_url,
        request.font_path,
        request.font_effect,
        request.font_color,
        request.subtitle_y_position
    )

    final_video_path = f"http://127.0.0.1:8000/videos/{final_video}"
    return {"final_video_url": final_video_path}
