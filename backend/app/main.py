from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.base import Base
from app.db.session import engine


def _ensure_sqlite_compatibility() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = {row[1] for row in rows}
        if "password_hash" not in column_names:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
            )

        notif_rows = conn.execute(text("PRAGMA table_info(notification_preferences)")).fetchall()
        notif_cols = {row[1] for row in notif_rows}
        if notif_rows and "timezone" not in notif_cols:
            conn.execute(
                text("ALTER TABLE notification_preferences ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'UTC'")
            )
        if notif_rows and "preferred_weekdays" not in notif_cols:
            conn.execute(
                text("ALTER TABLE notification_preferences ADD COLUMN preferred_weekdays JSON NOT NULL DEFAULT '[]'")
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_compatibility()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
