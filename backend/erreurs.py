from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

messages = {
    "missing": "Champ obligatoire",
    "greater_than": "Doit être plus grand que {gt}",
    "too_short": "Il faut au moins {min_length} élément",
    "string_too_short": "Il faut au moins {min_length} caractère",
    "enum": "Valeur non permise. Choix possibles : {expected}",
    "int_parsing": "Doit être un nombre entier",
    "int_from_float": "Doit être un nombre entier, sans décimales",
    "int_type": "Doit être un nombre entier",
    "string_type": "Doit être du texte",
    "list_type": "Doit être une liste",
    "model_attributes_type": "Doit être un objet JSON",
    "json_invalid": "JSON mal formé : il manque peut-être une virgule, un guillemet ou une accolade",
}


def traduire(erreur: dict) -> str:
    modele = messages.get(erreur["type"])
    if modele is None:
        return erreur["msg"]
    contexte = erreur.get("ctx", {})
    message = modele.format(**contexte)
    return message.replace(" or ", " ou ")


def erreurs_en_francais(request: Request, erreur: RequestValidationError) -> JSONResponse:
    details = erreur.errors()
    for detail in details:
        detail["msg"] = traduire(detail)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(details)})
