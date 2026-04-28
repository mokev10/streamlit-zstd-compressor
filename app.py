import streamlit as st
from compressor import compress_file, decompress_file

st.title("Compression Zstandard")

uploaded_file = st.file_uploader("Choisir un fichier", type=["zip","rar","7z","txt","csv","bin"])
level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    if st.button("Compresser"):
        output_path = compress_file(uploaded_file, level)
        st.success(f"Fichier compressé : {output_path}")

    if st.button("Décompresser"):
        output_path = decompress_file(uploaded_file)
        st.success(f"Fichier décompressé : {output_path}")
