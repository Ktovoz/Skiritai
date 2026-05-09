import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logger import logger
from app.engine.agent_loop import register_all_tools
from app.routers import cases, ws

# Explicitly register all tools at startup (Playwright + perception)
register_all_tools()

app = FastAPI(title="Skiritai", description="AI 驱动的测试自动化智能体")

cors_origins_str = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175",
)
allow_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
