#!/usr/bin/env python3
# app.py
import streamlit as st
import zstandard as zstd
import os
import tempfile

from pathlib import Path
from urllib.request import urlopen, Request
import hashlib
import tarfile
import shutil
import subprocess
import sys
import argparse
import threading
import time
from typing import Optional

# Configuration de la page
st.set_page_config(
    page_title="AI Compressor Files",
    page_icon="https://img.icons8.com/external-flat-juicy-fish/60/external-zip-data-organisation-flat-flat-juicy-fish.png",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🗜️ Ultra-fast file compressor | AI-powered booster")

# ---------------------------
# Utilitaires pour logging UI
# ---------------------------

def append_log(key: str, message: str) -> None:
    """Ajoute une ligne au log stocké dans st.session_state[key]."""
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key].append(message)

def get_log_text(key: str) -> str:
    """Retourne le log sous forme de texte."""
    return "\n".join(st.session_state.get(key, []))

# ---------------------------
# Fonctions d'installation
# ---------------------------

DEFAULT_VERSION = "3.5.3"
DEFAULT_FILENAME_TEMPLATE = "AI Compressor Files-{version}.tar.gz"
DEFAULT_URL_TEMPLATE = "https://www.libarchive.org/downloads/{filename}"
DEFAULT_CHECKSUM = "72788e5f58d16febddfa262a5215e05fc9c79f2670f641ac039e6df44330ef51"

def download_file(url: str, dest: Path, log_key: str) -> None:
    append_log(log_key, f"Téléchargement: {url}")
    req = Request(url, headers={"User-Agent": "python-urllib/3"})
    with urlopen(req) as resp, open(dest, "wb") as out:
        total = resp.getheader("Content-Length")
        if total:
            total = int(total)
        downloaded = 0
        chunk_size = 8192
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 // total
                append_log(log_key, f"  téléchargé {downloaded}/{total} bytes ({pct}%)")
    append_log(log_key, f"Téléchargement terminé: {dest}")

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_tar_gz(archive_path: Path, dest_dir: Path, log_key: str) -> Path:
    append_log(log_key, f"Extraction de {archive_path} dans {dest_dir}")
    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        tar.extractall(path=dest_dir)
        top_dirs = {m.name.split("/")[0] for m in members if m.name and "/" in m.name}
        if not top_dirs:
            return dest_dir / archive_path.stem
        top_dir = sorted(top_dirs)[0]
        extracted = dest_dir / top_dir
        append_log(log_key, f"Répertoire extrait: {extracted}")
        return extracted

def run_command(cmd: list, cwd: Optional[Path], log_key: str, check: bool = True) -> int:
    append_log(log_key, f"Exécution: {' '.join(cmd)} (cwd={cwd})")
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        append_log(log_key, line.rstrip())
    proc.wait()
    append_log(log_key, f"Commande terminée avec code {proc.returncode}")
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return proc.returncode

def build_from_source(source_dir: Path, log_key: str, do_install: bool = False) -> None:
    configure_path = source_dir / "configure"
    if not configure_path.exists():
        raise FileNotFoundError(f"configure introuvable dans {source_dir}")
    # Rendre exécutable
    mode = configure_path.stat().st_mode
    configure_path.chmod(mode | 0o111)
    run_command(["./configure"], cwd=source_dir, log_key=log_key)
    run_command(["make"], cwd=source_dir, log_key=log_key)
    if do_install:
        # make install peut nécessiter sudo; on l'exécute tel quel et laisse l'utilisateur gérer les privilèges
        run_command(["make", "install"], cwd=source_dir, log_key=log_key)

def install_libarchive(
    version: str = DEFAULT_VERSION,
    url: Optional[str] = None,
    filename: Optional[str] = None,
    checksum: str = DEFAULT_CHECKSUM,
    workdir: Optional[str] = None,
    keep: bool = False,
    do_install: bool = False,
    log_key: str = "install_log"
) -> int:
    """Télécharge, vérifie, extrait et compile libarchive."""
    append_log(log_key, "=== Début de l'installation libarchive ===")
    filename = filename or DEFAULT_FILENAME_TEMPLATE.format(version=version)
    url = url or DEFAULT_URL_TEMPLATE.format(filename=filename)
    workdir_path = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="libarchive-build-"))
    workdir_path.mkdir(parents=True, exist_ok=True)
    archive_path = workdir_path / filename

    try:
        append_log(log_key, f"Répertoire de travail: {workdir_path}")
        download_file(url, archive_path, log_key)
        append_log(log_key, "Vérification du checksum SHA-256...")
        actual = sha256_of_file(archive_path)
        append_log(log_key, f"Attendu: {checksum}")
        append_log(log_key, f"Actuel : {actual}")
        if actual != checksum:
            raise ValueError("Checksum mismatch! Abandon.")
        source_dir = extract_tar_gz(archive_path, workdir_path, log_key)
        append_log(log_key, "Compilation depuis les sources (configure && make)...")
        build_from_source(source_dir, log_key, do_install=do_install)
        append_log(log_key, "Compilation terminée avec succès.")
        if not keep:
            try:
                archive_path.unlink(missing_ok=True)
            except Exception:
                pass
            # supprimer le répertoire source
            try:
                shutil.rmtree(source_dir)
            except Exception:
                pass
            # si workdir était temporaire, le supprimer
            if workdir is None:
                try:
                    shutil.rmtree(workdir_path)
                except Exception:
                    pass
        append_log(log_key, "=== Installation terminée ===")
        return 0
    except Exception as exc:
        append_log(log_key, f"Erreur: {exc}")
        append_log(log_key, f"Workdir préservé: {workdir_path}")
        return 1

