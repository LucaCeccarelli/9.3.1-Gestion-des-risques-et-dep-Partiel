"""Imprime le tableau Markdown licence / version installée / dernière stable de chaque package.

Usage : uv run python scripts/audit_deps.py
"""

import json
import urllib.request
from importlib.metadata import distributions


def licence(meta) -> str:
    expr = meta.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier", []) if c.startswith("License ::")]
    return ", ".join(classifiers) or (meta.get("License") or "?").splitlines()[0]


def latest(name: str) -> str:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=10) as r:
        return json.load(r)["info"]["version"]


print("| Package | Licence | Installée | Dernière stable (PyPI) | État |")
print("|---|---|---|---|---|")
for dist in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
    name = dist.metadata["Name"]
    if name == "reveil-musical":
        continue
    new = latest(name)
    state = "à jour" if new == dist.version else f"⚠ en retard"
    print(f"| {name} | {licence(dist.metadata)} | {dist.version} | {new} | {state} |")
