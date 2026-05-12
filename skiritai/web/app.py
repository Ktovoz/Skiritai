"""FastAPI application factory for Skiritai web server."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from skiritai.core.agent_loop import register_all_tools
from skiritai.web.routers import cases, ws


def create_app(cases_root: Path | None = None, llm=None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        cases_root: Root directory containing case folders. If None, reads
            from SKIRITAI_CASES_ROOT env var, falling back to ``<cwd>/examples``.
        llm: Optional LLM provider instance shared by all API requests.
            If None, auto-detects from environment variables.
    """
    # Explicitly register all tools at startup (Playwright + perception)
    register_all_tools()

    # Resolve cases root: argument > env var > default
    if cases_root is None:
        env_root = os.getenv("SKIRITAI_CASES_ROOT")
        cases_root = Path(env_root) if env_root else Path.cwd() / "examples"

    # Inject into router module
    cases.set_cases_root(cases_root)
    if llm is not None:
        cases.set_llm(llm)

    app = FastAPI(title="Skiritai", description="AI 驱动的测试自动化智能体")

    cors_origins_str = (
            os.getenv("SKIRITAI_CORS_ORIGINS")
            or os.getenv("CORS_ALLOWED_ORIGINS")
            or "http://localhost:5173,http://localhost:5174,http://localhost:5175"
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

    return app
