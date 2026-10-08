# Réveil musical
> CECCARELLI Luca

Service qui réveille un utilisateur avec un morceau choisi selon le jour de la semaine et la
météo, puis le prévient sur son canal préféré (email, SMS ou push — simulés).

## Lancer

```bash
uv sync                 # crée l'environnement (Python ≥ 3.12)
uv run reveil-musical   # démarre l'API sur http://127.0.0.1:8000 (doc interactive : /docs)
uv run pytest           # tests + couverture (échec sous 95 %)
uv run ruff check .     # lint
```

Le point d'entrée est `POST /wake-up`, l'appel que l'ordonnanceur (externe, non codé) exécute à
l'heure du réveil :

```bash
curl -X POST localhost:8000/wake-up -H 'content-type: application/json' \
     -d '{"user_id": "alice", "day": "LUNDI", "weather": "PLUIE"}'
```

Réponse (tirage au sort parmi les candidats du jour et de la météo, ici l'un des trois possibles) :

```json
{"user_id": "alice", "channel": "EMAIL", "delivered_via": "EMAIL", "day": "LUNDI", "weather": "PLUIE",
 "track_title": "Riders on the Storm", "track_artist": "The Doors",
 "text": "Bonjour, c'est lundi et il fait pluie : réveil avec « Riders on the Storm » de The Doors."}
```

Jours : `LUNDI … DIMANCHE`. Météo : `SOLEIL / PLUIE / NEIGE / NUAGEUX` (fournis en entrée,
aucun appel météo). Choix du morceau : l'utilisateur liste plusieurs morceaux par jour et par météo ;
le réveil tire au sort parmi la réunion des deux listes (un lundi de neige, les morceaux du
lundi et ceux de la neige sont tous candidats). Si aucune des deux listes ne couvre le cas,
tirage parmi les morceaux de secours. Réponses : `404` utilisateur inconnu, `422` entrée invalide.
Une panne de canal ne produit jamais d'erreur : voir « Jamais de silence » ci-dessous.
`channel` est le canal préféré, `delivered_via` celui réellement utilisé : s'ils diffèrent,
l'envoi s'est fait en mode dégradé (`CONSOLE` = dernier recours).
Utilisateurs de démo : `alice` (email), `bob` (SMS), `carol` (push) — voir `users.py`.

Extension assumée du sujet : l'énoncé décrit *un* morceau par type de météo et *un* morceau de
secours. J'ai gardé ce contrat (une liste à un élément s'y ramène) mais l'ai élargi à
plusieurs morceaux par météo, plusieurs morceaux de secours et une liste par jour de la semaine.
Le sujet annonce en effet un morceau « choisi selon le jour de la semaine et la météo du jour » :
sans liste par jour, le jour ne pèserait pas sur le choix, et avec un seul morceau par météo
l'utilisateur entendrait le même titre chaque matin de pluie. Le tirage au sort dans la réunion
des deux listes fait varier le réveil sans ajouter de règle d'historique (« jamais le même
qu'hier ») : le jour et la météo changent, le tirage suffit.

## Architecture

```
src/reveil_musical/
├── domain.py            modèle métier + ports (Protocol) : MusicProvider, Notifier, UserPreferencesProvider
├── wake_up.py           WakeUpService : le cas d'usage, ne dépend que des ports
├── users.py             mock du service interne de préférences
├── music/
│   ├── http.py          port HttpClient + implémentation urllib (stdlib)
│   ├── itunes.py        adaptateur iTunes Search API
│   ├── musicbrainz.py   adaptateur MusicBrainz (User-Agent identifiable)
│   ├── local.py         liste codée en dur : complète un titre connu sans réseau, ne tombe jamais
│   └── resilient.py     CachedMusicProvider (rate-limit) + FallbackChainMusicProvider
├── notification/
│   ├── mocks.py         EmailMock / SmsMock / PushMock, interfaces volontairement différentes
│   ├── adapters.py      ramènent chaque mock vers le port Notifier
│   └── router.py        ChannelRouter : canal préféré, sinon un autre (mode dégradé), sinon la console
├── container.py         conteneur DI (dependency-injector) : seul endroit où le concret est assemblé
└── api.py               point d'entrée HTTP (FastAPI) : POST /wake-up
```

