import unicodedata


def enlever_accents(texte: str) -> str:
    resultat = ""
    for lettre in unicodedata.normalize("NFD", texte):
        if not unicodedata.combining(lettre):
            resultat += lettre
    return resultat


def normaliser(texte: str) -> str:
    texte = " ".join(texte.split()).lower()
    texte = texte.replace("œ", "oe").replace("’", "'")
    return enlever_accents(texte)
