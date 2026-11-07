from fastapi.testclient import TestClient

from main import app

api = TestClient(app)


def test_accueil():
    reponse = api.get("/")
    assert reponse.status_code == 200
    assert reponse.json() == {"message": "L'API de Relais est en marche"}
