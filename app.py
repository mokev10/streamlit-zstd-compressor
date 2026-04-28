import streamlit as st
import tempfile
import os
import sys

# Sécurité pour l'importation : on ajoute le dossier courant au chemin système
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from compressor.compress import compress_file
    from compressor.decompress import decompress_file
except ImportError:
    st.error("Erreur : Les modules dans le dossier 'compressor' sont introuvables. Vérifiez la structure GitHub.")

st.set_page_config(page_title="Zstd Compressor", layout="centered")
st.title("🗜️ Zstandard Ultra Compressor")

uploaded_file = st.file_uploader(
    "Choisir un fichier",
    type=["zip", "rar", "7z", "txt", "csv", "bin", "zst"]
)

level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    # Création d'un fichier temporaire propre
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, uploaded_file.name)
        
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Compresser"):
                output_path = input_path + ".zst"
                with st.spinner("Compression en cours..."):
                    compress_file(input_path, output_path, level)
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Télécharger le .zst",
                            data=f,
                            file_name=uploaded_file.name + ".zst"
                        )
                st.success("Terminé !")

        with col2:
            if uploaded_file.name.endswith(".zst"):
                if st.button("🔓 Décompresser"):
                    output_path = input_path.replace(".zst", "")
                    with st.spinner("Décompression en cours..."):
                        decompress_file(input_path, output_path)
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Télécharger le fichier original",
                                data=f,
                                file_name=os.path.basename(output_path)
                            )
                    st.success("Décompressé !")
            else:
                st.info("L'option décompression n'apparaît que pour les fichiers .zst")
