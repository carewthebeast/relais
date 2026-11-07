# Relais

Plateforme de coordination des opérations pour la distribution alimentaire. Relais relie la prise de commandes, la validation humaine, la répartition des tournées de livraison et le suivi d'équipe dans un seul outil.

Relais ne remplace pas l'ERP ou le CRM du client : il travaille à côté, relié par un plugin. L'équipe du client reste dans son outil habituel. Premier plugin : Odoo.

Toutes les données sont fictives et identifiées comme telles (clients, adresses, employés). Aucune donnée personnelle réelle (Loi 25).

## Pile technique

- **Backend :** Python 3.13, FastAPI, Pydantic — dossier `backend/`, point d'entrée `backend/main.py`, environnement virtuel `backend/.venv`
- **Plugin :** module Odoo (Python), version Community installée en local
- **Frontend :** React (Vite) — dossier `frontend/`
- **Données :** en mémoire pour commencer, puis SQLite
- Lancer l'API : `cd backend && source .venv/bin/activate && fastapi dev main.py` puis http://127.0.0.1:8000/docs

## Fonctionnalités, dans l'ordre

1. **Commandes** — créer et lister des commandes (client, produit, quantité). Règles de validation : quantité valide, produit présent au catalogue. Statuts : reçue → à vérifier → validée → envoyée à l'entrepôt. Chaque commande garde sa `source` (formulaire, texte libre, ERP) et sa `reference_externe` (son numéro dans l'ERP du client).
2. **Validation humaine** — une personne approuve ou corrige chaque commande avant l'envoi à l'entrepôt ; on garde le nom de la personne et l'historique.
3. **Lecture automatique** — transformer une commande reçue en texte libre (texto, courriel, transcription d'un message vocal) en commande structurée, toujours suivie d'une validation humaine.
4. **Tournées** — regrouper les commandes validées en tournées de livraison et optimiser l'ordre des arrêts sur un scénario simulé, en affichant les kilomètres avant et après.
5. **Équipe** — qui fait quelle tournée.
6. **Connexion pour le plugin** — une clé d'API (dans `.env`) pour que seul le plugin puisse envoyer des commandes, et une route pour lire le statut d'une commande. Une même `reference_externe` envoyée deux fois ne crée pas de doublon. Les données de l'ERP peuvent être désordonnées : on nettoie seulement ce qui est sûr (espaces, majuscules, virgule décimale), on rapproche les produits du catalogue de Relais, et en cas de doute la commande passe « à vérifier ». Jamais de correction silencieuse.
7. **Plugin Odoo** — module Odoo qui envoie les nouvelles commandes à Relais et affiche leur statut dans Odoo.
8. **Interface React** — tableau de bord par onglets : Commandes, Validation, Tournées, Équipe.

Le backend (1 à 6) vient d'abord, puis le plugin Odoo, puis React.

On termine et on teste une fonctionnalité avant de passer à la suivante.

## Règles de travail

- Le développeur apprend en construisant : **explique chaque nouveau concept** en une ou deux phrases (ce que c'est, à quoi ça sert) et chaque changement apporté.
- Code simple et lisible : petites fonctions, noms en français cohérents (`commande`, `client`, `produit`, `quantite`).
- Avance par petites étapes ; propose un message de commit à la fin de chaque étape.
- Ne jamais mettre de secrets (clés d'API, mots de passe) dans le code : utiliser un fichier `.env` qui n'est jamais commité.
- Interface et messages en français.
