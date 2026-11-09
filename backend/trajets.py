import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients import Lieu, clients, entrepot
from reglages import reglages

routeur = APIRouter(tags=["Trajets"])


class Matrice(BaseModel):
    lieux: list[Lieu]
    metres: list[list[int]]
    secondes: list[list[int]]


class Trajet(BaseModel):
    client: str
    ville: str
    km: float
    minutes: int


def coordonnees(lieux: list[Lieu]) -> str:
    return ";".join(f"{lieu.longitude},{lieu.latitude}" for lieu in lieux)


def appeler_osrm(chemin: str) -> dict:
    try:
        reponse = httpx.get(f"{reglages.osrm_url}{chemin}", timeout=10)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="OSRM ne répond pas. Est-il lancé ? Voir le README.",
        )
    return reponse.json()


def verifier_routes(lieux: list[Lieu], durees: list[list[float | None]]) -> None:
    for depart, ligne in enumerate(durees):
        for arrivee, duree in enumerate(ligne):
            if duree is None:
                raise HTTPException(
                    status_code=502,
                    detail=f"Aucune route trouvée de {lieux[depart].nom} à {lieux[arrivee].nom}",
                )


def arrondir(tableau: list[list[float]]) -> list[list[int]]:
    return [[round(valeur) for valeur in ligne] for ligne in tableau]


def demander_matrice(lieux: list[Lieu]) -> Matrice:
    donnees = appeler_osrm(f"/table/v1/driving/{coordonnees(lieux)}?annotations=distance,duration")
    if donnees.get("code") != "Ok":
        raise HTTPException(
            status_code=502,
            detail=f"OSRM a refusé la demande : {donnees.get('message', donnees.get('code'))}",
        )
    verifier_routes(lieux, donnees["durations"])
    return Matrice(
        lieux=lieux,
        metres=arrondir(donnees["distances"]),
        secondes=arrondir(donnees["durations"]),
    )


@routeur.get("/trajets/depuis-entrepot")
def trajets_depuis_entrepot() -> list[Trajet]:
    matrice = demander_matrice([entrepot, *clients])
    trajets = []
    for numero, client in enumerate(clients, start=1):
        trajets.append(
            Trajet(
                client=client.nom,
                ville=client.ville,
                km=round(matrice.metres[0][numero] / 1000, 1),
                minutes=round(matrice.secondes[0][numero] / 60),
            )
        )
    return sorted(trajets, key=lambda trajet: trajet.minutes)
