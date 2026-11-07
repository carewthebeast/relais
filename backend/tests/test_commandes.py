from fastapi.testclient import TestClient

from main import app

api = TestClient(app)

commande_valide = {
    "client": "Épicerie Test (fictif)",
    "produit": "Pommes McIntosh",
    "quantite": 3,
}


def test_creer_commande():
    reponse = api.post("/commandes", json=commande_valide)
    assert reponse.status_code == 200
    assert reponse.json() == commande_valide


def test_refuse_quantite_zero():
    commande = {"client": "Épicerie Test (fictif)", "produit": "Pommes McIntosh", "quantite": 0}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422


def test_refuse_produit_absent_du_catalogue():
    commande = {"client": "Épicerie Test (fictif)", "produit": "Ananas", "quantite": 2}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "Produit absent du catalogue : Ananas"


def test_lister_commandes():
    api.post("/commandes", json=commande_valide)
    reponse = api.get("/commandes")
    assert reponse.status_code == 200
    assert commande_valide in reponse.json()
