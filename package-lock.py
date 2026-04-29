#!/usr/bin/env python3
# package_lock.py
"""
Conversion Python de package-lock.json pour usage dans un environnement Streamlit.

Ce module fournit :
- Fonctions pour charger et interroger un fichier package-lock.json.
- Une petite application Streamlit intégrée pour afficher et rechercher les dépendances.
- Utilitaires pour exporter un sous-ensemble de la structure en JSON ou en affichage lisible.

Extrait du fichier fourni : "name": "stream-zip", "lockfileVersion": 3.
Ces deux champs sont lus et affichés automatiquement si le fichier package-lock.json est présent.

Usage (ligne de commande) :
    python package_lock.py --file package-lock.json --show

Usage Streamlit :
    streamlit run package_lock.py

Le module fonctionne de façon autonome : s'il trouve un fichier package-lock.json dans le répertoire courant,
il le charge automatiquement. Vous pouvez aussi spécifier un chemin via l'argument --file.
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st
import textwrap

# -------------------------
# Chargement et parsing
# -------------------------

def load_package_lock(path: Path) -> Dict[str, Any]:
    """
    Charge et retourne le contenu JSON d'un package-lock.json en tant que dictionnaire Python.
    """
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def get_top_level_info(lock: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """
    Retourne (name, lockfileVersion) si présents.
    """
    name = lock.get("name")
    lockfile_version = lock.get("lockfileVersion")
    return name, lockfile_version

def list_top_level_dependencies(lock: Dict[str, Any]) -> Dict[str, str]:
    """
    Retourne le mapping des dépendances listées au niveau racine (packages[""].dependencies).
    """
    packages = lock.get("packages", {})
    root = packages.get("", {})
    deps = root.get("dependencies", {}) or {}
    # Normaliser en str->str (nom->versionRange)
    return {k: str(v) for k, v in deps.items()}

def list_all_packages(lock: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Retourne une liste (package_path, package_info) pour tous les packages présents.
    package_path est la clé dans packages (ex: "node_modules/xxx").
    """
    packages = lock.get("packages", {})
    return sorted(list(packages.items()), key=lambda kv: kv[0])

def find_package(lock: Dict[str, Any], package_name: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Recherche les packages dont la clé contient package_name (insensible à la casse).
    Retourne une liste de tuples (key, info).
    """
    package_name_lower = package_name.lower()
    results = []
    for key, info in (lock.get("packages") or {}).items():
        if package_name_lower in key.lower() or (info.get("name") and package_name_lower in str(info.get("name")).lower()):
            results.append((key, info))
    return results

def summarize_package_info(key: str, info: Dict[str, Any]) -> str:
    """
    Retourne une chaîne lisible résumant les informations d'un package.
    """
    version = info.get("version", info.get("resolved", ""))
    license_ = info.get("license", "")
    deps = info.get("dependencies") or {}
    dep_count = len(deps)
    return f"{key} — version: {version} — license: {license_} — dependencies: {dep_count}"

# -------------------------
# Export / utilitaires
# -------------------------

def export_subset(lock: Dict[str, Any], out_path: Path, package_keys: Optional[List[str]] = None) -> None:
    """
    Exporte un sous-ensemble de la structure package-lock en JSON.
    Si package_keys est None, exporte l'objet 'packages' complet.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if package_keys is None:
        to_export = lock.get("packages", {})
    else:
        pkgs = lock.get("packages", {})
        to_export = {k: pkgs[k] for k in package_keys if k in pkgs}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"packages": to_export}, f, indent=2, ensure_ascii=False)
    print(f"Exporté {len(to_export)} entrées vers {out_path}")

# -------------------------
# Streamlit UI
# -------------------------

