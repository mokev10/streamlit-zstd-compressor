import streamlit as st
import zstandard as zstd
import os
import tempfile

# Configuration de la page
st.set_page_config(
    page_title="AI Compressor Files",
    page_icon="https://img.icons8.com/fluency/48/folder-invoices--v2.png",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🗜️ Standard Ultra Compressor")

# Fonctions de compression et décompression
def compress_data(data: bytes, level: int) -> bytes:
    """Compresse des données en mémoire avec Zstandard."""
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)

def decompress_data(data: bytes) -> bytes:
    """Décompresse des données en mémoire avec Zstandard."""
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)

# Upload du fichier
uploaded_file = st.file_uploader(
    "Choisir un fichier",
    type=["zip", "rar", "7z", "txt", "csv", "bin", "zst"]
)

# Slider pour le niveau de compression
level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    # Deux colonnes pour séparer compression et décompression
    col1, col2 = st.columns(2)

    # Colonne compression
    with col1:
        if st.button("Compresser"):
            with st.spinner("Compression ultra en cours..."):
                try:
                    compressed = compress_data(file_bytes, level)
                    st.download_button(
                        label="Télécharger le fichier compressé (.zst)",
                        data=compressed,
                        file_name=f"{filename}.zst"
                    )
                    st.success("Compression terminée avec succès !")
                except Exception as e:
                    st.error(f"Erreur lors de la compression : {e}")

    # Colonne décompression
    with col2:
        if filename.endswith(".zst"):
            if st.button("🔓 Décompresser"):
                with st.spinner("Décompression en cours..."):
                    try:
                        decompressed = decompress_data(file_bytes)
                        new_filename = filename.replace(".zst", "")
                        st.download_button(
                            label="Télécharger le fichier décompressé",
                            data=decompressed,
                            file_name=new_filename
                        )
                        st.success("Décompression terminée avec succès !")
                    except Exception:
                        st.error("Erreur : Ce fichier n'est pas un .zst valide.")
        else:
            st.info("Fichier standard détecté (non compressé).")

# Footer
st.divider()
st.caption(
    "Note : Le ratio de compression dépend fortement du type de données. "
    "Le niveau 22 est le plus puissant mais peut être plus lent."
)