# ---------------------------
# Fonctions Zstandard
# ---------------------------

def compress_with_zstd(input_bytes: bytes, level: int = 3) -> bytes:
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(input_bytes)

def decompress_with_zstd(input_bytes: bytes) -> bytes:
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(input_bytes)

# ---------------------------
# UI Streamlit
# ---------------------------

# Sidebar: installation options
st.sidebar.header("Installer libarchive (depuis les sources)")
with st.sidebar.form("install_form"):
    version = st.text_input("Version", value=DEFAULT_VERSION)
    filename = st.text_input("Nom du fichier (optionnel)", value="")
    url = st.text_input("URL (optionnel)", value="")
    checksum = st.text_input("SHA-256 attendu", value=DEFAULT_CHECKSUM)
    workdir = st.text_input("Répertoire de travail (laisser vide pour tempdir)", value="")
    keep = st.checkbox("Conserver les artefacts (keep)", value=False)
    do_install = st.checkbox("Exécuter 'make install' (peut nécessiter sudo)", value=False)
    install_submit = st.form_submit_button("Lancer l'installation")

# Zone principale: deux colonnes
col1, col2 = st.columns(2)

# Colonne gauche: Installation
with col1:
    st.header("Installation libarchive")
    if "install_log" not in st.session_state:
        st.session_state["install_log"] = []
    st.text("Logs d'installation:")
    log_area = st.empty()
    log_area.text(get_log_text("install_log"))

    if install_submit:
        # lancer l'installation dans un thread pour ne pas bloquer l'UI
        def target():
            # vider le log
            st.session_state["install_log"] = []
            st.experimental_rerun()  # forcer rafraîchissement pour afficher log vide
        # Start a thread to clear logs and then run install in another thread to avoid blocking
        # We'll run the install synchronously but update logs after completion (Streamlit limitations).
        st.session_state["install_log"] = []
        st.experimental_rerun()

    # Button to actually run (separate from form to allow streaming logs after)
    if st.button("Exécuter l'installation maintenant"):
        st.session_state["install_log"] = []
        with st.spinner("Installation en cours..."):
            ret = install_libarchive(
                version=version,
                url=url or None,
                filename=filename or None,
                checksum=checksum,
                workdir=workdir or None,
                keep=keep,
                do_install=do_install,
                log_key="install_log"
            )
        st.success("Installation terminée" if ret == 0 else "Installation échouée")
        log_area.text(get_log_text("install_log"))

    # Afficher logs en direct (rafraîchir manuellement)
    if st.button("Rafraîchir les logs"):
        log_area.text(get_log_text("install_log"))

# Colonne droite: Zstandard compressor
with col2:
    st.header("Zstandard Compressor")
    st.write("Uploadez un fichier pour le compresser ou le décompresser avec zstandard.")
    uploaded = st.file_uploader("Choisir un fichier", type=None)
    zstd_level = st.slider("Niveau de compression zstd", min_value=1, max_value=22, value=3)
    action = st.radio("Action", ("Compresser", "Décompresser"))

    if uploaded is not None:
        file_bytes = uploaded.read()
        st.write(f"Fichier: **{uploaded.name}** — taille: {len(file_bytes)} bytes")
        if action == "Compresser":
            try:
                compressed = compress_with_zstd(file_bytes, level=zstd_level)
                st.success(f"Compression terminée — taille compressée: {len(compressed)} bytes")
                st.download_button(
                    label="Télécharger le fichier compressé (.zst)",
                    data=compressed,
                    file_name=f"{uploaded.name}.zst",
                    mime="application/octet-stream"
                )
            except Exception as exc:
                st.error(f"Erreur lors de la compression: {exc}")
        else:
            # Décompression
            try:
                decompressed = decompress_with_zstd(file_bytes)
                st.success(f"Décompression terminée — taille: {len(decompressed)} bytes")
                st.download_button(
                    label="Télécharger le fichier décompressé",
                    data=decompressed,
                    file_name=f"{uploaded.name}.decompressed",
                    mime="application/octet-stream"
                )
            except Exception as exc:
                st.error(f"Erreur lors de la décompression: {exc}")

# Section bas: aide et recommandations
st.markdown("---")
st.subheader("Notes et recommandations")
st.markdown(
    """
- **Privilèges**: `make install` peut nécessiter des privilèges root (`sudo`). Si vous cochez l'option, exécutez l'application dans un environnement où vous pouvez fournir ces privilèges ou exécutez `make install` manuellement.
- **Dépendances de compilation**: sur Debian/Ubuntu installez `build-essential`, `autoconf`, `automake`, `libtool`, etc. Le script ne les installe pas automatiquement.
- **Sécurité**: le checksum SHA-256 est vérifié avant extraction.
- **Personnalisation**: changez la version ou l'URL si vous souhaitez compiler une autre version.
"""
)

# Footer: afficher logs d'installation si présents
if st.session_state.get("install_log"):
    st.markdown("### Logs d'installation complets")
    st.code(get_log_text("install_log"))
