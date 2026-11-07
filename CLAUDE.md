# Relais

Application d'opérations pour un distributeur alimentaire. Relais relaie chaque commande du client à l'entrepôt, puis au camion, sans rien perdre en chemin. Elle donne aussi au coordonnateur TI un seul endroit pour gérer le budget, les projets et l'équipement.

Relais ne remplace pas l'ERP ou le CRM du client : il travaille à côté, relié par un plugin. L'équipe du client reste dans son outil habituel. Premier plugin : Odoo.

## Données fictives

- Toutes les données sont fictives et identifiées comme telles : distributeur, clients, adresses, employés, procédures. Aucune donnée personnelle réelle (Loi 25).
- Le distributeur porte un nom inventé, marqué comme fictif. Aucun nom, logo ou donnée d'une vraie entreprise dans l'application.
- Le modèle de prédiction des temps est entraîné sur des trajets simulés, et l'application le dit.

## Problèmes à résoudre

| Problème | Aujourd'hui, sans Relais |
|---|---|
| Commandes désordonnées | Les clients commandent par texto, courriel ou message vocal, et quelqu'un retape tout dans l'ERP : c'est lent et il y a des erreurs |
| Tournées inefficaces | Les camions suivent l'ordre des appels : des km en trop et des livraisons urgentes en retard |
| Temps de trajet inconnus | La neige, le trafic et le chargement changent les temps, et personne ne peut les prévoir |
| Procédures perdues | Les employés ne savent pas comment faire et s'interrompent entre eux |
| Passations perdues | Le service à la clientèle, l'entrepôt et la répartition ne savent pas qui fait quoi |
| TI dispersées | Le budget, les projets et l'équipement sont suivis à des endroits différents |

## Pile technique

- **Backend :** Python 3.13, FastAPI, Pydantic — dossier `backend/`, point d'entrée `backend/main.py`, environnement virtuel `backend/.venv`
- **Tests :** pytest — dossier `backend/tests/`
- **Données :** en mémoire pour commencer, puis SQLite
- **Tournées :** OSRM pour les routes réelles (installé en local), OR-Tools pour l'optimisation, scikit-learn pour la prédiction des temps, Open-Meteo pour la météo
- **Plugin :** module Odoo (Python), version Community installée en local
- **Frontend :** React (Vite) et MapLibre pour la carte — dossier `frontend/`
- Installer les dépendances : `cd backend && source .venv/bin/activate && pip install -r requirements.txt`. Chaque nouveau paquet est ajouté à `requirements.txt` avec sa version.
- Lancer l'API : `cd backend && source .venv/bin/activate && fastapi dev main.py` puis http://127.0.0.1:8000/docs
- Lancer les tests : `cd backend && source .venv/bin/activate && pytest`

## Organisation du backend

```
backend/
  main.py         crée l'application et branche les routeurs
  commandes.py    routes des commandes (un fichier par partie)
  donnees/        données fictives : catalogue, clients, procédures
  tests/          tests automatiques
```

Chaque partie a son propre fichier avec un `APIRouter`, que `main.py` branche. Les routes sont en français : `/commandes`, `/tournees`, etc.

## Phases, dans l'ordre

1. **Commandes**
   - Lire un message de client (texto, courriel, transcription d'un message vocal) et en tirer des lignes de commande propres, rapprochées du catalogue : `POST /commandes/analyser`. Des règles d'abord, un vrai modèle d'IA plus tard.
   - Signaler les lignes floues. Une personne confirme ou corrige chaque commande avant tout envoi à l'entrepôt, et on garde son nom et l'historique : `POST /commandes`.
   - Règles de validation : quantité valide, produit présent au catalogue. Statuts : reçue → à vérifier → validée → envoyée à l'entrepôt.
   - Chaque commande garde sa `source` (formulaire, texte libre, ERP) et sa `reference_externe` (son numéro dans l'ERP du client).
2. **Tournées**
   - Clients fictifs dans la région de Granby. Routes réelles avec OSRM : km et temps de conduite réels.
   - Optimisation avec OR-Tools : le meilleur ordre des arrêts, en respectant les compartiments congelé, réfrigéré et sec, les livraisons urgentes et les plages horaires.
   - Km et temps avant et après l'optimisation, puis l'ordre de chargement envoyé à l'entrepôt.
3. **Prédiction des temps** — un modèle de gradient boosting ajuste les temps selon la météo (Open-Meteo), l'heure et le chargement. Exemple : « Neige demain : +18 min ».
4. **Procédures, Équipe, Projets et parc**
   - Procédures : un employé pose une question en mots simples, et Relais répond à partir des procédures écrites en nommant le responsable. Les questions sans réponse vont au coordonnateur TI.
   - Équipe : chaque tâche et chaque passation, de qui à qui, dans un fil d'équipe en direct.
   - Projets et parc : budget TI, projets, demandes de l'équipe, état de l'équipement et de l'infrastructure.
5. **Intégration**
   - Connexion pour le plugin : une clé d'API (dans `.env`) pour que seul le plugin puisse envoyer des commandes, et une route pour lire le statut d'une commande. Une même `reference_externe` envoyée deux fois ne crée pas de doublon.
   - Données de l'ERP désordonnées : on nettoie seulement ce qui est sûr (espaces, majuscules, virgule décimale), on rapproche les produits du catalogue, et en cas de doute la commande passe « à vérifier ». Jamais de correction silencieuse.
   - Plugin Odoo : il envoie les nouvelles commandes à Relais et affiche leur statut dans Odoo.
   - Un schéma qui montre comment Relais se branche à l'ERP, au CRM et au logiciel de répartition.
6. **Interface React** — onglets Commandes, Tournées, Procédures, Équipe, Projets et parc, Intégration. Carte interactive de la région de Granby avec MapLibre (zoom, déplacement, inclinaison 3D), un camion qui roule sur la tournée, des arrêts qui changent de couleur une fois livrés, et une bascule « tournée reçue / tournée optimisée ».

On termine et on teste une phase avant de passer à la suivante.

## Règles de travail

- Le développeur apprend en construisant : **explique chaque nouveau concept** en une ou deux phrases (ce que c'est, à quoi ça sert) et chaque changement apporté.
- Code simple et lisible : petites fonctions, noms en français cohérents (`commande`, `client`, `produit`, `quantite`).
- Chaque route a au moins un test automatique (pytest).
- Avance par petites étapes ; propose un message de commit à la fin de chaque étape.
- Ne jamais mettre de secrets (clés d'API, mots de passe) dans le code : utiliser un fichier `.env` qui n'est jamais commité.
- Interface et messages en français.
