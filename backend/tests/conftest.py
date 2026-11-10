import pytest

import base_de_donnees
import trajets
from reglages import reglages


@pytest.fixture(autouse=True)
def base_de_test(tmp_path, monkeypatch):
    monkeypatch.setattr(base_de_donnees, "chemin_base", tmp_path / "test.db")


@pytest.fixture(autouse=True)
def optimisation_rapide(monkeypatch):
    monkeypatch.setattr(reglages, "millisecondes_optimisation", 300)


def faux_tableau(nombre: int, par_pas: int) -> list[list[int]]:
    return [[abs(depart - arrivee) * par_pas for arrivee in range(nombre)] for depart in range(nombre)]


def repondre_comme_osrm(chemin: str) -> dict:
    """Faux OSRM : 10 km et 10 minutes entre deux lieux voisins de la liste."""
    nombre = chemin.split("?")[0].count(";") + 1
    return {
        "code": "Ok",
        "distances": faux_tableau(nombre, 10_000),
        "durations": faux_tableau(nombre, 600),
    }


@pytest.fixture
def faux_osrm(monkeypatch):
    monkeypatch.setattr(trajets, "appeler_osrm", repondre_comme_osrm)
