import zstandard as zstd

def compress_file(input_path: str, output_path: str, level: int = 15):
    """Compresse un fichier avec Zstandard."""
    cctx = zstd.ZstdCompressor(level=level)
    with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
        cctx.copy_stream(f_in, f_out)
    return output_path