Traduction des quatre exigences :

| Besoin métier | Réponse technique |
|---|---|
| Changer de fournisseur musical | `MusicProvider` est un port ; iTunes, MusicBrainz et le fallback local sont interchangeables. `trackViewUrl` et `artist-credit` ne sortent pas de leur adaptateur : le métier ne voit que `Track(title, artist)`. |
| Ajouter un canal (WhatsApp, vocal…) | Une valeur dans l'enum `Channel`, un adaptateur `Notifier` et une entrée dans le `ChannelRouter` du conteneur. Le métier ne change pas. |
| Vérification des dépendances | Tableau ci-dessous, régénérable avec `uv tree --outdated` et `uvx pip-licenses`. HTTP sortant via `urllib` (stdlib), pas de SDK tiers. |
| Jamais de silence | Chaîne de fournisseurs avec fallback local en fin de chaîne ; routeur de canaux qui bascule sur un autre canal si le préféré est en panne, et sur `ConsoleNotifier` (dernier recours, ne dépend de rien) si tous le sont. Une panne est journalisée (`WARNING`, `ERROR` pour le dernier recours), jamais bloquante : l'API répond toujours `200` et expose le canal utilisé dans `delivered_via`. Si aucun fournisseur ne connaît le titre (tous en panne, ou titre absent de la liste locale), le titre choisi par l'utilisateur est envoyé tel quel, avec « artiste inconnu » : le mode dégradé ne remplace jamais le morceau choisi par un autre. |

Isolation / DI : `WakeUpService` ne reçoit que des ports via son constructeur. Aucune classe
métier n'instancie d'implémentation concrète ; l'assemblage est déclaré dans `container.py`
(`Container`, un `DeclarativeContainer` de `dependency-injector`). Chaque fournisseur, canal
ou client HTTP est un `provider` remplaçable par `container.<nom>.override(...)` — c'est ce que
font les tests, et ce que ferait un changement de fournisseur en production. L'API reçoit le
service par `Depends`, elle ne connaît pas non plus les implémentations.

Rate-limit iTunes (~20 req/min) : deux décorateurs empilés. `CachedMusicProvider` mémorise
chaque requête réussie 1 h : un même titre n'est demandé à iTunes qu'une fois par heure, quel
que soit le nombre d'utilisateurs qui l'ont choisi. En dessous, `RateLimitedMusicProvider`
compte les appels réels dans une fenêtre glissante (20 par 60 s pour iTunes, 1 par seconde pour
MusicBrainz) : au-delà du quota, il répond `None` sans appeler l'API et la chaîne passe au
fournisseur suivant. Un fournisseur en panne est donc lui aussi sollicité au plus 20 fois par
minute. Limites assumées : compteurs en mémoire du processus (un quota par instance, pas
partagé entre plusieurs workers) et cache sans borne de taille (une entrée par titre distinct).

## Design patterns

| Pattern | Où | Pourquoi |
|---|---|---|
| Adapter | `notification/adapters.py`, `music/itunes.py`, `music/musicbrainz.py` | ramener des interfaces hétérogènes (mocks, JSON des APIs) vers les ports métier |
| Strategy | ports `MusicProvider` / `Notifier` / `TrackPicker` injectés dans `WakeUpService` | changer de fournisseur, de canal ou de règle de tirage sans toucher au métier |
| Decorator | `CachedMusicProvider`, `RateLimitedMusicProvider` | ajouter le cache puis le quota d'appels à n'importe quel fournisseur, sans le modifier |
| Chain of Responsibility | `FallbackChainMusicProvider`, `ChannelRouter` | passer au suivant en cas de panne : jamais de silence |
| Facade | `WakeUpService` | un seul point d'entrée pour le déclencheur |
| IoC container | `container.Container` (`dependency-injector`) | déclare le graphe, instancie le concret, permet `override` |

