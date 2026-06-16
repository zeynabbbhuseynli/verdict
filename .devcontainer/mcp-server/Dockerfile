FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.32.0

COPY verdict_sift_server/ ./verdict_sift_server/

CMD ["uvicorn", "verdict_sift_server.server:app", "--host", "0.0.0.0", "--port", "8001"]
