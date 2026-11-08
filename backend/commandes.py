import unicodedata
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


class Commande(NouvelleCommande):
    id: int
    statut: Statut


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


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande) -> Commande:
    nouvelle = Commande(
        id=len(commandes) + 1,
        client=commande.client,
        lignes=rapprocher_lignes(commande.lignes),
        source=commande.source,
        reference_externe=commande.reference_externe,
        statut=Statut.RECUE,
    )
    commandes.append(nouvelle)
    return nouvelle


@routeur.get("/commandes")
def lister_commandes() -> list[Commande]:
    return commandes