Injection de dépendances : par constructeur, orchestrée par `dependency-injector`. Les classes
métier ne voient que des ports ; le conteneur est le seul à connaître les implémentations.

## Dépendances : licence, version, fraîcheur

Audit du 2026-10-08. Outils : uv 0.12.5 (MIT OR Apache-2.0), Python 3.12.12 (PSF-2.0).

Pour refaire l'audit :

```bash
uv tree --outdated                                        # arbre, versions installées, dernière stable
uvx pip-licenses --python .venv/bin/python --format=markdown  # licence de chaque package installé
```

Production (déclarées : `dependency-injector`, `fastapi`, `uvicorn` ; le reste est transitif) :

| Package | Rôle | Licence | Installée | Dernière stable (PyPI) | État |
|---|---|---|---|---|---|
| dependency-injector | conteneur IoC | BSD-3-Clause | 4.49.1 | 4.49.1 | à jour |
| fastapi | API HTTP | MIT | 0.142.4 | 0.142.4 | à jour |
| uvicorn | serveur ASGI | BSD-3-Clause | 0.54.0 | 0.54.0 | à jour |
| starlette | via fastapi | BSD-3-Clause | 1.7.0 | 1.7.0 | à jour |
| pydantic | via fastapi (validation) | MIT | 2.13.5 | 2.13.5 | à jour |
| pydantic-core | via pydantic | MIT | 2.46.5 | 2.49.0 | **en retard — justifié ci-dessous** |
| annotated-types | via pydantic | MIT | 0.8.0 | 0.8.0 | à jour |
| typing-inspection | via pydantic | MIT | 0.4.4 | 0.4.4 | à jour |
| annotated-doc | via fastapi | MIT | 0.0.5 | 0.0.5 | à jour |
| opentelemetry-api | via fastapi | Apache-2.0 | 1.45.1 | 1.45.1 | à jour |
| anyio | via starlette | MIT | 4.15.1 | 4.15.1 | à jour |
| idna | via anyio | BSD-3-Clause | 3.20 | 3.20 | à jour |
| click | via uvicorn | BSD-3-Clause | 8.5.0 | 8.5.0 | à jour |
| h11 | via uvicorn | MIT | 0.16.0 | 0.16.0 | à jour |
| typing-extensions | via dependency-injector (Python < 3.13) | PSF-2.0 | 4.16.0 | 4.16.0 | à jour |

Développement uniquement (non livrées en production) :

| Package | Rôle | Licence | Installée | Dernière stable (PyPI) | État |
|---|---|---|---|---|---|
| pytest | tests | MIT | 9.1.1 | 9.1.1 | à jour |
| pytest-cov | couverture | MIT | 7.1.0 | 7.1.0 | à jour |
| coverage | via pytest-cov | Apache-2.0 | 7.16.2 | 7.16.2 | à jour |
| pluggy | via pytest | MIT | 1.6.0 | 1.6.0 | à jour |
| iniconfig | via pytest | MIT | 2.3.1 | 2.3.1 | à jour |
| packaging | via pytest | Apache-2.0 OR BSD-2-Clause | 26.3 | 26.3 | à jour |
| Pygments | via pytest | BSD-2-Clause | 2.21.0 | 2.21.0 | à jour |
| httpx | client de test FastAPI | BSD-3-Clause | 0.28.1 | 0.28.1 | à jour |
| httpcore | via httpx | BSD-3-Clause | 1.0.9 | 1.0.9 | à jour |
| certifi | via httpx | **MPL-2.0 — justifié ci-dessous** | 2026.7.22 | 2026.7.22 | à jour |
| ruff | lint | MIT | 0.16.10 | 0.16.10 | à jour |
| colorama | via pytest, Windows uniquement (`sys_platform == 'win32'`) | BSD-3-Clause | 0.4.6 | 0.4.6 | à jour, non installé sous Linux |

