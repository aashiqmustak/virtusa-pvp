FROM python:3.12-slim
WORKDIR /workspace/server
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server .
COPY fixtures /workspace/fixtures
COPY policy.demo.json /workspace/policy.demo.json
RUN useradd --create-home desk && mkdir -p /data/uploads && chown -R desk:desk /data /workspace
USER desk
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--ws-max-size","65536"]
