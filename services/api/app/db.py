from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base


def database(url):
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def view(entity):
    return {
        **entity.payload,
        "id": entity.id,
        "demo": entity.demo,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
    }
