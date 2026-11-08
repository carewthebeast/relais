from fastapi.testclient import TestClient

from main import app

api = TestClient(app)


def premier_message(reponse) -> str:
    return reponse.json()["detail"][0]["msg"]


def test_quantite_zero_en_francais():
    commande = {"client": "Épicerie Beausoleil (fictif)", "lignes": [{"produit": "Beurre salé", "quantite": 0}]}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422
    assert premier_message(reponse) == "Doit être plus grand que 0"


def test_garde_l_emplacement_de_l_erreur():
    commande = {"client": "Épicerie Beausoleil (fictif)", "lignes": [{"produit": "Beurre salé", "quantite": 0}]}
    reponse = api.post("/commandes", json=commande)
    assert reponse.json()["detail"][0]["loc"] == ["body", "lignes", 0, "quantite"]


def test_champ_manquant_en_francais():
    commande = {"lignes": [{"produit": "Beurre salé", "quantite": 1}]}
    reponse = api.post("/commandes", json=commande)
    assert premier_message(reponse) == "Champ obligatoire"


def test_source_inconnue_en_francais():
    commande = {"client": "Épicerie Beausoleil (fictif)", "source": "fax", "lignes": [{"produit": "Beurre salé", "quantite": 1}]}
    reponse = api.post("/commandes", json=commande)
    assert premier_message(reponse) == "Valeur non permise. Choix possibles : 'formulaire', 'texte_libre' ou 'erp'"


def test_commande_vide_en_francais():
    commande = {"client": "Épicerie Beausoleil (fictif)", "lignes": []}
    reponse = api.post("/commandes", json=commande)
    assert premier_message(reponse) == "Il faut au moins 1 élément"


def test_urgente_invalide_en_francais():
    commande = {"client": "Épicerie Beausoleil (fictif)", "urgente": "peut-être", "lignes": [{"produit": "Beurre salé", "quantite": 1}]}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422
    assert premier_message(reponse) == "Doit être true (oui) ou false (non)"


def test_numero_de_commande_invalide_en_francais():
    reponse = api.get("/commandes/abc")
    assert reponse.status_code == 422
    assert premier_message(reponse) == "Doit être un nombre entier"


def test_json_mal_forme_en_francais():
    texte_casse = '{"client": "Épicerie Beausoleil (fictif)" "lignes": []}'
    reponse = api.post("/commandes", content=texte_casse, headers={"Content-Type": "application/json"})
    assert reponse.status_code == 422
    assert premier_message(reponse) == "JSON mal formé : il manque peut-être une virgule, un guillemet ou une accolade"
