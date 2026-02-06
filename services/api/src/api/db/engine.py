"""SQLAlchemy engine setup."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from services.api.src.api.config import settings

_engine: Engine | None = None


def get_engine(database_url: str | None = None) -> Engine:
    """Get or create the SQLAlchemy engine."""
    global _engine

    url = database_url or settings.database_url

    if _engine is None or database_url is not None:
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        engine = create_engine(url, connect_args=connect_args)

        if database_url is None:
            _engine = engine
        return engine

    return _engine
