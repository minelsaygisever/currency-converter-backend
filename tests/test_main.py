# tests/test_main.py
from fastapi.testclient import TestClient
from src.main import app 

client = TestClient(app)

def test_read_root():
    # Arrange & Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Currency Converter API is up and running!"}