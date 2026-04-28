import os

def file_size(path: str) -> str:
    """Retourne la taille du fichier en MB."""
    size = os.path.getsize(path) / (1024 * 1024)
    return f"{size:.2f} MB"
