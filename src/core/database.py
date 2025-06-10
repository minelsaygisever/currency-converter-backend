# src/core/database.py

from sqlmodel import SQLModel, create_engine, Session
import os

DATABASE_URL = "sqlite:///./currency.db"

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    SQLModel.metadata.create_all(engine)
