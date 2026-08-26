FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1
COPY deploy/ui-runner/runner.py /app/runner.py

EXPOSE 8090
CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "8090"]
