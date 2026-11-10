from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from catalogue import routeur as routeur_catalogue
from clients import routeur as routeur_clients
from commandes import routeur as routeur_commandes
from erreurs import erreurs_en_francais
from tournees import routeur as routeur_tournees
from trajets import routeur as routeur_trajets

app = FastAPI(title="Relais API")
app.add_exception_handler(RequestValidationError, erreurs_en_francais)
app.include_router(routeur_commandes)
app.include_router(routeur_catalogue)
app.include_router(routeur_clients)
app.include_router(routeur_trajets)
app.include_router(routeur_tournees)


@app.get("/")
def accueil():
    return {"message": "L'API de Relais est en marche"}
