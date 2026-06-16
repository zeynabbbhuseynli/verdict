from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from verdict.db.database import init_db
from verdict.api.router import router
from verdict.api.websocket import websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VERDICT API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {"name": "VERDICT", "tagline": "Replay the Breach. Cross-Examine the Evidence."}
