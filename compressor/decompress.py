import zstandard as zstd

def decompress_file(input_path: str, output_path: str):
    """Décompresse un fichier .zst avec Zstandard."""
    dctx = zstd.ZstdDecompressor()
    with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
        dctx.copy_stream(f_in, f_out)
    return output_path
