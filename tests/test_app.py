from fastapi.testclient import TestClient
from src.abyssal_tome.app import app

client = TestClient(app)

def test_get_rulings():
    response = client.get("/rulings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
