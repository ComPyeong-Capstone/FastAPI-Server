# 1. 베이스 이미지
FROM python:3.10-slim

# 2. 작업 디렉터리
WORKDIR /app

# 3. 필수 파일 복사 후 패키지 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. 전체 프로젝트 복사 (.env는 .dockerignore에서 제외됨)
COPY . .

# 5. 정적 폴더가 존재하지 않으면 에러 → 미리 생성 보장
RUN mkdir -p /app/images /app/videos

# 6. FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