def streamlit_app(default_lock_path: Optional[Path] = None) -> None:
    st.set_page_config(page_title="package-lock Viewer", layout="wide")
    st.title("package-lock Viewer (Streamlit)")

    st.markdown(
        textwrap.dedent(
            """
            **Fonctions :**
            - Charger un `package-lock.json`.
            - Explorer les dépendances top-level et l'arbre `packages`.
            - Rechercher un package par nom.
            - Exporter un sous-ensemble en JSON.
            """
        )
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Chargement du fichier package-lock.json")
        uploaded = st.file_uploader("Téléversez un package-lock.json (ou laissez vide pour utiliser le fichier local)", type=["json"])
        if uploaded is not None:
            try:
                lock_data = json.load(uploaded)
                st.success("Fichier chargé depuis l'upload.")
            except Exception as exc:
                st.error(f"Erreur lors du chargement du JSON : {exc}")
                return
        else:
            # utiliser le chemin par défaut si fourni, sinon chercher package-lock.json dans le cwd
            path = default_lock_path or Path.cwd() / "package-lock.json"
            if path.exists():
                try:
                    lock_data = load_package_lock(path)
                    st.info(f"Fichier chargé depuis : {path}")
                except Exception as exc:
                    st.error(f"Impossible de charger {path}: {exc}")
                    return
            else:
                st.warning("Aucun fichier fourni et aucun package-lock.json trouvé dans le répertoire courant.")
                st.stop()

        # Afficher info top-level
        name, lockfile_version = get_top_level_info(lock_data)
        st.subheader("Informations générales")
        st.write(f"**name**: {name}")
        st.write(f"**lockfileVersion**: {lockfile_version}")

        st.subheader("Dépendances top-level (packages[''].dependencies)")
        top_deps = list_top_level_dependencies(lock_data)
        if top_deps:
            st.dataframe(
                [{"package": k, "versionRange": v} for k, v in top_deps.items()],
                use_container_width=True
            )
        else:
            st.write("Aucune dépendance top-level trouvée dans packages[''].dependencies.")

        st.subheader("Explorer tous les packages")
        packages = list_all_packages(lock_data)
        # Afficher un échantillon et permettre recherche
        sample_count = min(200, len(packages))
        st.write(f"{len(packages)} packages trouvés. Affichage des {sample_count} premiers (triés par clé).")
        for key, info in packages[:sample_count]:
            st.markdown(f"- **{key}** — version: {info.get('version', info.get('resolved', ''))}")

    with col2:
        st.header("Recherche et export")
        query = st.text_input("Rechercher un package (nom ou chemin)", value="")
        if st.button("Rechercher"):
            if not query:
                st.warning("Entrez un terme de recherche.")
            else:
                results = find_package(lock_data, query)
                st.write(f"{len(results)} résultat(s) pour '{query}':")
                for key, info in results:
                    st.markdown(f"**{key}**")
                    st.code(json.dumps(info, indent=2, ensure_ascii=False), language="json")

        st.markdown("---")
        st.subheader("Exporter un sous-ensemble")
        export_key = st.text_area("Listez les clés de package à exporter (une par ligne), ou laissez vide pour tout exporter", height=120)
        out_name = st.text_input("Nom du fichier de sortie (ex: subset-package-lock.json)", value="subset-package-lock.json")
        if st.button("Exporter"):
            keys = [k.strip() for k in export_key.splitlines() if k.strip()]
            out_path = Path.cwd() / out_name
            try:
                export_subset(lock_data, out_path, package_keys=keys if keys else None)
                st.success(f"Export réussi vers {out_path}")
                with out_path.open("r", encoding="utf-8") as f:
                    st.download_button("Télécharger le JSON exporté", data=f.read(), file_name=out_name, mime="application/json")
            except Exception as exc:
                st.error(f"Erreur lors de l'export: {exc}")

    st.markdown("---")
    st.caption("Ce viewer convertit et expose le contenu d'un package-lock.json pour exploration dans Streamlit.")

# -------------------------
# CLI / Entrypoint
# -------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="package-lock.py — viewer et utilitaires pour package-lock.json")
    p.add_argument("--file", "-f", help="Chemin vers package-lock.json (défaut: ./package-lock.json)", default="package-lock.json")
    p.add_argument("--show", action="store_true", help="Afficher un résumé en console")
    p.add_argument("--export", metavar="OUT", help="Exporter packages (tout) vers OUT (JSON)")
    p.add_argument("--streamlit", action="store_true", help="Lancer l'interface Streamlit (utiliser 'streamlit run package_lock.py' de préférence)")
    return p.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    path = Path(args.file)

    if args.streamlit:
        # Si lancé via `python package_lock.py --streamlit`, démarrer l'app Streamlit
        # Note: l'usage recommandé est `streamlit run package_lock.py`
        streamlit_app(default_lock_path=path if path.exists() else None)
        return 0

    if not path.exists():
        print(f"Fichier introuvable: {path}")
        return 2

    lock = load_package_lock(path)

    if args.show:
        name, lockfile_version = get_top_level_info(lock)
        print(f"name: {name}")
        print(f"lockfileVersion: {lockfile_version}")
        top_deps = list_top_level_dependencies(lock)
        print(f"\nTop-level dependencies ({len(top_deps)}):")
        for k, v in top_deps.items():
            print(f"  - {k}: {v}")

        packages = list_all_packages(lock)
        print(f"\nTotal packages entries: {len(packages)}")
        # print first 20
        for key, info in packages[:20]:
            print("  ", summarize_package_info(key, info))

    if args.export:
        out_path = Path(args.export)
        export_subset(lock, out_path, package_keys=None)
    return 0

if __name__ == "__main__":
    # Si exécuté directement via `streamlit run package_lock.py`, Streamlit exécutera le module et
    # appellera la fonction streamlit_app automatiquement. Pour permettre cela, on détecte si
    # Streamlit est en train d'exécuter ce fichier (variable d'environnement STREAMLIT_SERVER_RUNNING n'est pas fiable),
    # donc on propose deux modes : CLI et Streamlit.
    import sys
    # Si Streamlit a injecté des arguments spéciaux, ou si l'utilisateur a demandé --streamlit, lancer l'app
    if any(arg.startswith("streamlit") for arg in sys.argv) or "--streamlit" in sys.argv:
        # Lancer l'app Streamlit
        streamlit_app()
    else:
        raise SystemExit(main(sys.argv[1:]))
