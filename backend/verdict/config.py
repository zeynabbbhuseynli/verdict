import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://verdict:verdictpass@localhost/verdict")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
MODEL = "gemini-1.5-flash"
