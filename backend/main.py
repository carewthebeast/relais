from fastapi import FastAPI

app = FastAPI(title="Relais API")


@app.get("/")
def accueil():
    return {"message": "L'API de Relais est en marche"}