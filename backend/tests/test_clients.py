from fastapi.testclient import TestClient

from main import app

api = TestClient(app)


def lister() -> list[dict]:
    return api.get("/clients").json()


def dans_la_region(lieu: dict) -> bool:
    return 45.0 < lieu["latitude"] < 45.8 and -73.2 < lieu["longitude"] < -71.7


def test_lister_les_clients():
    reponse = api.get("/clients")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 20


def test_clients_identifies_comme_fictifs():
    for client in lister():
        assert client["nom"].endswith("(fictif)")


def test_chaque_client_a_son_propre_numero():
    numeros = [client["id"] for client in lister()]
    assert len(numeros) == len(set(numeros))


def test_clients_a_granby_et_autour():
    villes = {client["ville"] for client in lister()}
    assert "Granby" in villes
    assert {"Bromont", "Cowansville", "Waterloo", "Saint-Hyacinthe", "Magog", "Sherbrooke"} <= villes


def test_clients_dans_la_region():
    for client in lister():
        assert dans_la_region(client), client["nom"]


def test_plage_de_livraison_dans_le_bon_ordre():
    for client in lister():
        assert client["livraison_debut"] < client["livraison_fin"], client["nom"]


def test_lire_un_client():
    reponse = api.get("/clients/2")
    assert reponse.status_code == 200
    client = reponse.json()
    assert client["nom"] == "Restaurant Le Tournesol (fictif)"
    assert client["livraison_debut"] == "08:00:00"
    assert client["livraison_fin"] == "10:30:00"


def test_client_introuvable():
    reponse = api.get("/clients/999")
    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Client introuvable : 999"


def test_entrepot_fictif_a_granby():
    reponse = api.get("/entrepot")
    assert reponse.status_code == 200
    entrepot = reponse.json()
    assert entrepot["ville"] == "Granby"
    assert entrepot["nom"].endswith("(fictif)")
    assert dans_la_region(entrepot)
