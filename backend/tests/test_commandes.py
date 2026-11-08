from fastapi.testclient import TestClient

from main import app

api = TestClient(app)


def commande_de(produit: str, quantite: int = 1) -> dict:
    return {
        "client": "Épicerie Test (fictif)",
        "lignes": [{"produit": produit, "quantite": quantite}],
    }


def test_creer_commande():
    reponse = api.post("/commandes", json=commande_de("Pommes McIntosh", 3))
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["client"] == "Épicerie Test (fictif)"
    assert resultat["lignes"] == [{"produit": "Pommes McIntosh", "quantite": 3}]


def test_commande_avec_plusieurs_lignes():
    commande = {
        "client": "Épicerie Test (fictif)",
        "lignes": [
            {"produit": "lait 2 %", "quantite": 2},
            {"produit": "frites congelees", "quantite": 5},
        ],
    }
    resultat = api.post("/commandes", json=commande).json()
    assert resultat["lignes"] == [
        {"produit": "Lait 2 %", "quantite": 2},
        {"produit": "Frites congelées", "quantite": 5},
    ]


def test_refuse_commande_sans_ligne():
    commande = {"client": "Épicerie Test (fictif)", "lignes": []}
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422


def test_nouvelle_commande_est_recue():
    resultat = api.post("/commandes", json=commande_de("Pommes McIntosh")).json()
    assert resultat["statut"] == "recue"


def test_chaque_commande_a_son_numero():
    premiere = api.post("/commandes", json=commande_de("Pommes McIntosh")).json()
    deuxieme = api.post("/commandes", json=commande_de("Pommes McIntosh")).json()
    assert premiere["id"] != deuxieme["id"]


def test_source_par_defaut_est_formulaire():
    resultat = api.post("/commandes", json=commande_de("Pommes McIntosh")).json()
    assert resultat["source"] == "formulaire"
    assert resultat["reference_externe"] is None


def test_commande_venant_de_l_erp():
    commande = commande_de("Beurre salé", 4)
    commande["source"] = "erp"
    commande["reference_externe"] = "ODOO-4521"
    resultat = api.post("/commandes", json=commande).json()
    assert resultat["source"] == "erp"
    assert resultat["reference_externe"] == "ODOO-4521"


def test_refuse_source_inconnue():
    commande = commande_de("Beurre salé", 4)
    commande["source"] = "fax"
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422


def test_le_client_ne_choisit_pas_le_statut():
    commande = commande_de("Beurre salé", 4)
    commande["statut"] = "validee"
    resultat = api.post("/commandes", json=commande).json()
    assert resultat["statut"] == "recue"


def test_refuse_quantite_zero():
    reponse = api.post("/commandes", json=commande_de("Pommes McIntosh", 0))
    assert reponse.status_code == 422


def test_refuse_produit_absent_du_catalogue():
    reponse = api.post("/commandes", json=commande_de("Ananas"))
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "Absent du catalogue : Ananas"


def test_nomme_tous_les_produits_absents():
    commande = {
        "client": "Épicerie Test (fictif)",
        "lignes": [
            {"produit": "Ananas", "quantite": 1},
            {"produit": "Pommes McIntosh", "quantite": 2},
            {"produit": "Kiwi", "quantite": 3},
        ],
    }
    reponse = api.post("/commandes", json=commande)
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "Absent du catalogue : Ananas, Kiwi"


def test_accepte_majuscules_et_espaces():
    reponse = api.post("/commandes", json=commande_de("  POMMES   mcintosh "))
    assert reponse.status_code == 200
    assert reponse.json()["lignes"][0]["produit"] == "Pommes McIntosh"


def test_accepte_sans_accents():
    reponse = api.post("/commandes", json=commande_de("sirop d'erable"))
    assert reponse.status_code == 200
    assert reponse.json()["lignes"][0]["produit"] == "Sirop d'érable"


def test_accepte_oe_au_lieu_de_la_ligature():
    reponse = api.post("/commandes", json=commande_de("oeufs gros calibre"))
    assert reponse.status_code == 200
    assert reponse.json()["lignes"][0]["produit"] == "Œufs gros calibre"


