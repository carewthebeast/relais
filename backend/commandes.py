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


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande):
    if commande.produit not in catalogue:
        raise HTTPException(
            status_code=422,
            detail=f"Produit absent du catalogue : {commande.produit}",
        )
    commandes.append(commande)
    return commande


@routeur.get("/commandes")
def lister_commandes():
    return commandes
