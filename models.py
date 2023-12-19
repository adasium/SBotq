from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from database import Base
from database import engine


class CommandModel(Base):
    __tablename__ = 'commands'

    id: int = Column(Integer, primary_key=True, unique=True)
    name: str = Column(String, unique=True)
    command: str = Column(String)
    counter: int = Column(Integer, default=0)


class Markov2(Base):
    __tablename__ = 'markov2'

    id: int = Column(Integer, primary_key=True, unique=True)
    counter: int = Column(Integer, default=1)
    channel_id: int = Column(Integer)
    guild_id: int = Column(Integer)
    word1: str | None = Column(String, nullable=True)
    word2: str | None = Column(String, nullable=True)


class Markov3(Base):
    __tablename__ = 'markov3'

    id: int = Column(Integer, primary_key=True, unique=True)
    counter: int = Column(Integer, default=1)
    channel_id: int = Column(Integer)
    guild_id: int = Column(Integer)
    word1: str | None = Column(String, nullable=True)
    word2: str | None = Column(String, nullable=False)
    word3: str | None = Column(String, nullable=True)


Base.metadata.create_all(engine)
