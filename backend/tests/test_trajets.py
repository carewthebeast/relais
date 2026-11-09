import httpx
import pytest
from fastapi.testclient import TestClient

import trajets
from clients import clients, entrepot
from main import app
from reglages import reglages

api = TestClient(app)


def faux_tableau(nombre: int, par_pas: int) -> list[list[int]]:
    return [[abs(depart - arrivee) * par_pas for arrivee in range(nombre)] for depart in range(nombre)]


def repondre_comme_osrm(chemin: str) -> dict:
    nombre = chemin.split("?")[0].count(";") + 1
    return {
        "code": "Ok",
        "distances": faux_tableau(nombre, 10_000),
        "durations": faux_tableau(nombre, 600),
    }


@pytest.fixture
def faux_osrm(monkeypatch):
    monkeypatch.setattr(trajets, "appeler_osrm", repondre_comme_osrm)


def test_longitude_avant_latitude():
    assert trajets.coordonnees([entrepot]) == "-72.76,45.387"


def test_matrice_entrepot_et_clients(faux_osrm):
    matrice = trajets.demander_matrice([entrepot, *clients])
    assert len(matrice.metres) == 21
    assert len(matrice.secondes[0]) == 21
    assert matrice.secondes[0][0] == 0


def test_trajets_depuis_entrepot(faux_osrm):
    reponse = api.get("/trajets/depuis-entrepot")
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert len(resultat) == 20
    assert resultat[0] == {
        "client": "Épicerie Beausoleil (fictif)",
        "ville": "Granby",
        "km": 10.0,
        "minutes": 10,
    }


def test_trajets_du_plus_proche_au_plus_loin(faux_osrm):
    minutes = [trajet["minutes"] for trajet in api.get("/trajets/depuis-entrepot").json()]
    assert minutes == sorted(minutes)


def test_osrm_eteint(monkeypatch):
    def refuser(*args, **kwargs):
        raise httpx.ConnectError("Connexion refusée")

    monkeypatch.setattr(trajets.httpx, "get", refuser)
    reponse = api.get("/trajets/depuis-entrepot")
    assert reponse.status_code == 503
    assert reponse.json()["detail"] == "OSRM ne répond pas. Est-il lancé ? Voir le README."


def test_osrm_refuse_la_demande(monkeypatch):
    monkeypatch.setattr(trajets, "appeler_osrm", lambda chemin: {"code": "InvalidQuery", "message": "Query string malformed"})
    reponse = api.get("/trajets/depuis-entrepot")
    assert reponse.status_code == 502
    assert reponse.json()["detail"] == "OSRM a refusé la demande : Query string malformed"


def test_aucune_route_trouvee(monkeypatch):
    def repondre_avec_un_trou(chemin: str) -> dict:
        donnees = repondre_comme_osrm(chemin)
        donnees["durations"][0][3] = None
        return donnees

    monkeypatch.setattr(trajets, "appeler_osrm", repondre_avec_un_trou)
    reponse = api.get("/trajets/depuis-entrepot")
    assert reponse.status_code == 502
    assert reponse.json()["detail"] == (
        "Aucune route trouvée de Entrepôt de Granby (fictif) à École primaire des Érables (fictif)"
    )


def osrm_en_marche() -> bool:
    try:
        httpx.get(reglages.osrm_url, timeout=1)
        return True
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not osrm_en_marche(), reason="OSRM n'est pas lancé")
def test_vrai_osrm_entrepot_a_sherbrooke():
    carrefour = clients[13]
    assert carrefour.ville == "Sherbrooke"
    matrice = trajets.demander_matrice([entrepot, carrefour])
    assert 60_000 < matrice.metres[0][1] < 100_000
    assert 45 * 60 < matrice.secondes[0][1] < 100 * 60
