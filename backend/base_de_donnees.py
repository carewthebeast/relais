import sqlite3
from contextlib import contextmanager
from pathlib import Path

chemin_base = Path(__file__).parent / "relais.db"

tables = """
CREATE TABLE IF NOT EXISTS commandes (
    id INTEGER PRIMARY KEY,
    client TEXT NOT NULL,
    urgente INTEGER NOT NULL CHECK (urgente IN (0, 1)),
    source TEXT NOT NULL,
    reference_externe TEXT,
    statut TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lignes (
    id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL REFERENCES commandes (id),
    produit TEXT NOT NULL,
    quantite INTEGER NOT NULL CHECK (quantite > 0)
);

CREATE TABLE IF NOT EXISTS evenements (
    id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL REFERENCES commandes (id),
    statut TEXT NOT NULL,
    par TEXT NOT NULL,
    date TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


@contextmanager
def ouvrir():
    connexion = sqlite3.connect(chemin_base)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    connexion.executescript(tables)
    try:
        with connexion:
            yield connexion
    finally:
        connexion.close()
