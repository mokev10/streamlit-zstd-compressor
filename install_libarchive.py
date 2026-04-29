#!/usr/bin/env python3
# install_libarchive.py
"""
Télécharge, vérifie, extrait et compile libarchive depuis les sources.

Usage examples:
  python install_libarchive.py
  python install_libarchive.py --version 3.5.3 --keep
  python install_libarchive.py --url https://www.libarchive.org/downloads/libarchive-3.5.3.tar.gz
  python install_libarchive.py --checksum 72788e5f58d16febddfa262a5215e05fc9c79f2670f641ac039e6df44330ef51
  python install_libarchive.py --workdir /tmp/libarchive-build --install
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
from typing import Optional

DEFAULT_VERSION = "3.5.3"
DEFAULT_FILENAME_TEMPLATE = "libarchive-{version}.tar.gz"
DEFAULT_URL_TEMPLATE = "https://www.libarchive.org/downloads/{filename}"
DEFAULT_CHECKSUM = "72788e5f58d16febddfa262a5215e05fc9c79f2670f641ac039e6df44330ef51"


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """Télécharge une URL vers le chemin dest (écrase si existe)."""
    req = Request(url, headers={"User-Agent": "python-urllib/3"})
    with urlopen(req) as resp, open(dest, "wb") as out:
        total = resp.getheader("Content-Length")
        total_int = int(total) if total and total.isdigit() else None
        downloaded = 0
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total_int:
                pct = downloaded * 100 // total_int
                print(f"\rTéléchargé: {downloaded}/{total_int} bytes ({pct}%)", end="", flush=True)
    if total_int:
        print()
    print(f"Téléchargement terminé: {dest}")


def sha256_of_file(path: Path) -> str:
    """Calcule le SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_tar_gz(archive_path: Path, dest_dir: Path) -> Path:
    """Extrait une archive .tar.gz dans dest_dir et retourne le répertoire extrait principal."""
    print(f"Extraction de {archive_path} dans {dest_dir}")
    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        tar.extractall(path=dest_dir)
        # Déterminer le répertoire top-level créé
        top_dirs = {m.name.split("/")[0] for m in members if m.name and "/" in m.name}
        if not top_dirs:
            # fallback: nom de l'archive sans suffixe
            return dest_dir / archive_path.stem
        top_dir = sorted(top_dirs)[0]
        extracted = dest_dir / top_dir
        print(f"Répertoire extrait: {extracted}")
        return extracted


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Exécute une commande et affiche stdout/stderr en streaming."""
    print(f"Running: {' '.join(cmd)} (cwd={cwd})")
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    proc.wait()
    print(f"Commande terminée avec code {proc.returncode}")
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    return subprocess.CompletedProcess(cmd, proc.returncode)


def build_from_source(source_dir: Path, do_install: bool = False) -> None:
    """Rend configure exécutable, lance ./configure puis make (et optionnellement make install)."""
    configure_path = source_dir / "configure"
    if not configure_path.exists():
        raise FileNotFoundError(f"configure introuvable dans {source_dir}")
    # Rendre exécutable
    mode = configure_path.stat().st_mode
    configure_path.chmod(mode | 0o111)
    run_command(["./configure"], cwd=source_dir)
    run_command(["make"], cwd=source_dir)
    if do_install:
        # make install peut nécessiter sudo; on l'exécute tel quel
        run_command(["make", "install"], cwd=source_dir)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Télécharge, vérifie, extrait et compile libarchive depuis les sources.")
    p.add_argument("--version", default=DEFAULT_VERSION, help="Version de libarchive (défaut: %(default)s)")
    p.add_argument("--url", default=None, help="URL complète du tar.gz (par défaut: construit depuis la version)")
    p.add_argument("--filename", default=None, help="Nom du fichier archive (par défaut: libarchive-<version>.tar.gz)")
    p.add_argument("--checksum", default=DEFAULT_CHECKSUM, help="SHA-256 attendu du fichier téléchargé")
    p.add_argument("--workdir", default=None, help="Répertoire de travail (défaut: tempdir)")
    p.add_argument("--keep", action="store_true", help="Conserver les fichiers téléchargés et le répertoire de build")
    p.add_argument("--install", action="store_true", help="Exécuter 'make install' après la compilation (peut nécessiter sudo)")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    version = args.version
    filename = args.filename or DEFAULT_FILENAME_TEMPLATE.format(version=version)
    url = args.url or DEFAULT_URL_TEMPLATE.format(filename=filename)
    checksum_expected = args.checksum

    # Préparer le répertoire de travail
    if args.workdir:
        workdir = Path(args.workdir).expanduser().resolve()
        workdir.mkdir(parents=True, exist_ok=True)
        tempdir_created = False
    else:
        workdir = Path(tempfile.mkdtemp(prefix="libarchive-build-"))
        tempdir_created = True

    archive_path = workdir / filename

    try:
        print(f"Workdir: {workdir}")
        print(f"Téléchargement de {url} -> {archive_path}")
        download_file(url, archive_path)

        print("Vérification du checksum SHA-256...")
        checksum_actual = sha256_of_file(archive_path)
        print(f"Attendu: {checksum_expected}")
        print(f"Actuel : {checksum_actual}")
        if checksum_actual != checksum_expected:
            raise ValueError("Checksum mismatch! Abandon.")

        source_dir = extract_tar_gz(archive_path, workdir)

        print("Compilation depuis les sources (./configure && make)...")
        build_from_source(source_dir, do_install=args.install)
        print("Compilation terminée avec succès.")

        if not args.keep:
            try:
                archive_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                shutil.rmtree(source_dir)
            except Exception:
                pass
            if tempdir_created:
                try:
                    shutil.rmtree(workdir)
                except Exception:
                    pass

        print("Installation/compilation terminée.")
        return 0

    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        print(f"Workdir préservé: {workdir}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
