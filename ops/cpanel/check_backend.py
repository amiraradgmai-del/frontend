from __future__ import annotations

from app.core.config import get_settings
from app.main import create_app


def main() -> None:
    settings = get_settings()
    app = create_app(settings)
    print(
        {
            "environment": settings.environment,
            "database": settings.database_url.startswith("sqlite:"),
            "routes": len(app.routes),
        }
    )


if __name__ == "__main__":
    main()
