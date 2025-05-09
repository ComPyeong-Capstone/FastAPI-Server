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
def create_video_with_word_subtitles(video_filenames, subtitles, word_timings_list, font_path, font_size, text_color, subtitle_y_position):
    """
    비디오 파일들과 Whisper로 분석한 단어별 타이밍 리스트를 받아
    단어별로 튀어나오는 애니메이션 자막을 입힌 비디오 클립 리스트를 반환하는 함수.
    """
    video_clips = []
    interval = 5  # 각 클립의 예상 재생 시간 간격 (초 단위) — TTS 기준

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")

        clip = VideoFileClip(video_path)

        subtitle_text = subtitles[idx]
        subtitle_words = subtitle_text.strip().split()
        whisper_word_timings = word_timings_list[idx]

        # 🟡 전체 TTS 오디오 기준의 자막 시간을, 현재 영상 기준으로 변환
        clip_start_time = idx * interval  # 초 단위 오프셋
        aligned_word_timings = align_words_with_timings_split(subtitle_words, whisper_word_timings)
        merged_word_timings = merge_short_words(aligned_word_timings)

        word_clips = []

        for idx_word, word_info in enumerate(aligned_word_timings):
            word = word_info["word"]
            global_start = word_info["start"]

            # 다음 단어가 있다면, 그 단어의 시작 시간까지 지속
            if idx_word < len(aligned_word_timings) - 1:
                global_end = aligned_word_timings[idx_word + 1]["start"]
            else:
                # 마지막 단어는 영상 끝까지
                global_end = clip.duration + clip_start_time

            # 🟢 클립 로컬 시간으로 변환
            local_start = round(global_start - clip_start_time, 2)
            local_end = round(global_end - clip_start_time, 2)
            duration = round(local_end - local_start, 2)

            # 🛡️ 잘못된 시간 필터링
            if local_start < 0 or local_start >= clip.duration:
                continue
            if local_end > clip.duration:
                local_end = clip.duration
                duration = round(local_end - local_start, 2)

            txt = TextClip(
                word,
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, None),
                method='caption'
            ).set_position(("center", clip.h + subtitle_y_position))

            pop = txt.resize(lambda t: 0.3 + 0.7 * (t / 0.2) if t < 0.2 else 1)
            pop = pop.set_start(local_start).set_duration(duration)
            word_clips.append(pop)

        # 🧩 자막 + 영상 클립 합치기 (자막이 영상보다 길지 않게)
        video_with_word_subtitles = CompositeVideoClip([clip] + word_clips).set_duration(clip.duration)
        video_clips.append(video_with_word_subtitles)

    return video_clips


def merge_short_words(word_timings):
    """
    Whisper 분석 결과에서 단어가 짧을 경우(6자 이하), 다음 단어와 자막을 병합해 자연스럽게 출력되도록 정리.

    Args:
        word_timings (List[dict]): 단어 단위 Whisper 결과
            예: [{"word": "할", "start": 0.0, "end": 0.3}, ...]

    Returns:
        List[dict]: 병합된 자막 리스트
            예: [{"word": "할 수", "start": 0.0, "end": 0.6}, ...]
    """
    merged = []
    i = 0

    while i < len(word_timings):
        current = word_timings[i]
        current_word = current["word"].strip()
        current_len = len(current_word)

        # 마지막 단어거나 다음 단어가 없음
        if i == len(word_timings) - 1:
            merged.append(current)
            break

        next_word = word_timings[i + 1]["word"].strip()
        next_len = len(next_word)

        # 두 단어 모두 6글자 이하 → 병합
        if current_len <= 6 and next_len <= 6:
            merged_word = f"{current_word} {next_word}"
            merged_clip = {
                "word": merged_word,
                "start": current["start"],
                "end": word_timings[i + 1]["end"]
            }
            merged.append(merged_clip)
            i += 2  # 두 단어 건너뛰기
        else:
            # 병합하지 않고 그대로
            merged.append(current)
            i += 1

    return merged



# 사용자 입력 자막과 whisper모듈이 분석한 자막이 서로 맞지 않아 인덱스 차이와 맞춤법 차이가 발생
#아래 함수 추가하여 tts가 단어를 읽은 시간을 가져오고 자막은 사용자가 입력한 것으로 치환
#아직 싱크가 정확히 맞지도 않고 시간이 너무 길게 뽑힘 테스트 결과 54초 오차범위 2초 -> 오래걸리는 이유는 whisper 모델이 커서. 작은 모델 사용하면 10초 내외
def align_words_with_timings_split(subtitle_words, whisper_words):
    """
    Whisper 단어 구간에 여러 자막 단어가 매핑될 경우 시간 분배 방식으로 정렬
    """
    aligned_words = []
    whisper_idx = 0
    subtitle_idx = 0

    while subtitle_idx < len(subtitle_words) and whisper_idx < len(whisper_words):
        w_sub = subtitle_words[subtitle_idx]
        w_whisper = whisper_words[whisper_idx]["word"]
        start = whisper_words[whisper_idx]["start"]
        end = whisper_words[whisper_idx]["end"]

        # 자막 단어들을 Whisper 단어에 최대한 매핑
        matched = []
        temp_idx = subtitle_idx
        merged = ""

        while temp_idx < len(subtitle_words) and len(merged.replace(" ", "")) < len(w_whisper.replace(" ", "")):
            merged += subtitle_words[temp_idx]
            matched.append(subtitle_words[temp_idx])
            temp_idx += 1

        if len(matched) > 0:
            part_duration = (end - start) / len(matched)
            for i, word in enumerate(matched):
                word_start = round(start + i * part_duration, 2)
                word_end = round(word_start + part_duration, 2)
                aligned_words.append({
                    "word": word,
                    "start": word_start,
                    "end": word_end
                })
            subtitle_idx += len(matched)
        whisper_idx += 1

    return aligned_words