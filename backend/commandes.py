import sqlite3
import unicodedata
from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from base_de_donnees import ouvrir

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


class Statut(StrEnum):
    RECUE = "recue"
    A_VERIFIER = "a_verifier"
    VALIDEE = "validee"
    ENVOYEE_ENTREPOT = "envoyee_entrepot"


class Source(StrEnum):
    FORMULAIRE = "formulaire"
    TEXTE_LIBRE = "texte_libre"
    ERP = "erp"


class Ligne(BaseModel):
    produit: str
    quantite: int = Field(gt=0)


class NouvelleCommande(BaseModel):
    client: str
    lignes: list[Ligne] = Field(min_length=1)
    source: Source = Source.FORMULAIRE
    reference_externe: str | None = None


class Evenement(BaseModel):
    statut: Statut
    par: str
    date: datetime
    detail: str


class Commande(NouvelleCommande):
    id: int
    statut: Statut
    historique: list[Evenement]


class Action(BaseModel):
    par: str = Field(min_length=1)


class Validation(Action):
    lignes: list[Ligne] | None = Field(default=None, min_length=1)


class Message(BaseModel):
    texte: str = Field(min_length=1)


class LigneAVerifier(BaseModel):
    texte: str
    quantite: int | None
    suggestions: list[str]
    raisons: list[str]


class Lecture(BaseModel):
    lignes: list[Ligne]
    a_verifier: list[LigneAVerifier]


mots_ignores = {"bonjour", "salut", "allo", "merci", "svp", "stp"}


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


def trouver_produit(produit: str) -> str | None:
    for nom in catalogue:
        if normaliser(nom) == normaliser(produit):
            return nom
    return None


def rapprocher_lignes(lignes: list[Ligne]) -> list[Ligne]:
    propres = []
    absents = []
    for ligne in lignes:
        nom_officiel = trouver_produit(ligne.produit)
        if nom_officiel is None:
            absents.append(ligne.produit)
        else:
            propres.append(Ligne(produit=nom_officiel, quantite=ligne.quantite))
    if absents:
        raise HTTPException(
            status_code=422,
            detail=f"Absent du catalogue : {', '.join(absents)}",
        )
    return propres


def decrire(lignes: list[Ligne]) -> str:
    morceaux = []
    for ligne in lignes:
        morceaux.append(f"{ligne.quantite} {ligne.produit}")
    return ", ".join(morceaux)


def decouper(texte: str) -> list[str]:
    for separateur in ["\n", ";", ". ", "! ", " et ", " pis "]:
        texte = texte.replace(separateur, ",")
    morceaux = []
    for morceau in texte.split(","):
        morceau = morceau.strip()
        if morceau:
            morceaux.append(morceau)
    return morceaux


def garder_mots_utiles(morceau: str) -> list[str]:
    mots = []
    for mot in normaliser(morceau).split():
        mot = mot.strip(".!?")
        if mot and mot not in mots_ignores:
            mots.append(mot)
    return mots


def lire_quantite(mots: list[str]) -> tuple[int | None, list[str]]:
    if mots and mots[0].isdigit() and int(mots[0]) > 0:
        return int(mots[0]), mots[1:]
    return None, mots


def suggerer(texte: str) -> list[str]:
    mots = set(normaliser(texte).split())
    if not mots:
        return []
    suggestions = []
    for nom in catalogue:
        mots_du_nom = set(normaliser(nom).split())
        if mots <= mots_du_nom or mots_du_nom <= mots:
            suggestions.append(nom)
    return suggestions


def lire_morceau(morceau: str, lecture: Lecture) -> None:
    mots = garder_mots_utiles(morceau)
    if not mots:
        return
    quantite, mots_du_produit = lire_quantite(mots)
    texte_produit = " ".join(mots_du_produit)
    produit = trouver_produit(texte_produit)
    if produit is not None and quantite is not None:
        lecture.lignes.append(Ligne(produit=produit, quantite=quantite))
        return
    raisons = []
    if produit is None:
        raisons.append("Produit pas reconnu")
    if quantite is None:
        raisons.append("Quantité manquante")
    lecture.a_verifier.append(
        LigneAVerifier(
            texte=morceau,
            quantite=quantite,
            suggestions=suggerer(texte_produit),
            raisons=raisons,
        )
    )


def enregistrer_lignes(connexion: sqlite3.Connection, commande_id: int, lignes: list[Ligne]) -> None:
    for ligne in lignes:
        connexion.execute(
            "INSERT INTO lignes (commande_id, produit, quantite) VALUES (?, ?, ?)",
            (commande_id, ligne.produit, ligne.quantite),
        )


