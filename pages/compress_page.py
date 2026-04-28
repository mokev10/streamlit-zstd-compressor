import streamlit as st
import zstandard as zstd

st.title("🚀 Compression de fichiers")

def compress_data(data: bytes, level: int) -> bytes:
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)

uploaded_file = st.file_uploader(
    "Choisir un fichier à compresser",
    type=["zip", "rar", "7z", "txt", "csv", "bin"]
)

level = st.slider("Niveau de compression (1-22)", 1, 22, 15)

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    if st.button("Compresser"):
        with st.spinner("Compression en cours..."):
            try:
                compressed = compress_data(file_bytes, level)
                st.download_button(
                    label="⬇️ Télécharger le fichier compressé (.zst)",
                    data=compressed,
                    file_name=f"{filename}.zst"
                )
                st.success("Compression terminée avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de la compression : {e}")
