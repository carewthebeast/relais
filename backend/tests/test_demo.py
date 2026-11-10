from fastapi.testclient import TestClient

from demo import creer_journee
from main import app

api = TestClient(app)


def test_la_journee_demo_est_envoyee_a_l_entrepot():
    numeros = creer_journee()
    commandes = api.get("/commandes").json()
    assert len(numeros) == 14
    assert [commande["id"] for commande in commandes] == numeros
    assert {commande["statut"] for commande in commandes} == {"envoyee_entrepot"}


def test_la_journee_demo_a_des_urgences():
    creer_journee()
    urgentes = [commande["client"] for commande in api.get("/commandes").json() if commande["urgente"]]
    assert urgentes == ["Bistro du Quai (fictif)", "Boulangerie du Lac (fictif)"]
