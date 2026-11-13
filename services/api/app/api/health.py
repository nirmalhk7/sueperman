from sqlalchemy import text

from app.schemas import HealthResponse


def register(app, factory, settings):
    @app.get("/api/health", response_model=HealthResponse)
    def health():
        with factory() as s:
            s.execute(text("SELECT 1"))
        return {
            "db": "ok",
            "demo_ready": settings.demo_mode,
            "providers": [
                {"name": "csv", "enabled": True, "configured": True, "healthy": True},
                {"name": "cpsc", "enabled": settings.cpsc_live_enabled, "configured": True},
                {
                    "name": "brightdata",
                    "enabled": settings.brightdata_enabled,
                    "configured": bool(settings.brightdata_api_token),
                },
                {
                    "name": "gemini",
                    "enabled": settings.gemini_enabled,
                    "configured": bool(settings.gemini_api_key),
                },
                {
                    "name": "openai",
                    "enabled": settings.openai_enabled,
                    "configured": bool(settings.openai_api_key),
                },
            ],
        }
