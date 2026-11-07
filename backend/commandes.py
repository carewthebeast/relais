from fastapi import APIRouter
from pydantic import BaseModel, Field

routeur = APIRouter(tags=["Commandes"])


class NouvelleCommande(BaseModel):
    client: str
    produit: str
    quantite: int = Field(gt=0)


commandes = []


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande):
    commandes.append(commande)
    return commande


@routeur.get("/commandes")
def lister_commandes():
    return commandes
