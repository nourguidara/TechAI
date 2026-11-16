from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.config import settings

class Base(DeclarativeBase):
    pass

if not settings.database_url.startswith('sqlite:///'):
    raise ValueError('Only sandbox SQLite is supported')
Path(settings.database_url.removeprefix('sqlite:///')).resolve().parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def configure(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
Session = sessionmaker(engine, expire_on_commit=False)

def init_db():
    from backend import models
    Base.metadata.create_all(engine)
