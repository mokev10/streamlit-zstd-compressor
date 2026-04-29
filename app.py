#!/usr/bin/env python3
# app.py
"""
Streamlit app — Zstandard advanced compressor with dictionary training and streaming.

Features:
- Upload a file (large files supported).
- Optionally train a Zstd dictionary from the uploaded file (or additional sample files).
- Streaming compression using zstandard with configurable level and threads.
- Quick sample compression to estimate final size before full run.
- Download compressed .zst file when done.
- Logs and progress shown in the UI.

Requirements:
- streamlit
- zstandard
Install: pip install streamlit zstandard
Run: streamlit run app.py
"""

from __future__ import annotations

import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, List

import streamlit as st
import zstandard as zstd

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Ultra-fast Zstd Compressor",
    page_icon="🗜️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🗜️ Ultra-fast file compressor — Zstandard (streaming + dictionary)")

# -------------------------
# Helpers: logging & utils
# -------------------------
def append_log(key: str, message: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key].append(f"{time.strftime('%H:%M:%S')} {message}")

def get_log_text(key: str) -> str:
    return "\n".join(st.session_state.get(key, []))

def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

# -------------------------
# Dictionary training helpers
# -------------------------
def sample_bytes_from_file(path: Path, sample_total: int = 4 * 1024 * 1024, chunk_size: int = 64 * 1024) -> List[bytes]:
    """
    Read samples from file to build a list of sample chunks for dictionary training.
    We take evenly spaced samples across the file to capture variety.
    """
    size = path.stat().st_size
    if size == 0:
        return []
    samples: List[bytes] = []
    # If file small, just read whole file as one sample
    if size <= sample_total:
        with path.open("rb") as f:
            data = f.read()
            # split into chunk_size pieces
            for i in range(0, len(data), chunk_size):
                samples.append(data[i : i + chunk_size])
        return samples
    # Otherwise take N samples evenly spaced
    n_samples = max(1, sample_total // chunk_size)
    step = max(1, size // n_samples)
    with path.open("rb") as f:
        for i in range(n_samples):
            pos = min(size - chunk_size, i * step)
            f.seek(pos)
            chunk = f.read(chunk_size)
            if chunk:
                samples.append(chunk)
    return samples

def train_zstd_dictionary(samples: List[bytes], dict_size: int = 112640) -> bytes:
    """
    Train a zstd dictionary from sample bytes list.
    Returns raw dictionary bytes.
    """
    if not samples:
        raise ValueError("No samples provided for dictionary training.")
    trainer = zstd.train_dictionary(dict_size, samples)
    return trainer.as_bytes()

# -------------------------
# Compression helpers (streaming)
# -------------------------
def compress_streaming(
    input_path: Path,
    output_path: Path,
    level: int = 19,
    threads: int = 0,
    dict_bytes: Optional[bytes] = None,
    chunk_size: int = 256 * 1024,
    progress_callback=None,
) -> int:
    """
    Stream-compress input_path -> output_path using zstandard streaming writer.
    - level: compression level (1..22+)
    - threads: 0 means auto; >0 uses that many threads (zstd lib uses multi-threading)
    - dict_bytes: optional dictionary bytes (from train_zstd_dictionary)
    - chunk_size: read chunk size in bytes
    - progress_callback: function(bytes_read, total_bytes) for UI updates
    Returns compressed file size in bytes.
    """
    total = input_path.stat().st_size
    dict_obj = zstd.ZstdCompressionDict(dict_bytes) if dict_bytes else None

    # Create compressor
    compressor = zstd.ZstdCompressor(level=level, dict_data=dict_obj, threads=threads or 0, write_content_size=True)

    with input_path.open("rb") as fin, output_path.open("wb") as fout:
        with compressor.stream_writer(fout) as compressor_writer:
            read = 0
            while True:
                chunk = fin.read(chunk_size)
                if not chunk:
                    break
                compressor_writer.write(chunk)
                read += len(chunk)
                if progress_callback:
                    progress_callback(read, total)
    return output_path.stat().st_size

def compress_sample_bytes(data: bytes, level: int = 19, dict_bytes: Optional[bytes] = None) -> bytes:
    """
    Compress a bytes object in-memory to estimate ratio.
    """
    dict_obj = zstd.ZstdCompressionDict(dict_bytes) if dict_bytes else None
    compressor = zstd.ZstdCompressor(level=level, dict_data=dict_obj, threads=0, write_content_size=True)
    return compressor.compress(data)

# -------------------------
# UI: Sidebar options
# -------------------------
st.sidebar.header("Options de compression")
level = st.sidebar.slider("Niveau de compression zstd", min_value=1, max_value=22, value=19, help="Niveau plus élevé = meilleure compression mais plus lent")
threads = st.sidebar.slider("Threads (0 = auto)", min_value=0, max_value=8, value=0)
use_dictionary = st.sidebar.checkbox("Entraîner un dictionnaire Zstd (recommandé pour fichiers similaires)", value=True)
dict_size_mb = st.sidebar.number_input("Taille du dictionnaire (KB)", min_value=16, max_value=1024 * 4, value=112, step=16, help="Taille du dictionnaire en KB (ex: 112 KB)")
dict_size_bytes = int(dict_size_mb) * 1024
sample_total_mb = st.sidebar.number_input("Taille d'échantillonnage pour entraînement (MB)", min_value=1, max_value=64, value=4, step=1)
sample_total_bytes = int(sample_total_mb) * 1024 * 1024
chunk_size_kb = st.sidebar.number_input("Taille de lecture (KB)", min_value=64, max_value=1024 * 1024, value=256, step=64)
chunk_size = int(chunk_size_kb) * 1024

st.sidebar.markdown("---")
st.sidebar.markdown("Conseils :\n- Si vos fichiers sont similaires (mêmes formats, mêmes motifs), entraînez un dictionnaire.\n- Pour un fichier unique, le dictionnaire peut aider si le fichier contient motifs répétitifs.\n- Niveau 19–22 donne de la compression maximale mais prend plus de CPU.")

# -------------------------
# Main UI: upload and actions
# -------------------------
st.header("1) Téléversez le fichier à compresser")
uploaded = st.file_uploader("Choisir un fichier (supporte gros fichiers)", type=None)

# Optional: allow uploading additional sample files for dictionary training
st.markdown("**(Optionnel)** Téléversez des fichiers d'exemple pour entraîner le dictionnaire (plusieurs).")
sample_uploads = st.file_uploader("Fichiers d'exemple (facultatif)", accept_multiple_files=True, type=None)

col1, col2 = st.columns([2, 1])

with col1:
    st.header("2) Prévisualiser et configurer")
    if uploaded is None:
        st.info("Téléversez un fichier pour activer les options de compression.")
    else:
        # Save uploaded file to temp path to operate on it
        tmp_dir = Path(st.session_state.get("tmp_dir", "")) if st.session_state.get("tmp_dir") else None
        if tmp_dir is None or not tmp_dir.exists():
            tmp_dir = Path(tempfile.mkdtemp(prefix="streamlit_compress_"))
            st.session_state["tmp_dir"] = str(tmp_dir)
        input_path = tmp_dir / uploaded.name
        # write file if not already saved
        if not input_path.exists():
            with input_path.open("wb") as f:
                f.write(uploaded.read())
        st.write(f"Fichier sauvegardé temporairement : **{input_path}** — taille: **{human_size(input_path.stat().st_size)}**")

        # Show quick sample compression estimate
        st.subheader("Estimation rapide (échantillon)")
        sample_preview_size = min(2 * 1024 * 1024, input_path.stat().st_size)  # 2MB sample
        with input_path.open("rb") as f:
            sample_data = f.read(sample_preview_size)
        # Optionally train dictionary from sample_uploads + sample from file
        dict_bytes: Optional[bytes] = None
        if use_dictionary:
            st.write("Préparation des échantillons pour entraînement du dictionnaire...")
            samples: List[bytes] = []
            # samples from uploaded sample files
            for s in sample_uploads:
                try:
                    b = s.read()
                    # split into chunks
                    for i in range(0, len(b), 64 * 1024):
                        samples.append(b[i : i + 64 * 1024])
                except Exception:
                    pass
            # samples from the main file (evenly spaced)
            samples += sample_bytes_from_file(input_path, sample_total=sample_total_bytes, chunk_size=64 * 1024)
            # limit number of samples to reasonable amount
            if len(samples) > 2000:
                samples = samples[:2000]
            st.write(f"{len(samples)} échantillons collectés pour entraînement.")
            if len(samples) >= 1:
                try:
                    dict_bytes = train_zstd_dictionary(samples, dict_size=dict_size_bytes)
                    st.success(f"Dictionnaire entraîné — taille: {human_size(len(dict_bytes))}")
                except Exception as exc:
                    st.error(f"Erreur entraînement dictionnaire: {exc}")
                    dict_bytes = None
            else:
                st.warning("Pas assez d'échantillons pour entraîner un dictionnaire.")
        else:
            st.info("Dictionnaire désactivé (optionnel).")

        # Estimate compression on sample
        st.write("Compression d'un petit échantillon pour estimer le ratio...")
        try:
            compressed_sample = compress_sample_bytes(sample_data, level=level, dict_bytes=dict_bytes)
            est_ratio = len(compressed_sample) / len(sample_data) if len(sample_data) else 1.0
            st.write(f"Échantillon: {human_size(len(sample_data))} → compressé: {human_size(len(compressed_sample))} (ratio ≈ {est_ratio:.2f})")
            # Extrapolate estimate for full file (very rough)
            full_size = input_path.stat().st_size
            est_full = int(full_size * est_ratio)
            st.write(f"Estimation approximative pour le fichier complet: {human_size(full_size)} → ~**{human_size(est_full)}**")
        except Exception as exc:
            st.error(f"Erreur lors de l'estimation: {exc}")

        # Compression action
        st.subheader("3) Lancer la compression complète (streaming)")
        out_name_default = f"{input_path.name}.zst"
        out_name = st.text_input("Nom du fichier compressé", value=out_name_default)
        keep_tmp = st.checkbox("Conserver les fichiers temporaires (pour debug)", value=False)

        if st.button("Compresser maintenant"):
            out_path = tmp_dir / out_name
            st.session_state["compress_log"] = []
            append_log("compress_log", f"Démarrage compression: {input_path.name}")
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_cb(read_bytes: int, total_bytes: int):
                pct = int(read_bytes * 100 / total_bytes) if total_bytes else 0
                progress_bar.progress(min(pct, 100))
                status_text.text(f"Compressé {human_size(read_bytes)} / {human_size(total_bytes)} ({pct}%)")

            try:
                start = time.time()
                compressed_size = compress_streaming(
                    input_path=input_path,
                    output_path=out_path,
                    level=level,
                    threads=threads,
                    dict_bytes=dict_bytes,
                    chunk_size=chunk_size,
                    progress_callback=progress_cb,
                )
                elapsed = time.time() - start
                append_log("compress_log", f"Compression terminée en {elapsed:.1f}s — taille: {human_size(compressed_size)}")
                st.success(f"Compression terminée — {human_size(compressed_size)}")
                st.write(f"Fichier compressé : **{out_path}** — taille: **{human_size(compressed_size)}**")
                # Provide download
                with out_path.open("rb") as f:
                    data = f.read()
                    st.download_button("Télécharger le fichier compressé (.zst)", data=data, file_name=out_path.name, mime="application/octet-stream")
                # Optionally show ratio
                orig = input_path.stat().st_size
                ratio = compressed_size / orig if orig else 0
                st.write(f"Ratio: {ratio:.3f} — réduction: {100*(1-ratio):.1f}%")
                append_log("compress_log", f"Ratio final: {ratio:.3f}")
                if not keep_tmp:
                    try:
                        input_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    # keep out_path so user can download; do not delete
                # show logs
                st.markdown("### Logs de compression")
                st.code(get_log_text("compress_log"))
            except Exception as exc:
                append_log("compress_log", f"Erreur: {exc}")
                st.error(f"Erreur pendant la compression: {exc}")
                st.code(get_log_text("compress_log"))

with col2:
    st.header("Aide et recommandations")
    st.markdown(
        """
- **Nature des données** : la compression dépend fortement du contenu. Données textuelles, CSV, JSON, logs, images répétitives se compressent très bien. Données déjà compressées (JPEG, MP4, archives) ne se compressent pas beaucoup.
- **Dictionnaire** : si vous traitez plusieurs fichiers similaires (mêmes formats), entraînez un dictionnaire sur un corpus d'exemples — cela améliore fortement la compression.
- **Niveau** : niveaux 19–22 donnent la meilleure compression mais augmentent le temps CPU.
- **Threads** : augmentez le nombre de threads si vous avez CPU disponible.
- **Streaming** : l'approche streaming évite d'utiliser toute la RAM pour les gros fichiers.
"""
    )
    st.markdown("---")
    st.subheader("Logs")
    if "compress_log" in st.session_state:
        st.code(get_log_text("compress_log"))
    else:
        st.write("Aucun log pour le moment.")

# Footer: housekeeping
st.markdown("---")
st.caption("Astuce : pour des tests reproductibles, fournissez un corpus d'exemples similaire et augmentez la taille du dictionnaire.")

