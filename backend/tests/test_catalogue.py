from fastapi.testclient import TestClient

from main import app

api = TestClient(app)


def compartiment_de(nom: str) -> str:
    for produit in api.get("/catalogue").json():
        if produit["nom"] == nom:
            return produit["compartiment"]
    raise AssertionError(f"{nom} absent du catalogue")


def test_lister_le_catalogue():
    reponse = api.get("/catalogue")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 10


def test_chaque_produit_a_son_compartiment():
    assert compartiment_de("Frites congelées") == "congele"
    assert compartiment_de("Lait 2 %") == "refrigere"
    assert compartiment_de("Farine tout usage") == "sec"


def test_les_trois_compartiments_sont_utilises():
    compartiments = {produit["compartiment"] for produit in api.get("/catalogue").json()}
    assert compartiments == {"congele", "refrigere", "sec"}
