import json
from datetime import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from base_de_donnees import ouvrir
from catalogue import Compartiment, trouver_produit
from clients import Client, entrepot, trouver_client
from commandes import Commande, Statut, charger_commande
from optimisation import Camion, Itineraire, Livraison, optimiser
from reglages import reglages
from trajets import demander_matrice

routeur = APIRouter(tags=["Tournées"])

fichier_camions = Path(__file__).parent / "donnees" / "camions.json"
camions = [Camion(**camion) for camion in json.loads(fichier_camions.read_text(encoding="utf-8"))]


class ArretPrevu(BaseModel):
    position: int
    commande_id: int
    client: str
    ville: str
    arrivee: str
    urgente: bool


class TourneeCamion(BaseModel):
    camion: str
    depart: str
    retour: str
    km: float
    caisses: dict[Compartiment, int]
    arrets: list[ArretPrevu]


class CommandeNonPlacee(BaseModel):
    commande_id: int
    client: str


class TourneeDuJour(BaseModel):
    camions: list[TourneeCamion]
    km_total: float
    non_placees: list[CommandeNonPlacee]


def heure(secondes: int) -> str:
    return f"{secondes // 3600:02d}:{secondes % 3600 // 60:02d}"


def en_secondes(moment: time) -> int:
    return moment.hour * 3600 + moment.minute * 60


def commandes_a_livrer() -> list[Commande]:
    with ouvrir() as connexion:
        rangees = connexion.execute(
            "SELECT * FROM commandes WHERE statut = ? ORDER BY id",
            (Statut.ENVOYEE_ENTREPOT,),
        ).fetchall()
        return [charger_commande(connexion, rangee) for rangee in rangees]


def compter_caisses(commandes: list[Commande]) -> dict[Compartiment, int]:
    caisses = {compartiment: 0 for compartiment in Compartiment}
    for commande in commandes:
        for ligne in commande.lignes:
            caisses[trouver_produit(ligne.produit).compartiment] += ligne.quantite
    return caisses


def preparer_livraison(commande: Commande, client: Client) -> Livraison:
    return Livraison(
        commande_id=commande.id,
        debut=en_secondes(client.livraison_debut),
        fin=en_secondes(client.livraison_fin),
        caisses=compter_caisses([commande]),
        urgente=commande.urgente,
    )


def presenter_camion(itineraire: Itineraire, commandes: dict[int, Commande]) -> TourneeCamion:
    arrets = []
    for position, (commande_id, arrivee) in enumerate(zip(itineraire.commandes, itineraire.arrivees), start=1):
        commande = commandes[commande_id]
        arrets.append(
            ArretPrevu(
                position=position,
                commande_id=commande_id,
                client=commande.client,
                ville=trouver_client(commande.client).ville,
                arrivee=heure(arrivee),
                urgente=commande.urgente,
            )
        )
    return TourneeCamion(
        camion=itineraire.camion,
        depart=heure(itineraire.depart),
        retour=heure(itineraire.retour),
        km=round(itineraire.metres / 1000, 1),
        caisses=compter_caisses([commandes[numero] for numero in itineraire.commandes]),
        arrets=arrets,
    )


@routeur.get("/tournees/du-jour")
def tournee_du_jour() -> TourneeDuJour:
    a_livrer = commandes_a_livrer()
    if not a_livrer:
        return TourneeDuJour(camions=[], km_total=0, non_placees=[])
    clients_du_jour = [trouver_client(commande.client) for commande in a_livrer]
    matrice = demander_matrice([entrepot, *clients_du_jour])
    livraisons = [preparer_livraison(commande, client) for commande, client in zip(a_livrer, clients_du_jour)]
    plan = optimiser(livraisons, camions, matrice.metres, matrice.secondes, reglages.millisecondes_optimisation)
    commandes = {commande.id: commande for commande in a_livrer}
    tournees = [presenter_camion(itineraire, commandes) for itineraire in plan.itineraires]
    return TourneeDuJour(
        camions=tournees,
        km_total=round(sum(tournee.km for tournee in tournees), 1),
        non_placees=[
            CommandeNonPlacee(commande_id=numero, client=commandes[numero].client) for numero in plan.oubliees
        ],
    )
