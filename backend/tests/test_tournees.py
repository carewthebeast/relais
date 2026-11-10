from fastapi.testclient import TestClient

from clients import trouver_client
from demo import creer_journee
from main import app
from tournees import camions, heure

api = TestClient(app)


def tournee() -> dict:
    reponse = api.get("/tournees/du-jour")
    assert reponse.status_code == 200
    return reponse.json()


def test_heure_lisible():
    assert heure(8 * 3600 + 5 * 60) == "08:05"


def test_rien_a_livrer():
    assert tournee() == {"camions": [], "km_total": 0, "non_placees": []}


def test_chaque_commande_placee_ou_signalee(faux_osrm):
    numeros = creer_journee()
    resultat = tournee()
    placees = [arret["commande_id"] for camion in resultat["camions"] for arret in camion["arrets"]]
    non_placees = [commande["commande_id"] for commande in resultat["non_placees"]]
    assert sorted(placees + non_placees) == sorted(numeros)


def test_aucun_compartiment_ne_deborde(faux_osrm):
    creer_journee()
    for camion in tournee()["camions"]:
        capacites = next(modele.capacites for modele in camions if modele.nom == camion["camion"])
        for compartiment, caisses in camion["caisses"].items():
            assert caisses <= capacites[compartiment]


def test_arrivees_dans_les_plages_de_livraison(faux_osrm):
    creer_journee()
    for camion in tournee()["camions"]:
        for arret in camion["arrets"]:
            client = trouver_client(arret["client"])
            assert client.livraison_debut.strftime("%H:%M") <= arret["arrivee"] <= client.livraison_fin.strftime("%H:%M")


def test_ignore_les_commandes_pas_encore_envoyees(faux_osrm):
    api.post("/commandes", json={"client": "Marché Lafleur (fictif)", "lignes": [{"produit": "Beurre salé", "quantite": 2}]})
    assert tournee()["camions"] == []
