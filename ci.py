#!/usr/bin/env python3
# ci.py
"""
Script d'automatisation CI local pour projet Streamlit.

Fonctions :
- crée (optionnellement) un virtualenv isolé,
- installe les dépendances depuis requirements.txt,
- exécute pytest et retourne le code de sortie.

Usage :
  python ci.py                # installe et lance pytest dans l'environnement courant
  python ci.py --venv .venv   # crée ./venv, installe et lance pytest dedans
  python ci.py --requirements requirements.txt
  python ci.py --pytest-args "-q -k fast"
"""

from __future__ import annotations

import argparse
import os
import streamlit as st
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run(cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """Exécute une commande en streaming et retourne le code de sortie."""
    print(f"> {' '.join(shlex.quote(p) for p in cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    proc.wait()
    return proc.returncode


def create_virtualenv(venv_path: Path) -> int:
    """Crée un virtualenv dans venv_path."""
    if venv_path.exists():
        print(f"Virtualenv déjà présent : {venv_path}")
        return 0
    print(f"Création du virtualenv dans {venv_path} ...")
    cmd = [sys.executable, "-m", "venv", str(venv_path)]
    return run(cmd)


def install_requirements(python_exe: str, requirements: Optional[Path]) -> int:
    """Installe pip et requirements via pip."""
    # Upgrade pip
    rc = run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    if rc != 0:
        return rc
    # Install requirements if present
    if requirements and requirements.exists():
        print(f"Installation des dépendances depuis {requirements} ...")
        rc = run([python_exe, "-m", "pip", "install", "-r", str(requirements)])
        return rc
    else:
        print("Aucun requirements.txt trouvé, installation minimale de streamlit et pytest.")
        return run([python_exe, "-m", "pip", "install", "streamlit", "pytest"])


def run_pytest(python_exe: str, pytest_args: Optional[List[str]] = None, cwd: Optional[Path] = None) -> int:
    """Lance pytest via l'interpréteur python_exe."""
    cmd = [python_exe, "-m", "pytest"]
    if pytest_args:
        cmd.extend(pytest_args)
    return run(cmd, cwd=cwd)


def parse_args(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="CI helper for Streamlit project: install deps and run pytest.")
    p.add_argument("--venv", help="Path to virtualenv to create/use (if omitted, uses current env)", default=None)
    p.add_argument("--requirements", help="Path to requirements.txt (default: ./requirements.txt)", default="requirements.txt")
    p.add_argument("--pytest-args", help="Arguments to pass to pytest (quoted string)", default="")
    p.add_argument("--workdir", help="Working directory where tests should run (default: project root)", default=".")
    p.add_argument("--skip-install", action="store_true", help="Skip installing dependencies")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    workdir = Path(args.workdir).resolve()
    req_path = Path(args.requirements).resolve()

    # Determine python executable to use
    if args.venv:
        venv_path = Path(args.venv).resolve()
        rc = create_virtualenv(venv_path)
        if rc != 0:
            print("Échec création virtualenv.", file=sys.stderr)
            return rc
        # Python inside venv
        if os.name == "nt":
            python_exe = str(venv_path / "Scripts" / "python.exe")
        else:
            python_exe = str(venv_path / "bin" / "python")
    else:
        python_exe = sys.executable

    print(f"Utilisation de l'interpréteur Python : {python_exe}")
    if not args.skip_install:
        rc = install_requirements(python_exe, req_path if req_path.exists() else None)
        if rc != 0:
            print("Échec de l'installation des dépendances.", file=sys.stderr)
            return rc
    else:
        print("Installation des dépendances ignorée (--skip-install).")

    pytest_args = shlex.split(args.pytest_args) if args.pytest_args else []
    rc = run_pytest(python_exe, pytest_args=pytest_args, cwd=workdir)
    if rc == 0:
        print("Tests réussis (exit code 0).")
    else:
        print(f"Tests échoués (exit code {rc}).", file=sys.stderr)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
