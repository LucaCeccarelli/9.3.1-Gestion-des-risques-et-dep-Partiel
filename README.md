# Réveil musical

Service qui réveille un utilisateur avec un morceau choisi selon le jour de la semaine et la
météo, puis le prévient sur son canal préféré (email, SMS ou push — simulés).

## Lancer

```bash
uv sync                                   # crée l'environnement (Python ≥ 3.12)
uv run reveil-musical alice LUNDI PLUIE   # <user_id> <jour> <météo>
uv run pytest                             # tests + couverture
```

Jours : `LUNDI … DIMANCHE`. Météo : `SOLEIL / PLUIE / NEIGE / NUAGEUX`.
Utilisateurs de démo : `alice` (email), `bob` (SMS), `carol` (push).

L'ordonnancement n'est pas codé : la commande est l'appel exécuté « à la bonne heure ».

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
└── cli.py               point d'entrée
```

Traduction des quatre exigences :

| Besoin métier | Réponse technique |
|---|---|
| Changer de fournisseur musical | `MusicProvider` est un port ; iTunes, MusicBrainz et le fallback local sont interchangeables. `trackViewUrl` et `artist-credit` ne sortent pas de leur adaptateur : le métier ne voit que `Track(title, artist)`. |
| Ajouter un canal (WhatsApp, vocal…) | Un adaptateur `Notifier` + une entrée dans le `ChannelRouter` du conteneur. Rien d'autre ne change. |
| Vérification des dépendances | Tableau ci-dessous. Une seule dépendance runtime (`dependency-injector`, BSD) ; HTTP via `urllib` (stdlib). |
| Jamais de silence | Chaîne de fournisseurs avec fallback local en fin de chaîne ; routeur de canaux qui bascule sur un autre canal si le préféré est en panne. Une panne est journalisée (`WARNING`), jamais bloquante. |

Isolation / DI : `WakeUpService` ne reçoit que des ports via son constructeur. Aucune classe
métier n'instancie d'implémentation concrète ; l'assemblage est déclaré dans `container.py`
(`Container`, un `DeclarativeContainer` de `dependency-injector`). Chaque fournisseur, canal
ou client HTTP est un `provider` remplaçable par `container.<nom>.override(...)` — c'est ce que
font les tests, et ce que ferait un changement de fournisseur en production.

Rate-limit iTunes (~20 req/min) : `CachedMusicProvider` mémorise chaque requête réussie 1 h.
Un réveil par utilisateur et par jour, avec des morceaux fixes par météo, tient donc largement
dans la limite.

## Design patterns

| Pattern | Où | Pourquoi |
|---|---|---|
| Adapter | `notification/adapters.py`, `music/itunes.py`, `music/musicbrainz.py` | ramener des interfaces hétérogènes (mocks, JSON des APIs) vers les ports métier |
| Strategy | ports `MusicProvider` / `Notifier` injectés dans `WakeUpService` | changer de fournisseur ou de canal sans toucher au métier |
| Decorator | `CachedMusicProvider` | ajouter le cache (rate-limit) à n'importe quel fournisseur |
| Chain of Responsibility | `FallbackChainMusicProvider`, `ChannelRouter` | passer au suivant en cas de panne : jamais de silence |
| Facade | `WakeUpService` | un seul point d'entrée pour le déclencheur |
| IoC container | `container.Container` (`dependency-injector`) | déclare le graphe, instancie le concret, permet `override` |

Injection de dépendances : par constructeur, orchestrée par `dependency-injector`. Les classes
métier ne voient que des ports ; le conteneur est le seul à connaître les implémentations.

## Dépendances : licence, version, fraîcheur

Audit du 2026-10-08.

Production :

| Package | Rôle | Licence | Installée | Dernière stable (PyPI) | Remarque |
|---|---|---|---|---|---|
| dependency-injector | conteneur IoC | BSD-3-Clause | 4.49.1 | 4.49.1 | à jour ; extensions Cython compilées, wheels fournis pour Linux/macOS/Windows |
| typing-extensions | (via dependency-injector, Python < 3.13) | PSF-2.0 | 4.16.0 | 4.16.0 | à jour ; disparaît en passant à Python 3.13 |

Développement :

| Package | Rôle | Licence | Installée | Dernière stable (PyPI) | Remarque |
|---|---|---|---|---|---|
| pytest | tests | MIT | 9.1.1 | 9.1.1 | à jour |
| pytest-cov | couverture | MIT | 7.1.0 | 7.1.0 | à jour |
| coverage | (via pytest-cov) | Apache-2.0 | 7.16.2 | 7.16.2 | à jour |
| pluggy | (via pytest) | MIT | 1.6.0 | 1.6.0 | à jour |
| iniconfig | (via pytest) | MIT | 2.3.1 | 2.3.1 | à jour |
| packaging | (via pytest) | Apache-2.0 OR BSD-2-Clause | 26.3 | 26.3 | à jour |
| Pygments | (via pytest) | BSD-2-Clause | 2.21.0 | 2.21.0 | à jour |

Outils : uv 0.12.5 (MIT OR Apache-2.0), Python 3.12.12 (PSF-2.0).

Aucun composant copyleft, aucune version ancienne. Toutes les licences sont permissives et
compatibles avec un usage commercial.

Services externes (pas de SDK, appelés en HTTP via la stdlib) :

| Service | Clé | Contrainte | Prise en compte |
|---|---|---|---|
| iTunes Search API | aucune | ~20 req/min | cache 1 h par requête |
| MusicBrainz WS/2 | aucune | `User-Agent` identifiable obligatoire, 1 req/s | en-tête `ReveilMusical/0.1 (contact@…)` ; second de la chaîne, donc rarement sollicité |

Pour refaire l'audit : `uv tree` puis comparer avec `https://pypi.org/pypi/<package>/json`.

## Tests

`uv run pytest` : 29 tests, 98 % de couverture. Les seules lignes non couvertes sont l'appel
réseau réel (`urllib`) et une branche de refus du mock SMS, volontairement hors tests unitaires.