def changer_statut(
    connexion: sqlite3.Connection, commande_id: int, statut: Statut, par: str, detail: str
) -> None:
    connexion.execute(
        "UPDATE commandes SET statut = ? WHERE id = ?",
        (statut, commande_id),
    )
    connexion.execute(
        "INSERT INTO evenements (commande_id, statut, par, date, detail) VALUES (?, ?, ?, ?, ?)",
        (commande_id, statut, par, datetime.now().astimezone().isoformat(), detail),
    )


def charger_commande(connexion: sqlite3.Connection, rangee: sqlite3.Row) -> Commande:
    lignes = connexion.execute(
        "SELECT produit, quantite FROM lignes WHERE commande_id = ? ORDER BY id",
        (rangee["id"],),
    ).fetchall()
    evenements = connexion.execute(
        "SELECT statut, par, date, detail FROM evenements WHERE commande_id = ? ORDER BY id",
        (rangee["id"],),
    ).fetchall()
    return Commande(
        id=rangee["id"],
        client=rangee["client"],
        source=rangee["source"],
        reference_externe=rangee["reference_externe"],
        statut=rangee["statut"],
        lignes=[Ligne(**ligne) for ligne in lignes],
        historique=[Evenement(**evenement) for evenement in evenements],
    )


def trouver_commande(connexion: sqlite3.Connection, commande_id: int) -> Commande:
    rangee = connexion.execute(
        "SELECT * FROM commandes WHERE id = ?",
        (commande_id,),
    ).fetchone()
    if rangee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Commande introuvable : {commande_id}",
        )
    return charger_commande(connexion, rangee)


@routeur.post("/commandes")
def creer_commande(commande: NouvelleCommande) -> Commande:
    lignes = rapprocher_lignes(commande.lignes)
    with ouvrir() as connexion:
        curseur = connexion.execute(
            "INSERT INTO commandes (client, source, reference_externe, statut) VALUES (?, ?, ?, ?)",
            (commande.client, commande.source, commande.reference_externe, Statut.RECUE),
        )
        commande_id = curseur.lastrowid
        enregistrer_lignes(connexion, commande_id, lignes)
        changer_statut(connexion, commande_id, Statut.RECUE, commande.client, f"Reçue ({commande.source})")
        return trouver_commande(connexion, commande_id)


@routeur.post("/commandes/analyser")
def analyser_message(message: Message) -> Lecture:
    lecture = Lecture(lignes=[], a_verifier=[])
    for morceau in decouper(message.texte):
        lire_morceau(morceau, lecture)
    return lecture


@routeur.get("/commandes")
def lister_commandes() -> list[Commande]:
    with ouvrir() as connexion:
        rangees = connexion.execute("SELECT * FROM commandes ORDER BY id").fetchall()
        return [charger_commande(connexion, rangee) for rangee in rangees]


@routeur.get("/commandes/{commande_id}")
def lire_commande(commande_id: int) -> Commande:
    with ouvrir() as connexion:
        return trouver_commande(connexion, commande_id)


@routeur.post("/commandes/{commande_id}/valider")
def valider_commande(commande_id: int, validation: Validation) -> Commande:
    with ouvrir() as connexion:
        commande = trouver_commande(connexion, commande_id)
        if commande.statut not in (Statut.RECUE, Statut.A_VERIFIER):
            raise HTTPException(
                status_code=409,
                detail=f"Impossible de valider : la commande est déjà « {commande.statut} »",
            )
        if validation.lignes is None:
            changer_statut(connexion, commande_id, Statut.VALIDEE, validation.par, "Validée telle quelle")
        else:
            nouvelles = rapprocher_lignes(validation.lignes)
            connexion.execute("DELETE FROM lignes WHERE commande_id = ?", (commande_id,))
            enregistrer_lignes(connexion, commande_id, nouvelles)
            changer_statut(
                connexion,
                commande_id,
                Statut.VALIDEE,
                validation.par,
                f"Corrigée et validée. Avant : {decrire(commande.lignes)}",
            )
        return trouver_commande(connexion, commande_id)


@routeur.post("/commandes/{commande_id}/envoyer")
def envoyer_a_l_entrepot(commande_id: int, action: Action) -> Commande:
    with ouvrir() as connexion:
        commande = trouver_commande(connexion, commande_id)
        if commande.statut != Statut.VALIDEE:
            raise HTTPException(
                status_code=409,
                detail="Une commande doit être validée avant l'envoi à l'entrepôt",
            )
        changer_statut(connexion, commande_id, Statut.ENVOYEE_ENTREPOT, action.par, "Envoyée à l'entrepôt")
        return trouver_commande(connexion, commande_id)
