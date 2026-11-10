"""Crée une journée de livraisons fictive : chaque commande est créée, validée et envoyée à l'entrepôt.

Lancer depuis le dossier backend : python demo.py
"""

import json
from pathlib import Path

from commandes import Action, NouvelleCommande, Validation, creer_commande, envoyer_a_l_entrepot, valider_commande

fichier_journee = Path(__file__).parent / "donnees" / "journee_demo.json"


def creer_journee() -> list[int]:
    numeros = []
    for donnees in json.loads(fichier_journee.read_text(encoding="utf-8")):
        commande = creer_commande(NouvelleCommande(**donnees))
        valider_commande(commande.id, Validation(par="Sophie (fictif)"))
        envoyer_a_l_entrepot(commande.id, Action(par="Sophie (fictif)"))
        numeros.append(commande.id)
        print(f"Commande {commande.id} envoyée à l'entrepôt : {commande.client}")
    return numeros


if __name__ == "__main__":
    creer_journee()
