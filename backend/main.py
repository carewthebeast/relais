from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from commandes import routeur as routeur_commandes
from erreurs import erreurs_en_francais

app = FastAPI(title="Relais API")
app.add_exception_handler(RequestValidationError, erreurs_en_francais)
app.include_router(routeur_commandes)


@app.get("/")
def accueil():
    return {"message": "L'API de Relais est en marche"}
