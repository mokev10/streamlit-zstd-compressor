#!/usr/bin/env python3
# app_test_stream_zip.py
"""
Streamlit app to load, view and run a Python test file (e.g., test_stream_zip.py).

Features:
- Upload or paste test file content.
- Save the test file to a temporary working directory.
- Run pytest on the saved file (all tests or filtered with -k).
- Stream pytest output to the UI and show final exit code.
- Download the saved test file.

Usage:
    streamlit run app_test_stream_zip.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

# -------------------------
# Helpers
# -------------------------

def ensure_workdir(base: Optional[Path] = None) -> Path:
    """
    Create and return a persistent temporary working directory for this Streamlit session.
    """
    if "workdir" not in st.session_state:
        if base:
            workdir = Path(base).expanduser().resolve()
            workdir.mkdir(parents=True, exist_ok=True)
        else:
            workdir = Path(tempfile.mkdtemp(prefix="streamlit-tests-"))
        st.session_state["workdir"] = str(workdir)
    return Path(st.session_state["workdir"])


def save_test_file(content: str, filename: str = "test_stream_zip.py", workdir: Optional[Path] = None) -> Path:
    """
    Save the provided content to filename inside workdir and return the path.
    """
    wd = ensure_workdir(workdir)
    path = wd / filename
    path.write_text(content, encoding="utf-8")
    return path


def run_pytest_on_file(file_path: Path, pytest_args: Optional[list[str]] = None) -> Tuple[int, str]:
    """
    Run pytest on the given file_path with optional pytest_args.
    Returns (exit_code, combined_output).
    """
    cmd = [sys.executable, "-m", "pytest", "-q", str(file_path)]
    if pytest_args:
        cmd.extend(pytest_args)
    # Use subprocess to capture output
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    output_lines = []
    for line in proc.stdout:
        output_lines.append(line)
    proc.wait()
    return proc.returncode, "".join(output_lines)


def stream_subprocess_output(cmd: list[str], cwd: Optional[Path] = None):
    """
    Generator that yields lines from subprocess stdout in real time.
    """
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            yield line
    finally:
        proc.wait()
        yield f"\n[PROCESS EXIT CODE] {proc.returncode}\n"


# -------------------------
# Streamlit UI
# -------------------------

st.set_page_config(page_title="Test Runner — test_stream_zip", layout="wide")
st.title("Streamlit Test Runner — test_stream_zip.py")

st.markdown(
    """
