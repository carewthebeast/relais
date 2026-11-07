import unicodedata

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


class NouvelleCommande(BaseModel):
    client: str
    produit: str
    quantite: int = Field(gt=0)


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


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande):
    nom_officiel = trouver_produit(commande.produit)
    if nom_officiel is None:
        raise HTTPException(
            status_code=422,
            detail=f"Produit absent du catalogue : {commande.produit}",
        )
    commande.produit = nom_officiel
    commandes.append(commande)
    return commande


@routeur.get("/commandes")
def lister_commandes():
    return commandes
