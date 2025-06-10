# src/core/database.py

from sqlmodel import SQLModel, create_engine, Session
import os

# 1) SQLite dosya yolunu belirliyoruz. Proje kökünde 'currency.db' oluşturulsun.
DATABASE_URL = "sqlite:///./currency.db"

# 2) SQLModel'in create_engine fonksiyonu ile engine örneği oluşturuyoruz.
#    echo=True yazar; SQL sorgularını terminalde görmek istersen True yapabilirsin.
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    """
    FastAPI Depends() ile kullanabileceğimiz bir session generator.
    Her çağrıldığında yeni bir SQLModel Session örneği üretir.
    """
    with Session(engine) as session:
        yield session

def init_db():
    """
    Projedeki tüm SQLModel tabanlı modellerin (metadata) 
    ilgili veritabanında tablolarını oluşturur.
    """
    SQLModel.metadata.create_all(engine)