def test_accepte_apostrophe_courbe():
    reponse = api.post("/commandes", json=commande_de("Sirop d’érable"))
    assert reponse.status_code == 200
    assert reponse.json()["lignes"][0]["produit"] == "Sirop d'érable"


def test_refuse_faute_de_frappe():
    reponse = api.post("/commandes", json=commande_de("Pomme MacIntosh"))
    assert reponse.status_code == 422


def test_lister_commandes():
    creee = api.post("/commandes", json=commande_de("Pommes McIntosh")).json()
    reponse = api.get("/commandes")
    assert reponse.status_code == 200
    assert creee in reponse.json()


def creer(produit: str = "Pommes McIntosh", quantite: int = 3) -> dict:
    return api.post("/commandes", json=commande_de(produit, quantite)).json()


def test_historique_commence_a_la_reception():
    commande = creer()
    assert len(commande["historique"]) == 1
    premier = commande["historique"][0]
    assert premier["statut"] == "recue"
    assert premier["par"] == "Épicerie Test (fictif)"
    assert premier["detail"] == "Reçue (formulaire)"


def test_lire_une_commande():
    commande = creer()
    reponse = api.get(f"/commandes/{commande['id']}")
    assert reponse.status_code == 200
    assert reponse.json() == commande


def test_commande_introuvable():
    reponse = api.get("/commandes/9999")
    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Commande introuvable : 9999"


def test_valider_une_commande():
    commande = creer()
    reponse = api.post(f"/commandes/{commande['id']}/valider", json={"par": "Sophie (fictif)"})
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["statut"] == "validee"
    dernier = resultat["historique"][-1]
    assert dernier["statut"] == "validee"
    assert dernier["par"] == "Sophie (fictif)"
    assert dernier["detail"] == "Validée telle quelle"


def test_valider_avec_corrections():
    commande = creer("Pommes McIntosh", 3)
    correction = {"par": "Sophie (fictif)", "lignes": [{"produit": "pommes mcintosh", "quantite": 5}]}
    resultat = api.post(f"/commandes/{commande['id']}/valider", json=correction).json()
    assert resultat["lignes"] == [{"produit": "Pommes McIntosh", "quantite": 5}]
    assert resultat["historique"][-1]["detail"] == "Corrigée et validée. Avant : 3 Pommes McIntosh"


def test_correction_avec_produit_absent_ne_valide_pas():
    commande = creer()
    correction = {"par": "Sophie (fictif)", "lignes": [{"produit": "Ananas", "quantite": 1}]}
    reponse = api.post(f"/commandes/{commande['id']}/valider", json=correction)
    assert reponse.status_code == 422
    toujours = api.get(f"/commandes/{commande['id']}").json()
    assert toujours["statut"] == "recue"
    assert toujours["lignes"] == commande["lignes"]


def test_valider_exige_un_nom():
    commande = creer()
    sans_nom = api.post(f"/commandes/{commande['id']}/valider", json={})
    nom_vide = api.post(f"/commandes/{commande['id']}/valider", json={"par": ""})
    assert sans_nom.status_code == 422
    assert nom_vide.status_code == 422


def test_refuse_double_validation():
    commande = creer()
    api.post(f"/commandes/{commande['id']}/valider", json={"par": "Sophie (fictif)"})
    reponse = api.post(f"/commandes/{commande['id']}/valider", json={"par": "Marc (fictif)"})
    assert reponse.status_code == 409


def test_envoyer_une_commande_validee():
    commande = creer()
    api.post(f"/commandes/{commande['id']}/valider", json={"par": "Sophie (fictif)"})
    reponse = api.post(f"/commandes/{commande['id']}/envoyer", json={"par": "Sophie (fictif)"})
    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat["statut"] == "envoyee_entrepot"
    statuts = [evenement["statut"] for evenement in resultat["historique"]]
    assert statuts == ["recue", "validee", "envoyee_entrepot"]


def test_refuse_envoi_sans_validation():
    commande = creer()
    reponse = api.post(f"/commandes/{commande['id']}/envoyer", json={"par": "Sophie (fictif)"})
    assert reponse.status_code == 409
    assert reponse.json()["detail"] == "Une commande doit être validée avant l'envoi à l'entrepôt"
