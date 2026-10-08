# Réveil musical

Service qui réveille un utilisateur avec un morceau choisi selon le jour de la semaine et la
météo, puis le prévient sur son canal préféré (email, SMS ou push — simulés).

## Lancer

```bash
uv sync                 # crée l'environnement (Python ≥ 3.12)
uv run reveil-musical   # démarre l'API sur http://127.0.0.1:8000 (doc interactive : /docs)
uv run pytest           # tests + couverture
```

Le point d'entrée est `POST /wake-up`, l'appel que l'ordonnanceur (externe, non codé) exécute à
l'heure du réveil :

```bash
curl -X POST localhost:8000/wake-up -H 'content-type: application/json' \
     -d '{"user_id": "alice", "day": "LUNDI", "weather": "PLUIE"}'
```

```json
{"user_id": "alice", "channel": "EMAIL", "day": "LUNDI", "weather": "PLUIE",
 "track_title": "Riders on the Storm", "track_artist": "The Doors",
 "text": "Bonjour, c'est lundi et il fait pluie : réveil avec « Riders on the Storm » de The Doors."}
```

Jours : `LUNDI … DIMANCHE`. Météo : `SOLEIL / PLUIE / NEIGE / NUAGEUX` (fournis en entrée,
aucun appel météo). Choix du morceau : l'utilisateur liste plusieurs morceaux par jour et par météo ;
le réveil tire au sort parmi la réunion des deux listes (un lundi de neige, les morceaux du
lundi et ceux de la neige sont tous candidats). Si aucune des deux listes ne couvre le cas,
tirage parmi les morceaux de secours. Réponses : `404` utilisateur inconnu, `422` entrée invalide, `503` si tous
les canaux sont en panne. Utilisateurs de démo : `alice` (email), `bob` (SMS), `carol` (push) — voir `users.py`.

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
│   ├── local.py         liste codée en dur : dernier recours, ne tombe jamais
│   └── resilient.py     CachedMusicProvider (rate-limit) + FallbackChainMusicProvider
├── notification/
│   ├── mocks.py         EmailMock / SmsMock / PushMock, interfaces volontairement différentes
│   ├── adapters.py      ramènent chaque mock vers le port Notifier
│   └── router.py        ChannelRouter : canal préféré, sinon bascule sur un autre (mode dégradé)
├── container.py         conteneur DI (dependency-injector) : seul endroit où le concret est assemblé
└── api.py               point d'entrée HTTP (FastAPI) : POST /wake-up
```

Traduction des quatre exigences :

| Besoin métier | Réponse technique |
|---|---|
| Changer de fournisseur musical | `MusicProvider` est un port ; iTunes, MusicBrainz et le fallback local sont interchangeables. `trackViewUrl` et `artist-credit` ne sortent pas de leur adaptateur : le métier ne voit que `Track(title, artist)`. |
| Ajouter un canal (WhatsApp, vocal…) | Un adaptateur `Notifier` + une entrée dans le `ChannelRouter` du conteneur. Rien d'autre ne change. |
| Vérification des dépendances | Tableau ci-dessous, régénérable avec `uv tree --outdated` et `uvx pip-licenses`. HTTP sortant via `urllib` (stdlib), pas de SDK tiers. |
| Jamais de silence | Chaîne de fournisseurs avec fallback local en fin de chaîne ; routeur de canaux qui bascule sur un autre canal si le préféré est en panne. Une panne est journalisée (`WARNING`), jamais bloquante. |

Isolation / DI : `WakeUpService` ne reçoit que des ports via son constructeur. Aucune classe
métier n'instancie d'implémentation concrète ; l'assemblage est déclaré dans `container.py`
(`Container`, un `DeclarativeContainer` de `dependency-injector`). Chaque fournisseur, canal
ou client HTTP est un `provider` remplaçable par `container.<nom>.override(...)` — c'est ce que
font les tests, et ce que ferait un changement de fournisseur en production. L'API reçoit le
service par `Depends`, elle ne connaît pas non plus les implémentations.

Rate-limit iTunes (~20 req/min) : `CachedMusicProvider` mémorise chaque requête réussie 1 h.
Un réveil par utilisateur et par jour, avec des morceaux fixes par météo, tient donc largement
dans la limite.

## Design patterns

| Pattern | Où | Pourquoi |
|---|---|---|
| Adapter | `notification/adapters.py`, `music/itunes.py`, `music/musicbrainz.py` | ramener des interfaces hétérogènes (mocks, JSON des APIs) vers les ports métier |
| Strategy | ports `MusicProvider` / `Notifier` / `TrackPicker` injectés dans `WakeUpService` | changer de fournisseur, de canal ou de règle de tirage sans toucher au métier |
| Decorator | `CachedMusicProvider` | ajouter le cache (rate-limit) à n'importe quel fournisseur |
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

Composants posant question :

- **pydantic-core 2.46.5 (dernière : 2.49.0)** — pydantic épingle sa version de `pydantic-core`
  à l'exact (`==`) ; on ne peut pas la monter seule. Elle suivra la prochaine release de
  pydantic. Pas d'avis de sécurité connu sur 2.46.x.
- **certifi, MPL-2.0** — copyleft faible, à l'échelle du fichier : il n'impose des obligations
  que si l'on modifie et redistribue les fichiers de certifi eux-mêmes, ce que nous ne faisons
  pas. De plus il n'est tiré que par `httpx`, dépendance de développement (client de test).
  Aucun impact sur le produit livré.
- **dependency-injector** — extensions Cython compilées ; des wheels sont fournis pour
  Linux / macOS / Windows, pas de chaîne de compilation nécessaire.
- **opentelemetry-api** — tirée par fastapi ≥ 0.140 pour son module de télémétrie ; inactif
  tant qu'aucun SDK OpenTelemetry n'est installé. Apache-2.0, à jour.

Aucune licence copyleft forte (GPL/AGPL). Toutes compatibles avec un usage commercial.

Services externes (pas de SDK, appelés en HTTP via la stdlib) :

| Service | Clé | Contrainte | Prise en compte |
|---|---|---|---|
| iTunes Search API | aucune | ~20 req/min | cache 1 h par requête |
| MusicBrainz WS/2 | aucune | `User-Agent` identifiable obligatoire, 1 req/s | en-tête `ReveilMusical/0.1 (contact@…)` ; second de la chaîne, donc rarement sollicité |

## Tests

`uv run pytest` : 34 tests, 98 % de couverture. Les seules lignes non couvertes sont l'appel
réseau réel (`urllib`), le lancement d'uvicorn et une branche de refus du mock SMS,
volontairement hors tests unitaires.