Outillage de build et d'intégration continue (ni livré, ni installé dans l'environnement) :

| Composant | Rôle | Licence | Utilisée | Dernière stable | État |
|---|---|---|---|---|---|
| uv | gestion d'environnement, lock | MIT OR Apache-2.0 | 0.12.5 | 0.12.23 | en retard — justifié ci-dessous |
| uv_build | backend de build (`pyproject.toml`) | MIT OR Apache-2.0 | `>=0.12.5,<0.13.0` (résolu à la construction) | 0.12.23 | à jour : la dernière entre dans la plage |
| actions/checkout | CI GitHub | MIT | v7 | v7.0.1 | à jour |
| astral-sh/setup-uv | CI GitHub | MIT | v10.2.0 (pas de tag majeur flottant publié) | v10.2.0 | à jour |

Composants posant question :

- **pydantic-core 2.46.5 (dernière : 2.49.0)** — pydantic épingle sa version de `pydantic-core`
  à l'exact (`==`) ; on ne peut pas la monter seule. Elle suivra la prochaine release de
  pydantic. Pas d'avis de sécurité connu sur 2.46.x.
- **certifi, MPL-2.0** — copyleft faible, à l'échelle du fichier : il n'impose des obligations
  que si l'on modifie et redistribue les fichiers de certifi eux-mêmes, ce que je ne fais
  pas. De plus il n'est tiré que par `httpx`, dépendance de développement (client de test).
  Aucun impact sur le produit livré.
- **httpx 0.28 (dépendance de test)** — `starlette` 1.7 émet un `StarletteDeprecationWarning`
  à l'exécution des tests : `TestClient` abandonnera `httpx` au profit de `httpx2` (2.13.1,
  BSD-3-Clause). Sans impact sur le produit livré ni sur les tests aujourd'hui ; à migrer vers
  `httpx2` à la prochaine montée de version de `starlette`/`fastapi`, avant que l'avertissement
  ne devienne une erreur.
- **uv 0.12.5 (dernière : 0.12.23)** — outil local, pas une dépendance du produit ; la CI
  installe la dernière version via `setup-uv`. Le lock (`uv.lock`) est compatible, la CI le
  vérifie avec `uv sync --locked`.
- **dependency-injector** — extensions Cython compilées ; des wheels sont fournis pour
  Linux / macOS / Windows, pas de chaîne de compilation nécessaire.
- **opentelemetry-api** — tirée par fastapi ≥ 0.140 pour son module de télémétrie ; inactif
  tant qu'aucun SDK OpenTelemetry n'est installé. Apache-2.0, à jour.

Aucune licence copyleft forte (GPL/AGPL). Toutes compatibles avec un usage commercial.

Services externes (pas de SDK, appelés en HTTP via la stdlib) :

| Service | Clé | Contrainte | Prise en compte |
|---|---|---|---|
| iTunes Search API | aucune | ~20 req/min | cache 1 h par titre, puis quota 20 appels / 60 s |
| MusicBrainz WS/2 | aucune | `User-Agent` identifiable obligatoire, 1 req/s | en-tête `ReveilMusical/0.1 (contact@…)` ; cache 1 h, puis quota 1 appel / s |

## Tests

`uv run pytest` : 38 tests, 98 % de couverture, seuil d'échec à 95 % (`--cov-fail-under`).
Les seules lignes non couvertes sont l'appel réseau réel (`urllib`), le lancement d'uvicorn et
une branche de refus du mock SMS, volontairement hors tests unitaires.

Lint : `ruff` (règles pyflakes, pycodestyle, isort, pyupgrade, bugbear, bandit, blind-except).
CI : `.github/workflows/ci.yml` lance `uv sync --locked`, `ruff check` et `pytest` à chaque push.