**But** : charger, visualiser et exécuter le fichier de tests `test_stream_zip.py` dans un environnement Streamlit.
- Uploadez le fichier ou collez son contenu.
- Sauvegardez-le dans un répertoire de travail.
- Lancez `pytest` (tous les tests ou filtrés).
"""
)

# Sidebar: options
st.sidebar.header("Options")
workdir_input = st.sidebar.text_input("Répertoire de travail (laisser vide pour tempdir)", value="")
filename_input = st.sidebar.text_input("Nom du fichier de tests", value="test_stream_zip.py")
run_in_subprocess = st.sidebar.checkbox("Afficher la sortie en streaming (recommandé)", value=True)
pytest_k = st.sidebar.text_input("Filtre pytest -k (optionnel)", value="")
pytest_extra = st.sidebar.text_input("Arguments pytest supplémentaires (séparés par espace)", value="")

# Main: upload or paste
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Charger le fichier de tests")
    uploaded = st.file_uploader("Téléversez test_stream_zip.py (ou un autre fichier de tests)", type=["py"])
    pasted = st.text_area("Ou collez le contenu du fichier ici", height=300)

    # Determine content
    test_content = None
    if uploaded is not None:
        try:
            raw = uploaded.read()
            # uploaded.read() returns bytes
            test_content = raw.decode("utf-8")
            st.success(f"Fichier uploadé : {uploaded.name}")
        except Exception as exc:
            st.error(f"Erreur lors de la lecture du fichier uploadé : {exc}")
    elif pasted and pasted.strip():
        test_content = pasted
        st.info("Contenu collé détecté.")
    else:
        st.info("Aucun fichier fourni. Vous pouvez uploader ou coller le contenu du fichier de tests.")

    # Save button
    if test_content is not None:
        if st.button("Sauvegarder le fichier de tests dans le répertoire de travail"):
            wd = Path(workdir_input).expanduser().resolve() if workdir_input.strip() else None
            saved_path = save_test_file(test_content, filename=filename_input or "test_stream_zip.py", workdir=wd)
            st.success(f"Fichier sauvegardé : {saved_path}")
            st.session_state["last_saved_test"] = str(saved_path)

    # Show file content
    if test_content is not None:
        st.subheader("Aperçu du fichier de tests")
        st.code(test_content, language="python")

with col_right:
    st.subheader("Exécuter les tests")
    st.markdown(
        """
        **Étapes** :
        1. Sauvegardez d'abord le fichier de tests (bouton ci‑dessus).
        2. Choisissez un filtre `-k` si vous voulez exécuter un sous-ensemble.
        3. Cliquez sur **Lancer pytest**.
        """
    )

    last_saved = st.session_state.get("last_saved_test")
    if not last_saved:
        st.warning("Aucun fichier de tests sauvegardé dans cette session. Sauvegardez le fichier avant d'exécuter.")
    else:
        st.write(f"Fichier de tests sauvegardé : **{last_saved}**")
        # Build pytest args
        extra_args = []
        if pytest_k and pytest_k.strip():
            extra_args.extend(["-k", pytest_k.strip()])
        if pytest_extra and pytest_extra.strip():
            extra_args.extend(pytest_extra.strip().split())

        if st.button("Lancer pytest"):
            saved_path = Path(last_saved)
            if not saved_path.exists():
                st.error(f"Fichier introuvable : {saved_path}")
            else:
                st.info("Exécution de pytest en cours...")
                log_placeholder = st.empty()
                if run_in_subprocess:
                    # Stream output line by line
                    cmd = [sys.executable, "-m", "pytest", "-q", str(saved_path)]
                    if extra_args:
                        cmd.extend(extra_args)
                    lines = []
                    for line in stream_subprocess_output(cmd, cwd=saved_path.parent):
                        # Append line to lines and update UI
                        lines.append(line)
                        log_placeholder.code("".join(lines), language="text")
                    # After completion, show final status
                    st.success("Exécution terminée.")
                else:
                    # Run and capture
                    exit_code, output = run_pytest_on_file(saved_path, pytest_args=extra_args)
                    st.code(output, language="text")
                    if exit_code == 0:
                        st.success("pytest a réussi (exit code 0).")
                    else:
                        st.error(f"pytest a échoué (exit code {exit_code}).")

        if st.button("Afficher le répertoire de travail"):
            wd = saved_path.parent
            st.write(f"Workdir: {wd}")
            files = list(wd.iterdir())
            st.write([str(p.name) for p in files])

        if st.button("Télécharger le fichier de tests sauvegardé"):
            try:
                with open(last_saved, "rb") as f:
                    data = f.read()
                st.download_button("Télécharger", data=data, file_name=Path(last_saved).name, mime="text/x-python")
            except Exception as exc:
                st.error(f"Impossible de lire le fichier : {exc}")

# Bottom: environment checks and tips
st.markdown("---")
st.subheader("Vérifications et conseils")
st.markdown(
    """
- **Dépendances** : assurez-vous que `pytest` et les bibliothèques importées par vos tests (ex: `pyzipper`, `stream_unzip`, `stream_zip`) sont installées dans l'environnement Python utilisé par Streamlit.
- **Exécution longue** : certains tests peuvent être très longs ou consommer beaucoup de mémoire (tests de gros fichiers). Préférez exécuter ces tests dans un environnement dédié si nécessaire.
- **Permissions** : si vos tests appellent des outils externes (7z, unzip, bsdcpio), assurez-vous qu'ils sont installés et accessibles dans le PATH.
"""
)

# Footer: quick environment info
st.markdown("---")
st.caption(f"Python executable: {sys.executable}  —  Current working dir: {Path.cwd()}")

