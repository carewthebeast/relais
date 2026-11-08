import unicodedata
from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

routeur = APIRouter(tags=["Commandes"])

catalogue = [
    "Pommes McIntosh",
    "Lait 2 %",
    "Beurre salé",
    "Fromage cheddar",
    "Pain blanc tranché",
    "Farine tout usage",
    "Sirop d'érable",
    "Poulet entier congelé",
    "Frites congelées",
    "Œufs gros calibre",
]


class Statut(StrEnum):
    RECUE = "recue"
    A_VERIFIER = "a_verifier"
    VALIDEE = "validee"
    ENVOYEE_ENTREPOT = "envoyee_entrepot"


class Source(StrEnum):
    FORMULAIRE = "formulaire"
    TEXTE_LIBRE = "texte_libre"
    ERP = "erp"


class Ligne(BaseModel):
    produit: str
    quantite: int = Field(gt=0)


class NouvelleCommande(BaseModel):
    client: str
    lignes: list[Ligne] = Field(min_length=1)
    source: Source = Source.FORMULAIRE
    reference_externe: str | None = None


class Evenement(BaseModel):
    statut: Statut
    par: str
    date: datetime
    detail: str


class Commande(NouvelleCommande):
    id: int
    statut: Statut
    historique: list[Evenement]


class Action(BaseModel):
    par: str = Field(min_length=1)


class Validation(Action):
    lignes: list[Ligne] | None = Field(default=None, min_length=1)


commandes = []


def enlever_accents(texte: str) -> str:
    resultat = ""
    for lettre in unicodedata.normalize("NFD", texte):
        if not unicodedata.combining(lettre):
            resultat += lettre
    return resultat


def normaliser(texte: str) -> str:
    texte = " ".join(texte.split()).lower()
    texte = texte.replace("œ", "oe").replace("’", "'")
    return enlever_accents(texte)


def trouver_produit(produit: str) -> str | None:
    for nom in catalogue:
        if normaliser(nom) == normaliser(produit):
            return nom
    return None


def rapprocher_lignes(lignes: list[Ligne]) -> list[Ligne]:
    propres = []
    absents = []
    for ligne in lignes:
        nom_officiel = trouver_produit(ligne.produit)
        if nom_officiel is None:
            absents.append(ligne.produit)
        else:
            propres.append(Ligne(produit=nom_officiel, quantite=ligne.quantite))
    if absents:
        raise HTTPException(
            status_code=422,
            detail=f"Absent du catalogue : {', '.join(absents)}",
        )
    return propres


def decrire(lignes: list[Ligne]) -> str:
    morceaux = []
    for ligne in lignes:
        morceaux.append(f"{ligne.quantite} {ligne.produit}")
    return ", ".join(morceaux)


def trouver_commande(commande_id: int) -> Commande:
    for commande in commandes:
        if commande.id == commande_id:
            return commande
    raise HTTPException(
        status_code=404,
        detail=f"Commande introuvable : {commande_id}",
    )


def changer_statut(commande: Commande, statut: Statut, par: str, detail: str) -> None:
    commande.statut = statut
    commande.historique.append(
        Evenement(statut=statut, par=par, date=datetime.now().astimezone(), detail=detail)
    )


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande) -> Commande:
    nouvelle = Commande(
        id=len(commandes) + 1,
        client=commande.client,
        lignes=rapprocher_lignes(commande.lignes),
        source=commande.source,
        reference_externe=commande.reference_externe,
        statut=Statut.RECUE,
        historique=[],
    )
    changer_statut(nouvelle, Statut.RECUE, commande.client, f"Reçue ({commande.source})")
    commandes.append(nouvelle)
    return nouvelle


@routeur.get("/commandes")
def lister_commandes() -> list[Commande]:
    return commandes


@routeur.get("/commandes/{commande_id}")
def lire_commande(commande_id: int) -> Commande:
    return trouver_commande(commande_id)


@routeur.post("/commandes/{commande_id}/valider")
def valider_commande(commande_id: int, validation: Validation) -> Commande:
    commande = trouver_commande(commande_id)
    if commande.statut not in (Statut.RECUE, Statut.A_VERIFIER):
        raise HTTPException(
            status_code=409,
            detail=f"Impossible de valider : la commande est déjà « {commande.statut} »",
        )
    if validation.lignes is None:
        changer_statut(commande, Statut.VALIDEE, validation.par, "Validée telle quelle")
    else:
        avant = decrire(commande.lignes)
        commande.lignes = rapprocher_lignes(validation.lignes)
        changer_statut(
            commande, Statut.VALIDEE, validation.par, f"Corrigée et validée. Avant : {avant}"
        )
    return commande


@routeur.post("/commandes/{commande_id}/envoyer")
def envoyer_a_l_entrepot(commande_id: int, action: Action) -> Commande:
    commande = trouver_commande(commande_id)
    if commande.statut != Statut.VALIDEE:
        raise HTTPException(
            status_code=409,
            detail="Une commande doit être validée avant l'envoi à l'entrepôt",
        )
    changer_statut(commande, Statut.ENVOYEE_ENTREPOT, action.par, "Envoyée à l'entrepôt")
    return commande
