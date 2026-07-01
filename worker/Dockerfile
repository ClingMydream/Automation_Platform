FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
    -i https://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    -r /app/requirements.txt

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.cloud.tencent.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.cloud.tencent.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && python -m playwright install --with-deps --no-shell chromium \
    && chmod -R a+rX /ms-playwright

RUN python - <<'PY'
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

url = "https://playwright.download.prss.microsoft.com/dbazure/download/playwright/builds/chromium/1148/chromium-headless-shell-linux.zip"
archive = Path("/tmp/chromium-headless-shell-linux.zip")
target = Path("/ms-playwright/chromium_headless_shell-1148")
with urlopen(url, timeout=120) as response:
    archive.write_bytes(response.read())
target.mkdir(parents=True, exist_ok=True)
with ZipFile(archive) as zip_file:
    zip_file.extractall(target)
archive.unlink()
PY
RUN chmod -R a+rX /ms-playwright \
    && chmod +x /ms-playwright/chromium_headless_shell-1148/chrome-linux/headless_shell

COPY worker/app /app/app

USER app

CMD ["python", "-m", "app.worker"]
