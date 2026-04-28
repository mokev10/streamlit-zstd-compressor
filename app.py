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
st.title("🗜️ Zstandard Ultra Compressor")

# Fonctions de compression intégrées pour éviter les erreurs d'import
def compress_data(data, level):
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)

def decompress_data(data):
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)

uploaded_file = st.file_uploader(
    "Choisir un fichier",
    type=["zip", "rar", "7z", "txt", "csv", "bin", "zst"]
)

level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Compresser"):
            with st.spinner("Compression ultra en cours..."):
                try:
                    compressed = compress_data(file_bytes, level)
                    st.download_button(
                        label="⬇️ Télécharger le .zst",
                        data=compressed,
                        file_name=f"{filename}.zst"
                    )
                    st.success("Compression terminée !")
                except Exception as e:
                    st.error(f"Erreur lors de la compression : {e}")

    with col2:
        if filename.endswith(".zst"):
            if st.button("🔓 Décompresser"):
                with st.spinner("Décompression en cours..."):
                    try:
                        decompressed = decompress_data(file_bytes)
                        new_filename = filename.replace(".zst", "")
                        st.download_button(
                            label="⬇️ Télécharger l'original",
                            data=decompressed,
                            file_name=new_filename
                        )
                        st.success("Décompression terminée !")
                    except Exception as e:
                        st.error(f"Erreur : Ce fichier n'est pas un .zst valide.")
        else:
            st.info("Fichier standard détecté.")

st.divider()
st.caption("Note : La compression de 1Go vers 15Mo dépend de la nature des données. Le niveau 22 est le plus puissant.")
