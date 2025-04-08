import os
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# ✅ 문장 반 나누는 자막 생성 함수
def create_video_with_split_subtitles(video_filenames, subtitles, durations, font_path, font_size, text_color, subtitle_y_position):
    """
    비디오 파일들과 자막(문장 리스트)과 각 자막 duration을 받아
    문장 반 나눠서 자막을 입힌 비디오 클립 리스트를 반환하는 함수.
    """
    video_clips = []

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")
        
        clip = VideoFileClip(video_path)
        subtitle_text = subtitles[idx]
        words = subtitle_text.strip().split()
        half = (len(words) + 1) // 2

        first_sub = " ".join(words[:half])
        second_sub = " ".join(words[half:])

        duration = durations[idx]

        first_subtitle = (
            TextClip(
                first_sub,
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, 100 + 50),
                method='caption'
            )
            .set_position(("center", clip.h + subtitle_y_position))
            .set_start(0)
            .set_duration(duration)
        )

        second_subtitle = (
            TextClip(
                second_sub,
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, 100 + 50),
                method='caption'
            )
            .set_position(("center", clip.h + subtitle_y_position))
            .set_start(duration)
            .set_duration(clip.duration - duration)
        )

        video_with_subtitles = CompositeVideoClip([clip, first_subtitle, second_subtitle])
        video_clips.append(video_with_subtitles)

    return video_clips


# ✅ 단어별로 튀어나오는 자막 생성 함수
def create_video_with_word_subtitles(video_filenames, subtitles, font_path, font_size, text_color, subtitle_y_position):
    """
    비디오 파일들과 자막(문장 리스트)을 받아
    단어별로 튀어나오는 애니메이션 자막을 입힌 비디오 클립 리스트를 반환하는 함수.
    """
    video_clips = []

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")
        
        clip = VideoFileClip(video_path)
        subtitle_text = subtitles[idx]
        words = subtitle_text.strip().split()

        word_clips = []

        for word_idx, word in enumerate(words):
            txt = TextClip(
                word,
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, None),
                method='caption'
            ).set_position(("center", clip.h + subtitle_y_position))

            pop = txt.resize(lambda t: 0.3 + 0.7 * (t / 0.2) if t < 0.2 else 1)

            start_time = word_idx * 0.5
            duration = 0.5

            pop = pop.set_start(start_time).set_duration(duration)
            word_clips.append(pop)

        video_with_word_subtitles = CompositeVideoClip([clip] + word_clips)
        video_clips.append(video_with_word_subtitles)

    return video_clips
