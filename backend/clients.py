import json
from datetime import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from texte import normaliser

routeur = APIRouter(tags=["Clients et entrepôt"])

dossier_donnees = Path(__file__).parent / "donnees"


class Lieu(BaseModel):
    nom: str
    ville: str
    latitude: float
    longitude: float


class Client(Lieu):
    id: int
    livraison_debut: time
    livraison_fin: time


def lire_fichier(nom_fichier: str):
    return json.loads((dossier_donnees / nom_fichier).read_text(encoding="utf-8"))


entrepot = Lieu(**lire_fichier("entrepot.json"))
clients = [Client(**client) for client in lire_fichier("clients.json")]


def trouver_client(nom: str) -> Client | None:
    for client in clients:
        if normaliser(client.nom) == normaliser(nom):
            return client
    return None


@routeur.get("/clients")
def lister_clients() -> list[Client]:
    return clients


@routeur.get("/clients/{client_id}")
def lire_client(client_id: int) -> Client:
    for client in clients:
        if client.id == client_id:
            return client
    raise HTTPException(status_code=404, detail=f"Client introuvable : {client_id}")


@routeur.get("/entrepot")
def lire_entrepot() -> Lieu:
    return entrepot
