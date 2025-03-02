# 사용자의 입력을 통해 영상 합치기 / 음악, 자막, tts 입히기 작업을 진행해 최종 결과물 영상을 반환
from fastapi import APIRouter
from typing import List
import requests
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, AudioFileClip
from gtts import gTTS

router = APIRouter()

# 비디오 다운로드 함수
def download_video(video_url: str, save_path: str):
    response = requests.get(video_url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        return save_path
    return None

# TTS 생성 함수
def generate_tts(subtitle: str, output_path: str):
    tts = gTTS(text=subtitle, lang="en")
    tts.save(output_path)
    return output_path

# 최종 비디오 생성 함수
def create_final_video(video_urls: List[str], subtitles: List[str], music_url: str):
    video_clips = []
    temp_files = []  # 다운로드한 파일 저장

    # 비디오 다운로드 및 VideoFileClip 변환
    for idx, video_url in enumerate(video_urls):
        video_path = f"temp_video_{idx}.mp4"
        download_video(video_url, video_path)
        clip = VideoFileClip(video_path)
        
        # 자막 추가
        text_clip = TextClip(subtitles[idx], fontsize=40, color='white').set_position(('center', 'bottom')).set_duration(clip.duration)
        video_with_subtitle = CompositeVideoClip([clip, text_clip])

        # TTS 음성 생성 및 추가
        tts_path = f"tts_audio_{idx}.mp3"
        generate_tts(subtitles[idx], tts_path)
        tts_audio = AudioFileClip(tts_path).set_duration(video_with_subtitle.duration)
        video_with_audio = video_with_subtitle.set_audio(tts_audio)

        video_clips.append(video_with_audio)
        temp_files.extend([video_path, tts_path])  # 삭제할 파일 저장

    # 모든 비디오 합치기
    final_video = concatenate_videoclips(video_clips, method="compose")

    # 배경 음악 추가
    music_path = "temp_music.mp3"
    download_video(music_url, music_path)
    bgm_audio = AudioFileClip(music_path).set_duration(final_video.duration)
    final_video_with_bgm = final_video.set_audio(bgm_audio)

    # 최종 비디오 저장
    output_path = "final_video.mp4"
    final_video_with_bgm.write_videofile(output_path, codec="libx264", audio_codec="aac")

    # 임시 파일 삭제
    for file in temp_files + [music_path]:
        if os.path.exists(file):
            os.remove(file)

    return output_path

# FastAPI 엔드포인트
@router.post("/")
async def generate_final_video(videos: List[str], subtitles: List[str], music_url: str):
    if not (6 <= len(videos) <= 12 and 6 <= len(subtitles) <= 12):
        return {"error": "비디오와 자막 개수는 6~12개여야 합니다."}

    final_video_path = create_final_video(videos, subtitles, music_url)

    return {"final_video_url": final_video_path}
