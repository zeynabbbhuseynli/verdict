FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    google-generativeai==0.8.3 \
    langgraph==0.2.53 \
    "sqlalchemy[asyncio]==2.0.36" \
    asyncpg==0.30.0 \
    "redis[asyncio]==5.2.0" \
    httpx==0.27.2 \
    pydantic==2.10.0 \
    python-multipart==0.0.12 \
    python-dotenv==1.0.1

COPY verdict/ ./verdict/

CMD ["uvicorn", "verdict.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
