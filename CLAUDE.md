# Relais

Plateforme de coordination des opérations pour la distribution alimentaire. Relais relie la prise de commandes, la validation humaine, la répartition des tournées de livraison et le suivi d'équipe dans un seul outil.

Toutes les données sont fictives et identifiées comme telles (clients, adresses, employés). Aucune donnée personnelle réelle (Loi 25).

## Pile technique

- **Backend :** Python 3.13, FastAPI, Pydantic — dossier `backend/`, point d'entrée `backend/main.py`, environnement virtuel `backend/.venv`
- **Frontend :** React (Vite) — dossier `frontend/`
- **Données :** en mémoire pour commencer, puis SQLite
- Lancer l'API : `cd backend && source .venv/bin/activate && fastapi dev main.py` puis http://127.0.0.1:8000/docs

## Fonctionnalités, dans l'ordre

1. **Commandes** — créer et lister des commandes (client, produit, quantité). Règles de validation : quantité valide, produit présent au catalogue. Statuts : reçue → à vérifier → validée → envoyée à l'entrepôt.
2. **Validation humaine** — une personne approuve ou corrige chaque commande avant l'envoi à l'entrepôt ; on garde le nom de la personne et l'historique.
3. **Lecture automatique** — transformer une commande reçue en texte libre (texto, courriel, transcription d'un message vocal) en commande structurée, toujours suivie d'une validation humaine.
4. **Tournées** — regrouper les commandes validées en tournées de livraison et optimiser l'ordre des arrêts sur un scénario simulé, en affichant les kilomètres avant et après.
5. **Équipe** — qui fait quelle tournée.
6. **Interface React** — tableau de bord par onglets : Commandes, Validation, Tournées, Équipe.

On termine et on teste une fonctionnalité avant de passer à la suivante.

## Règles de travail

- Le développeur apprend en construisant : **explique chaque nouveau concept** en une ou deux phrases (ce que c'est, à quoi ça sert) et chaque changement apporté.
- Code simple et lisible : petites fonctions, noms en français cohérents (`commande`, `client`, `produit`, `quantite`).
- Avance par petites étapes ; propose un message de commit à la fin de chaque étape.
- Ne jamais mettre de secrets (clés d'API, mots de passe) dans le code : utiliser un fichier `.env` qui n'est jamais commité.
- Interface et messages en français.
