FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
RUN sed -i 's|deb.debian.org/debian|mirrors.cloud.tencent.com/debian|g; s|security.debian.org/debian-security|mirrors.cloud.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends fontconfig fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /tmp/automation-platform-transfers /var/lib/cling-learning \
    && chown -R app:app /tmp/automation-platform-transfers /var/lib/cling-learning \
    && chmod 700 /tmp/automation-platform-transfers /var/lib/cling-learning

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
    -i https://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    -r /app/requirements.txt

COPY backend/app /app/app

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
