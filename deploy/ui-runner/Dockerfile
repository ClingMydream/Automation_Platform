FROM python:3.12-slim

WORKDIR /app
RUN sed -i 's|deb.debian.org/debian|mirrors.cloud.tencent.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends chromium ffmpeg fonts-noto-cjk \
    && mkdir -p /root/.cache/ms-playwright/ffmpeg-1011 \
    && ln -s /usr/bin/ffmpeg /root/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple \
    fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 playwright==1.55.0
COPY deploy/ui-runner/runner.py /app/runner.py

EXPOSE 8090
CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "8090"]
