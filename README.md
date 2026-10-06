# Hydlearn (conteneurisé)

Hydlearn est un site d'e-learning où des instructeurs publient des cours en PDF et où des apprenants s'inscrivent, lisent les cours et échangent sur un forum.

## Prérequis

- Docker Engine 20.10 ou plus récent
- Docker Compose v2 (la commande s'écrit `docker compose`, avec un espace)

Vérification : `docker --version` et `docker compose version`.

## Démarrage

```bash
git clone https://github.com/Kakashi97/Hydlearn.git
cd Hydlearn
cp .env.example .env
docker compose up --build
```

## Accès

Ouvrez **http://localhost:8000** dans votre navigateur.

 **Port 8000 déjà utilisé** : dans `compose.yaml`, remplacez `"8000:8000"` par `"8080:8000"` et ouvrez http://localhost:8080.


Pour commencer : créez un compte « instructor » pour publier un cours (PDF + image), puis un compte « learner » pour vous y inscrire depuis la page *Courses*.

## Variables d'environnement

Elles sont lues depuis le fichier `.env` (créé à à partir de `.env.example`, qui contient des valeurs de développement utilisables telles quelles).

| Variable | Rôle |
|---|---|
| `DB_HOST` | Nom du service de la base sur le réseau Compose. Doit rester `db`. |
| `DB_PORT` | Port interne de PostgreSQL (`5432`). |
| `DB_USER` | Utilisateur PostgreSQL créé au premier démarrage. |
| `DB_PASSWORD` | Mot de passe technique utilisé par l'application pour se connecter à PostgreSQL. Sans lien avec les mots de passe des comptes du site. |
| `DB_NAME` | Nom de la base de données. |
| `SECRET_KEY` | Clé secrète de Flask pour signer les sessions. |

Attention : `DB_USER`, `DB_PASSWORD` et `DB_NAME` ne sont lus par PostgreSQL qu'à la **création** du volume.

## Commandes utiles

```bash
docker compose exec db psql -U hydlearn -d hydlearn     # ouvrir un shell SQL dans la base
docker compose down                                     # tout arrêter (les données sont conservées)
docker compose down -v                                  # tout arrêter ET supprimer les données

```

Après une modification du code ou du `Dockerfile`, relancez avec `docker compose up --build`.

