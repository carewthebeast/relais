import json
from datetime import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from base_de_donnees import ouvrir
from catalogue import Compartiment, trouver_produit
from clients import Client, entrepot, trouver_client
from commandes import Commande, Statut, charger_commande
from optimisation import Camion, Itineraire, Livraison, Plan, optimiser, suivre_l_ordre_des_appels
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
    dans_la_plage: bool
    urgente: bool


class ACharger(BaseModel):
    arret: int
    client: str
    produit: str
    quantite: int


class TourneeCamion(BaseModel):
    camion: str
    depart: str
    retour: str
    km: float
    minutes: int
    caisses: dict[Compartiment, int]
    arrets: list[ArretPrevu]
    chargement: dict[Compartiment, list[ACharger]]


class CommandeNonPlacee(BaseModel):
    commande_id: int
    client: str


class Version(BaseModel):
    km_total: float
    minutes_total: int
    hors_plage: int
    camions: list[TourneeCamion]
    non_placees: list[CommandeNonPlacee]


class TourneeDuJour(BaseModel):
    km_economises: float
    minutes_economisees: int
    recue: Version
    optimisee: Version


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


def ordre_de_chargement(arrets: list[ArretPrevu], commandes: dict[int, Commande]) -> dict[Compartiment, list[ACharger]]:
    """Le dernier arrêt se charge en premier, au fond du camion : le premier livré reste près de la porte."""
    chargement = {compartiment: [] for compartiment in Compartiment}
    for arret in reversed(arrets):
        for ligne in commandes[arret.commande_id].lignes:
            compartiment = trouver_produit(ligne.produit).compartiment
            chargement[compartiment].append(
                ACharger(arret=arret.position, client=arret.client, produit=ligne.produit, quantite=ligne.quantite)
            )
    return chargement


def presenter_arret(position: int, commande: Commande, arrivee: int) -> ArretPrevu:
    client = trouver_client(commande.client)
    return ArretPrevu(
        position=position,
        commande_id=commande.id,
        client=commande.client,
        ville=client.ville,
        arrivee=heure(arrivee),
        dans_la_plage=en_secondes(client.livraison_debut) <= arrivee <= en_secondes(client.livraison_fin),
        urgente=commande.urgente,
    )


def presenter_camion(itineraire: Itineraire, commandes: dict[int, Commande]) -> TourneeCamion:
    arrets = []
    for position, (commande_id, arrivee) in enumerate(zip(itineraire.commandes, itineraire.arrivees), start=1):
        arrets.append(presenter_arret(position, commandes[commande_id], arrivee))
    return TourneeCamion(
        camion=itineraire.camion,
        depart=heure(itineraire.depart),
        retour=heure(itineraire.retour),
        km=round(itineraire.metres / 1000, 1),
        minutes=round((itineraire.retour - itineraire.depart) / 60),
        caisses=compter_caisses([commandes[numero] for numero in itineraire.commandes]),
        arrets=arrets,
        chargement=ordre_de_chargement(arrets, commandes),
    )


def presenter_version(plan: Plan, commandes: dict[int, Commande]) -> Version:
    tournees = [presenter_camion(itineraire, commandes) for itineraire in plan.itineraires]
    hors_plage = 0
    for tournee in tournees:
        for arret in tournee.arrets:
            if not arret.dans_la_plage:
                hors_plage += 1
    return Version(
        km_total=round(sum(tournee.km for tournee in tournees), 1),
        minutes_total=sum(tournee.minutes for tournee in tournees),
        hors_plage=hors_plage,
        camions=tournees,
        non_placees=[CommandeNonPlacee(commande_id=numero, client=commandes[numero].client) for numero in plan.oubliees],
    )


@routeur.get("/tournees/du-jour")
def tournee_du_jour() -> TourneeDuJour:
    a_livrer = commandes_a_livrer()
    commandes = {commande.id: commande for commande in a_livrer}
    if a_livrer:
        clients_du_jour = [trouver_client(commande.client) for commande in a_livrer]
        matrice = demander_matrice([entrepot, *clients_du_jour])
        livraisons = [preparer_livraison(commande, client) for commande, client in zip(a_livrer, clients_du_jour)]
        plan_recu = suivre_l_ordre_des_appels(livraisons, camions, matrice.metres, matrice.secondes)
        plan_optimise = optimiser(livraisons, camions, matrice.metres, matrice.secondes, reglages.millisecondes_optimisation)
    else:
        plan_recu = plan_optimise = Plan(itineraires=[], oubliees=[])
    recue = presenter_version(plan_recu, commandes)
    optimisee = presenter_version(plan_optimise, commandes)
    return TourneeDuJour(
        km_economises=round(recue.km_total - optimisee.km_total, 1),
        minutes_economisees=recue.minutes_total - optimisee.minutes_total,
        recue=recue,
        optimisee=optimisee,
    )
