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


def arrets(version: dict) -> list[dict]:
    tous = []
    for camion in version["camions"]:
        tous += camion["arrets"]
    return tous


def test_heure_lisible():
    assert heure(8 * 3600 + 5 * 60) == "08:05"


def test_rien_a_livrer():
    resultat = tournee()
    assert resultat["km_economises"] == 0
    assert resultat["recue"]["camions"] == []
    assert resultat["optimisee"]["camions"] == []


def test_chaque_commande_placee_ou_signalee(faux_osrm):
    numeros = creer_journee()
    optimisee = tournee()["optimisee"]
    placees = [arret["commande_id"] for arret in arrets(optimisee)]
    non_placees = [commande["commande_id"] for commande in optimisee["non_placees"]]
    assert sorted(placees + non_placees) == sorted(numeros)


def test_aucun_compartiment_ne_deborde(faux_osrm):
    creer_journee()
    capacites = {camion.nom: camion.capacites for camion in camions}
    for camion in tournee()["optimisee"]["camions"]:
        for compartiment, caisses in camion["caisses"].items():
            assert caisses <= capacites[camion["camion"]][compartiment]


def test_arrivees_dans_les_plages_de_livraison(faux_osrm):
    creer_journee()
    for arret in arrets(tournee()["optimisee"]):
        client = trouver_client(arret["client"])
        assert client.livraison_debut.strftime("%H:%M") <= arret["arrivee"] <= client.livraison_fin.strftime("%H:%M")
        assert arret["dans_la_plage"]


def test_tournee_recue_suit_l_ordre_des_appels(faux_osrm):
    numeros = creer_journee()
    recue = tournee()["recue"]
    assert [arret["commande_id"] for arret in arrets(recue)] == numeros


def test_economies_avant_apres(faux_osrm):
    creer_journee()
    resultat = tournee()
    assert resultat["km_economises"] == round(resultat["recue"]["km_total"] - resultat["optimisee"]["km_total"], 1)
    assert resultat["optimisee"]["hors_plage"] == 0


def test_chargement_dernier_arret_au_fond(faux_osrm):
    creer_journee()
    for camion in tournee()["optimisee"]["camions"]:
        for zone in camion["chargement"].values():
            numeros_d_arret = [a_charger["arret"] for a_charger in zone]
            assert numeros_d_arret == sorted(numeros_d_arret, reverse=True)


def test_chargement_contient_toute_la_marchandise(faux_osrm):
    creer_journee()
    for camion in tournee()["optimisee"]["camions"]:
        total = sum(a_charger["quantite"] for zone in camion["chargement"].values() for a_charger in zone)
        assert total == sum(camion["caisses"].values())


def test_ignore_les_commandes_pas_encore_envoyees(faux_osrm):
    api.post("/commandes", json={"client": "Marché Lafleur (fictif)", "lignes": [{"produit": "Beurre salé", "quantite": 2}]})
    assert tournee()["optimisee"]["camions"] == []
