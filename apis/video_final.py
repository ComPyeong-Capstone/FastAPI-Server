# 사용자의 입력을 통해 영상 합치기 / 음악, 자막, tts 입히기 작업을 진행해 최종 결과물 영상을 반환
from fastapi import APIRouter
from typing import List, Union
import os
from pydantic import BaseModel
from moviepy.editor import CompositeAudioClip, concatenate_videoclips, AudioFileClip, VideoFileClip
from apis import googleTTS as tts
from apis import create_subtitle
from dotenv import load_dotenv
import asyncio

router = APIRouter()
load_dotenv()
SERVER_HOST = os.getenv("SERVER_HOST")

class FinalVideoRequest(BaseModel):
    videos: List[str]
    subtitles: Union[List[str], List[List[str]]]
    music_url: str
    font_path: str
    font_effect: str
    font_color: str
    subtitle_y_position: str

# 최종 비디오 생성 함수
async def create_final_video(
    video_filenames: List[str],
    subtitles: List[str],
    music_url: str,
    font_path: str,
    font_effect: str,
    font_color: str,
    subtitle_y_position: str
):
    # ✅ 해상도 기준으로 자막 크기 및 위치 계산 (첫 번째 영상 기준)
    filename = video_filenames[0]
    if not filename.endswith(".mp4"):
        filename += ".mp4"
    video_path = os.path.join("videos", filename)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"❌ Video file not found: {video_path}")

    subtitle_y_positions = []
    font_sizes = []
    for filename in video_filenames:
        video_path = os.path.join("videos", filename)
        clip = VideoFileClip(video_path)
        h = clip.h
        f_size = int(h*0.03)
        if subtitle_y_position == "center":
            y_ratio = 0.425
        elif subtitle_y_position == "bottom":
            y_ratio = 0.75
        elif subtitle_y_position == "top":
            y_ratio = 0.1
        y_pos = int(h * y_ratio - f_size * 0.5)
        font_sizes.append(f_size)          # 해상도 기반 폰트 크기
        subtitle_y_positions.append(y_pos)
        clip.close()
    
    video_clips = []
    if font_effect == "poping":
        tts_audio_path, durations = await tts.text_to_speech_with_poping(subtitles)
        video_clips = create_subtitle.create_video_with_word_subtitles(
            video_filenames, subtitles, durations, font_path, font_sizes, font_color, subtitle_y_positions)
    elif font_effect == "split":
        tts_audio_path, durations = await tts.text_to_speech(subtitles)
        video_clips = create_subtitle.create_video_with_split_subtitles(
            video_filenames, subtitles, durations, font_path, font_sizes, font_color, subtitle_y_positions)
    elif font_effect == "custom_poping":
        tts_audio_path, word_timings_list = await tts.text_to_speech_with_poping([" ".join(chunks) for chunks in subtitles])
        video_clips = create_subtitle.create_video_with_custom_chunks(
            video_filenames, subtitles, word_timings_list, font_path, font_sizes, font_color, subtitle_y_positions)

    # ✅ 모든 비디오 클립 이어 붙이기
    final_video = concatenate_videoclips(video_clips, method="compose")

    # ✅ 배경음악 로드
    music_path = os.path.join("music", music_url)
    bgm_audio = AudioFileClip(music_path).volumex(0.2)

    # ✅ TTS 로드
    tts_audio = AudioFileClip(tts_audio_path)

    # ✅ 두 오디오를 합침
    combined_audio = CompositeAudioClip([bgm_audio, tts_audio]).set_duration(final_video.duration)

    # ✅ 임시 TTS 파일 삭제
    if os.path.exists(tts_audio_path):
        os.remove(tts_audio_path)

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
    final_video = await create_final_video(
        request.videos,
        request.subtitles,
        request.music_url,
        request.font_path,
        request.font_effect,
        request.font_color,
        request.subtitle_y_position
    )

    final_video_path = f"http://{SERVER_HOST}/videos/{final_video}"
    return {"final_video_url": final_video_path}
