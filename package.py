#!/usr/bin/env python3
# package.py
"""
Conversion Python de package.json pour usage dans un environnement Streamlit.

Ce module contient :
- une représentation Python complète du contenu de package.json fourni,
- une petite application Streamlit prête à exécuter pour afficher et interagir avec ces dépendances,
- une option pour télécharger le module Python généré (le même contenu sous forme de fichier .py),
- utilitaires pour charger un package.json externe si vous préférez.

Usage Streamlit :
    streamlit run package.py

Le fichier est autonome : copiez-collez tel quel dans votre projet Streamlit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st

# -------------------------
# Données converties
# -------------------------
# Représentation Python complète du package.json fourni par l'utilisateur.
PACKAGE: Dict[str, Any] = {
    "dependencies": {
        "@11ty/eleventy": "^3.1.2",
        "@x-govuk/govuk-eleventy-plugin": "^9.0.1"
    }
}

# -------------------------
# Utilitaires
# -------------------------

def load_package_json(path: Path) -> Dict[str, Any]:
    """
    Charge un fichier package.json depuis le disque et retourne son contenu.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def package_to_python_module(package_dict: Dict[str, Any], module_name: str = "package_data") -> str:
    """
    Génère une chaîne de caractères contenant un module Python complet qui définit
    la variable PACKAGE_DATA reprenant le contenu du package.json.
    Cette chaîne peut être sauvegardée en .py et importée.
    """
    header = (
        "# Auto-generated Python module from package.json\n"
        "# Encoding: utf-8\n\n"
        "from __future__ import annotations\n\n"
        "import json\n\n"
        f"PACKAGE_DATA = "
    )
    body = json.dumps(package_dict, indent=2, ensure_ascii=False)
    footer = "\n\n# Fin du module\n"
    return header + body + footer

def pretty_dependencies(deps: Dict[str, str]) -> str:
    """
    Retourne une représentation lisible des dépendances (une ligne par dépendance).
    """
    lines = []
    for name, ver in deps.items():
        lines.append(f"{name} : {ver}")
    return "\n".join(lines)

# -------------------------
# Streamlit UI
# -------------------------

def streamlit_app(package_override: Optional[Dict[str, Any]] = None) -> None:
    st.set_page_config(page_title="package.json Viewer", layout="wide")
    st.title("Conversion package.json → package.py (Streamlit)")

    st.markdown(
        "Cette page affiche le contenu converti de `package.json` en **Python** et permet de "
        "télécharger le module Python généré prêt à être importé dans un projet."
    )

    # Choix de la source : utiliser l'objet embarqué PACKAGE ou charger un fichier
    st.sidebar.header("Source des données")
    use_embedded = st.sidebar.checkbox("Utiliser le package embarqué (fourni)", value=True)
    uploaded = None
    if not use_embedded:
        uploaded = st.sidebar.file_uploader("Téléversez un package.json", type=["json"])
    st.sidebar.markdown("---")
    st.sidebar.markdown("Vous pouvez aussi copier-coller un JSON dans la zone ci-dessous.")
    pasted = st.sidebar.text_area("Coller JSON (optionnel)", height=120)

    # Déterminer les données à afficher
    data = package_override or PACKAGE
    if not use_embedded:
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                st.sidebar.success("package.json chargé depuis l'upload.")
            except Exception as exc:
                st.sidebar.error(f"Erreur lors du chargement du JSON uploadé: {exc}")
                st.stop()
        elif pasted and pasted.strip():
            try:
                data = json.loads(pasted)
                st.sidebar.success("package.json chargé depuis le texte collé.")
            except Exception as exc:
                st.sidebar.error(f"Erreur lors du parsing du JSON collé: {exc}")
                st.stop()
        else:
            st.sidebar.warning("Aucune source fournie : utilisation du package embarqué par défaut.")
            data = PACKAGE

    # Affichage principal
    st.header("Contenu (JSON)")
    st.code(json.dumps(data, indent=2, ensure_ascii=False), language="json")

    # Afficher les dépendances si présentes
    deps = data.get("dependencies") or {}
    dev_deps = data.get("devDependencies") or {}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dépendances")
        if deps:
            st.write(f"{len(deps)} dépendance(s) trouvée(s).")
            st.text(pretty_dependencies(deps))
        else:
            st.info("Aucune dépendance listée dans `dependencies`.")

    with col2:
        st.subheader("DevDependencies")
        if dev_deps:
            st.write(f"{len(dev_deps)} dépendance(s) de développement trouvée(s).")
            st.text(pretty_dependencies(dev_deps))
        else:
            st.info("Aucune dépendance listée dans `devDependencies`.")

    st.markdown("---")
    st.subheader("Générer le module Python `package_data.py`")

    module_name = st.text_input("Nom du module Python (sans extension)", value="package_data")
    generated_code = package_to_python_module(data, module_name=module_name)

    st.markdown("Aperçu du module Python généré :")
    st.code(generated_code, language="python")

    st.markdown("Télécharger le module Python généré")
    st.download_button(
        label="Télécharger package_data.py",
        data=generated_code.encode("utf-8"),
        file_name=f"{module_name}.py",
        mime="text/x-python"
    )

    st.markdown("---")
    st.subheader("Conseils d'intégration")
    st.markdown(
        "- Le module généré définit une variable `PACKAGE_DATA` contenant la structure du `package.json`.\n"
        "- Dans un projet Streamlit, vous pouvez importer ce module et l'utiliser pour afficher ou automatiser des tâches liées à la documentation statique (ex: Eleventy) ou pour afficher les dépendances.\n"
        "- Ce fichier **ne** traduit pas automatiquement les dépendances Node en équivalents Python. Il sert uniquement de représentation et d'outil d'exploration."
    )

    st.caption("Fichier converti automatiquement depuis le package.json fourni.")

# -------------------------
# Entrypoint CLI (optionnel)
# -------------------------

def main_cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="package.py — viewer / convertisseur simple pour package.json")
    parser.add_argument("--file", "-f", help="Chemin vers package.json (optionnel). Si absent, utilise le package embarqué.", default=None)
    parser.add_argument("--write", "-w", help="Écrire le module Python généré vers ce fichier (ex: package_data.py)", default=None)
    args = parser.parse_args()

    data = PACKAGE
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"Fichier introuvable: {p}")
            return 2
        data = load_package_json(p)

    module_code = package_to_python_module(data, module_name="package_data")
    if args.write:
        out = Path(args.write)
        out.write_text(module_code, encoding="utf-8")
        print(f"Wrote Python module to {out}")
    else:
        print(module_code)
    return 0

# -------------------------
# Exécution
# -------------------------

if __name__ == "__main__":
    # Si lancé via `streamlit run package.py`, Streamlit importera ce module et exécutera le code.
    # Pour permettre l'exécution directe en CLI : détecter si Streamlit est en cours d'exécution.
    import sys
    # Si l'argument 'streamlit' est présent ou si Streamlit a démarré, lancer l'app Streamlit.
    if any("streamlit" in arg for arg in sys.argv) or "STREAMLIT_RUN" in os.environ:
        streamlit_app()
    else:
        raise SystemExit(main_cli())
