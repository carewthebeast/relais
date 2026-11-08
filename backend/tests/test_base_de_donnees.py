from fastapi.testclient import TestClient

from base_de_donnees import ouvrir
from main import app

api = TestClient(app)

commande = {
    "client": "Épicerie Test (fictif)",
    "lignes": [
        {"produit": "Pommes McIntosh", "quantite": 3},
        {"produit": "Lait 2 %", "quantite": 2},
    ],
}


def test_commande_enregistree_dans_la_base():
    creee = api.post("/commandes", json=commande).json()
    with ouvrir() as connexion:
        rangee = connexion.execute(
            "SELECT client, statut FROM commandes WHERE id = ?", (creee["id"],)
        ).fetchone()
        lignes = connexion.execute(
            "SELECT produit, quantite FROM lignes WHERE commande_id = ?", (creee["id"],)
        ).fetchall()
    assert rangee["client"] == "Épicerie Test (fictif)"
    assert rangee["statut"] == "recue"
    assert [tuple(ligne) for ligne in lignes] == [("Pommes McIntosh", 3), ("Lait 2 %", 2)]


def test_validation_enregistree_dans_la_base():
    creee = api.post("/commandes", json=commande).json()
    api.post(f"/commandes/{creee['id']}/valider", json={"par": "Sophie (fictif)"})
    with ouvrir() as connexion:
        statut = connexion.execute(
            "SELECT statut FROM commandes WHERE id = ?", (creee["id"],)
        ).fetchone()["statut"]
        evenements = connexion.execute(
            "SELECT statut, par FROM evenements WHERE commande_id = ? ORDER BY id", (creee["id"],)
        ).fetchall()
    assert statut == "validee"
    assert [tuple(evenement) for evenement in evenements] == [
        ("recue", "Épicerie Test (fictif)"),
        ("validee", "Sophie (fictif)"),
    ]


def test_les_numeros_viennent_de_la_base():
    premiere = api.post("/commandes", json=commande).json()
    deuxieme = api.post("/commandes", json=commande).json()
    assert deuxieme["id"] == premiere["id"] + 1
