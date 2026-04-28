import streamlit as st
import zstandard as zstd

st.title("🔓 Décompression de fichiers")

def decompress_data(data: bytes) -> bytes:
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)

uploaded_file = st.file_uploader(
    "Choisir un fichier .zst à décompresser",
    type=["zst"]
)

if uploaded_file:
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    if st.button("Décompresser"):
        with st.spinner("Décompression en cours..."):
            try:
                decompressed = decompress_data(file_bytes)
                new_filename = filename.replace(".zst", "")
                st.download_button(
                    label="⬇️ Télécharger le fichier décompressé",
                    data=decompressed,
                    file_name=new_filename
                )
                st.success("Décompression terminée avec succès !")
            except Exception:
                st.error("Erreur : Ce fichier n'est pas un .zst valide.")
