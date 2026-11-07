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


def test_accepte_majuscules_et_espaces():
    commande = {"client": "Épicerie Test (fictif)", "produit": "  POMMES   mcintosh ", "quantite": 1}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 200
    assert reponse.json()["produit"] == "Pommes McIntosh"


def test_accepte_sans_accents():
    commande = {"client": "Épicerie Test (fictif)", "produit": "sirop d'erable", "quantite": 1}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 200
    assert reponse.json()["produit"] == "Sirop d'érable"


def test_accepte_oe_au_lieu_de_la_ligature():
    commande = {"client": "Épicerie Test (fictif)", "produit": "oeufs gros calibre", "quantite": 1}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 200
    assert reponse.json()["produit"] == "Œufs gros calibre"


def test_accepte_apostrophe_courbe():
    commande = {"client": "Épicerie Test (fictif)", "produit": "Sirop d’érable", "quantite": 1}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 200
    assert reponse.json()["produit"] == "Sirop d'érable"


def test_refuse_faute_de_frappe():
    commande = {"client": "Épicerie Test (fictif)", "produit": "Pomme MacIntosh", "quantite": 1}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422


def test_lister_commandes():
    api.post("/commandes", json=commande_valide)
    reponse = api.get("/commandes")
    assert reponse.status_code == 200
    assert commande_valide in reponse.json()
