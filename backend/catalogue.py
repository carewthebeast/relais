import json
from enum import StrEnum
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from texte import normaliser

routeur = APIRouter(tags=["Catalogue"])

fichier_catalogue = Path(__file__).parent / "donnees" / "catalogue.json"


class Compartiment(StrEnum):
    CONGELE = "congele"
    REFRIGERE = "refrigere"
    SEC = "sec"


class Produit(BaseModel):
    nom: str
    compartiment: Compartiment


def charger_catalogue() -> list[Produit]:
    produits = json.loads(fichier_catalogue.read_text(encoding="utf-8"))
    return [Produit(**produit) for produit in produits]


catalogue = charger_catalogue()


def trouver_produit(texte: str) -> Produit | None:
    for produit in catalogue:
        if normaliser(produit.nom) == normaliser(texte):
            return produit
    return None


def suggerer(texte: str) -> list[str]:
    mots = set(normaliser(texte).split())
    if not mots:
        return []
    suggestions = []
    for produit in catalogue:
        mots_du_nom = set(normaliser(produit.nom).split())
        if mots <= mots_du_nom or mots_du_nom <= mots:
            suggestions.append(produit.nom)
    return suggestions


@routeur.get("/catalogue")
def lister_produits() -> list[Produit]:
    return catalogue
