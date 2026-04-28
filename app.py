import streamlit as st
import tempfile
import os
from compressor.compress import compress_file
from compressor.decompress import decompress_file

# Configuration de la page
st.set_page_config(page_title="Zstd Compressor", layout="centered")
st.title("Streamlit Zstandard Compressor")

# Upload du fichier
uploaded_file = st.file_uploader(
    "Choisir un fichier",
    type=["zip", "rar", "7z", "txt", "csv", "bin"]
)

# Slider pour le niveau de compression
level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    # Sauvegarde temporaire du fichier uploadé
    temp_dir = tempfile.gettempdir()
    input_path = os.path.join(temp_dir, uploaded_file.name)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.read())

    # Bouton de compression
    if st.button("Compresser"):
        output_path = input_path + ".zst"
        compress_file(input_path, output_path, level)
        st.success(f"Fichier compressé : {output_path}")

    # Bouton de décompression
    if st.button("Décompresser"):
        # On retire l'extension .zst pour recréer le fichier original
        output_path = input_path.replace(".zst", "")
        decompress_file(input_path, output_path)
        st.success(f"Fichier décompressé : {output_path}")
