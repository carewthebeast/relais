from fastapi import FastAPI

from commandes import routeur as routeur_commandes

app = FastAPI(title="Relais API")
app.include_router(routeur_commandes)


@app.get("/")
def accueil():
    return {"message": "L'API de Relais est en marche"}
