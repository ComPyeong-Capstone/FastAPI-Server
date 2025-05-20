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
    자연스럽게 병합된 단어 자막을 영상에 입히는 함수
    """
    video_clips = []
    interval = 5  # 각 클립의 예상 재생 시간 간격 (초 단위) — TTS 기준

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")

        clip = VideoFileClip(video_path)
        subtitle_text = subtitles[idx].strip()
        subtitle_words = subtitle_text.split()
        whisper_word_timings = word_timings_list[idx]

        # 1. Whisper-자막 정렬
        aligned_word_timings = align_words_with_timings_split(subtitle_words, whisper_word_timings)

        # 2. 자연스럽게 병합
        merged_word_timings = merge_natural_korean_phrases(aligned_word_timings)

        print(f"\n🧾 [인덱스 {idx}] 병합 전 단어 리스트:")
        for w in aligned_word_timings:
            print(f" - {w['word']} | {w['start']} ~ {w['end']}")

        print(f"\n🧾 [인덱스 {idx}] 병합 후 자막 리스트:")
        for w in merged_word_timings:
            print(f"📝 {w['word']} | {w['start']} ~ {w['end']}")


        # 3. 자막 클립 생성
        clip_start_time = idx * interval
        word_clips = []

        for word_info in merged_word_timings:
            global_start = word_info["start"]
            global_end = word_info["end"]
            local_start = round(global_start - clip_start_time, 2)
            local_end = round(global_end - clip_start_time, 2)
            duration = round(local_end - local_start, 2)

            # 영상 범위 벗어난 자막 제거
            if local_start < 0 or local_start >= clip.duration:
                continue
            if local_end > clip.duration:
                local_end = clip.duration
                duration = round(local_end - local_start, 2)

            txt = TextClip(
                word_info["word"],
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, 200),
                method='caption'
            ).set_position(("center", clip.h + subtitle_y_position))

            pop = txt.resize(lambda t: 0.3 + 0.7 * (t / 0.2) if t < 0.2 else 1)
            pop = pop.set_start(local_start).set_duration(duration)
            pop = pop.set_start(local_start).set_duration(duration)
            word_clips.append(pop)

        # 영상 + 자막 합성
        final = CompositeVideoClip([clip] + word_clips).set_duration(clip.duration)
        video_clips.append(final)

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


def merge_natural_korean_phrases(word_timings):
    """
    자연스러운 의미 단위로 자막 병합 (조사 끝 단어 병합 금지, 조사 단어는 앞 단어에 병합)
    """
    merged = []
    i = 0
    josa_list = ["을", "를", "이", "가", "은", "는", "에", "에서", "으로", "와", "과", "도", "만", "부터", "까지", "처럼", "보다"]

    while i < len(word_timings):
        current = word_timings[i]
        curr_word = current["word"].strip()

        if i == len(word_timings) - 1:
            merged.append(current)
            break

        next_word_obj = word_timings[i + 1]
        next_word = next_word_obj["word"].strip()

        def should_merge(prev, curr):
            # 쉼표 있는 단어는 병합 금지
            if "," in prev or "," in curr:
                return False
            # 앞 단어가 조사로 끝나는 경우 병합 금지
            if any(prev.endswith(josa) for josa in josa_list):
                return False
            # 뒷 단어가 조사 하나면 병합 (예: "을")
            if curr in josa_list:
                return True
            # 둘 다 짧은 단어면 병합 허용
            if len(prev) <= 6 and len(curr) <= 6:
                return True
            return False

        if should_merge(curr_word, next_word):
            merged.append({
                "word": f"{curr_word} {next_word}",
                "start": current["start"],
                "end": next_word_obj["end"]
            })
            i += 2
        else:
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


def create_video_with_custom_chunks(video_filenames, subtitle_chunks_list, whisper_word_timings_list, font_path, font_size, text_color, subtitle_y_position):
    """
    사용자가 직접 정의한 자막 덩어리 리스트를 기반으로 poping 애니메이션 자막을 생성하는 함수.
    Whisper 단어 타이밍과 매칭하여 각 덩어리의 시작/끝 시간으로 자막 처리.

    Args:
        video_filenames (List[str]): 비디오 파일명 리스트
        subtitle_chunks_list (List[List[str]]): 각 문장에 대해 사용자가 나눈 자막 덩어리 리스트
        whisper_word_timings_list (List[List[dict]]): Whisper로 분석된 단어별 타이밍 리스트
        font_path (str): 폰트 이름
        font_size (int): 글자 크기
        text_color (str): 글자 색
        subtitle_y_position (int): 자막 Y축 위치 오프셋

    Returns:
        List[VideoClip]: 자막이 입혀진 비디오 클립 리스트
    """
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

    interval = 5  # 각 클립의 시작 시간 오프셋
    video_clips = []

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")

        clip = VideoFileClip(video_path)
        subtitle_chunks = subtitle_chunks_list[idx]
        whisper_word_timings = whisper_word_timings_list[idx]

        # 사용자 자막 덩어리를 Whisper 타이밍과 매칭
        aligned_chunks = align_custom_subtitles_with_timings(subtitle_chunks, whisper_word_timings)

        print(f"\n🧾 [인덱스 {idx}] 사용자 정의 자막 타이밍:")
        for w in aligned_chunks:
            print(f"📝 {w['word']} | {w['start']} ~ {w['end']}")

        # 자막 클립 생성
        clip_start_time = idx * interval
        word_clips = []

        for chunk in aligned_chunks:
            global_start = chunk["start"]
            global_end = chunk["end"]
            local_start = round(global_start - clip_start_time, 2)
            local_end = round(global_end - clip_start_time, 2)
            duration = round(local_end - local_start, 2)

            # 범위 벗어나는 자막 제외
            if local_start < 0 or local_start >= clip.duration:
                continue
            if local_end > clip.duration:
                local_end = clip.duration
                duration = round(local_end - local_start, 2)

            txt = TextClip(
                chunk["word"],
                fontsize=font_size,
                color=text_color,
                font=font_path,
                size=(clip.w, 150),
                method='caption'
            ).set_position(("center", clip.h + subtitle_y_position))

            pop = txt.resize(lambda t: 0.3 + 0.7 * (t / 0.2) if t < 0.2 else 1)
            pop = pop.set_start(local_start).set_duration(duration)
            word_clips.append(pop)

        # 영상과 자막 합성
        final = CompositeVideoClip([clip] + word_clips).set_duration(clip.duration)
        video_clips.append(final)

    return video_clips

def align_custom_subtitles_with_timings(subtitle_chunks, whisper_word_timings):
    aligned_chunks = []
    whisper_idx = 0
    last_end_time = whisper_word_timings[-1]["end"] if whisper_word_timings else 0.0

    for chunk in subtitle_chunks:
        chunk_words = chunk.strip().split()
        chunk_len = len(chunk_words)
        matched_words = []

        while whisper_idx < len(whisper_word_timings) and len(matched_words) < chunk_len:
            matched_words.append(whisper_word_timings[whisper_idx])
            whisper_idx += 1

        # ✅ 매칭된 것이 있으면 정상 처리
        if matched_words:
            start_time = matched_words[0]["start"]
            end_time = matched_words[-1]["end"]
            aligned_chunks.append({
                "word": chunk,
                "start": round(start_time, 2),
                "end": round(end_time, 2)
            })
        else:
            # ✅ Whisper 타이밍이 끝났지만 자막이 남은 경우 → 마지막 시간 이후로 처리
            aligned_chunks.append({
                "word": chunk,
                "start": round(last_end_time, 2),
                "end": round(last_end_time + 0.5, 2)  # 대략적인 길이 할당
            })
            last_end_time += 0.5  # 다음 자막을 위해 오프셋 이동

    return aligned_chunks


#사실상 기존과 동일
def create_video_with_poping_subtitles(video_filenames, subtitles, word_timings_list, font_path, font_size, text_color, subtitle_y_position):
    """
    글자가 작게 시작해서 커지는 팝업 애니메이션을 적용하되 선명도를 유지한 버전
    """
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

    video_clips = []
    interval = 5

    for idx, video_filename in enumerate(video_filenames):
        video_path = os.path.join("videos", video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"{video_path} 파일이 존재하지 않습니다.")

        clip = VideoFileClip(video_path)
        subtitle_text = subtitles[idx].strip()
        subtitle_words = subtitle_text.split()
        whisper_word_timings = word_timings_list[idx]

        aligned_word_timings = align_words_with_timings_split(subtitle_words, whisper_word_timings)
        merged_word_timings = merge_natural_korean_phrases(aligned_word_timings)

        word_clips = []
        clip_start_time = idx * interval

        for word_info in merged_word_timings:
            global_start = word_info["start"]
            global_end = word_info["end"]
            local_start = round(global_start - clip_start_time, 2)
            local_end = round(global_end - clip_start_time, 2)
            duration = round(local_end - local_start, 2)

            if local_start < 0 or local_start >= clip.duration:
                continue
            if local_end > clip.duration:
                local_end = clip.duration
                duration = round(local_end - local_start, 2)

            # 고해상도로 텍스트 렌더링 후 절반 크기로 기본 사이즈 설정
            txt = TextClip(
                word_info["word"],
                fontsize=font_size * 2,
                color=text_color,
                font=font_path,
                size=(clip.w * 2, 300),
                method='caption'
            ).resize(0.5).set_position(("center", clip.h + subtitle_y_position))

            # 팝업 애니메이션 적용 (선명도 유지)
            pop = txt.resize(lambda t: 0.3 + 0.7 * (t / 0.2) if t < 0.2 else 1)
            pop = pop.set_start(local_start).set_duration(duration)
            word_clips.append(pop)

        final = CompositeVideoClip([clip] + word_clips).set_duration(clip.duration)
        video_clips.append(final)

    return video_clips


