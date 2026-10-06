# RAPPORT : Hydlearn conteneurisé

Application : Flask + PostgreSQL (migrée depuis SQLite). Deux services : `web` (Gunicorn) et `db` (PostgreSQL 16).
Mesures prises sur ma machine : WSL (Ubuntu) sous Windows, Docker Desktop, projet situé dans `/mnt/c/...`.

## Image de base

J'ai retenu **`python:3.12-slim`** pour le service `web`.

- `python:3.12` (complète): image bien plus lourde pour aucun bénéfice.
- `python:3.12-alpine`: la plus petite, mais des dépendances comme `psycopg2` peuvent nécessiter une compilation et des paquets système supplémentaires.
- `python:3.12-slim` est un compromis : image officielle, glibc, et `psycopg2-binary` s'installe directement sans compilation.

Le tag `3.12-slim` fixe la version mineure de Python (pas de saut de version involontaire). 
`postgres:16` fixe la version majeure de la base.

## Cache

Les dépendances (qui changent rarement) sont installées avant la copie du code (qui change souvent). Quand je modifie une ligne de `app.py`, seule la couche `COPY app/ .` (et celles qui la suivent) est reconstruite ; 

**Build 1 : `--no-cache`**
(Docker n'a aucune couche déjà construite à réutiliser. Il doit donc tout refaire depuis le début.)
```
[+] Building 22.0s (12/12) FINISHED

[+] build 1/1
 ✔ Image hydlearn-web Built                                                                                              22.4s

real    0m23.310s
user    0m0.587s
sys     0m0.896s
```

**Build 2 : aucun changement**
```
[+] Building 2.4s (12/12) FINISHED

 ✔ Image hydlearn-web Built                                                                                               3.0s

real    0m3.384s
user    0m0.423s
sys     0m0.506s
```

**Build 3 : une ligne ajoutée dans `app.py`**
```
[+] Building 3.8s (12/12) FINISHED

[+] build 1/1
 ✔ Image hydlearn-web Built                                                                                               4.6s

real    0m6.168s
user    0m0.490s
sys     0m0.874s
```


## Taille

Image `hydlearn-web:latest` :

```
hydlearn-web:latest    224MB (disk usage)   55.1MB (content size)
```

224 MB est la taille décompressée sur disque ; 55,1 MB est la taille compressée, celle qui serait transférée vers un registre.

Je n'ai pas optimisé la taille au-delà du choix de `slim`.

##  Persistance

Les données de PostgreSQL sont stockées dans le volume nommé `pgdata`, monté sur `/var/lib/postgresql/data`. Contrôle utilisé avant/après chaque test :

```bash
docker compose exec db psql -U hydlearn -d hydlearn -c "SELECT id, name, role FROM users;"
```

**`docker compose down` puis `up`** : les conteneurs et le réseau sont supprimés puis recréés, mais le volume est conservé. PostgreSQL trouve un dossier de données déjà initialisé, donc il ne rejoue pas `init.sql`. Les utilisateurs et les cours créés depuis le navigateur sont toujours là.

```
 id | name  |    role
----+-------+------------
  1 | Thami | instructor
(1 row)
```

**`docker compose down -v`** : le volume `pgdata` est aussi supprimé. Au `up` suivant, le dossier de données est vide : PostgreSQL se réinitialise (`initdb`) et exécute `init.sql`, qui recrée les tables vides. Toutes les données sont perdues.
```
 ✔ Volume hydlearn_pgdata   Removed
```
```
 id | name | role
----+------+------
(0 rows)
```
