#!/usr/bin/env python3
# devcontainer.py
"""
devcontainer.py

Convert and manage a VS Code Dev Container configuration for a Streamlit environment.

This script:
- Encodes the original devcontainer.json configuration as a Python structure.
- Can write a devcontainer.json file to disk.
- Can generate a simple Dockerfile that mirrors the chosen base image and installs
  requirements and optional system packages.
- Can write a requirements.txt and packages.txt helper files.
- Provides a small CLI to create the devcontainer artifacts and optionally run Streamlit locally.

Usage examples:
  # Write devcontainer.json and helper files to ./devcontainer
  python devcontainer.py --out ./devcontainer --write-json --write-dockerfile --write-requirements

  # Create files and print instructions
  python devcontainer.py --out ./devcontainer --create

  # Write files and run streamlit locally (not inside container)
  python devcontainer.py --out ./devcontainer --write-requirements --run-streamlit

Notes:
- This script does NOT build or run Docker containers. It generates configuration and helper files
  that you can use with VS Code Remote - Containers or GitHub Codespaces.
- The generated Dockerfile is a convenience starting point. Adjust it for your CI/host constraints.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import streamlit as st
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

# -------------------------
# Original devcontainer.json content (converted to Python)
# -------------------------

DEFAULT_DEVCONTAINER = {
    "name": "Python 3",
    # Use a base image; this is the original image from the JSON
    "image": "mcr.microsoft.com/devcontainers/python:1-3.11-bookworm",
    "customizations": {
        "codespaces": {
            "openFiles": [
                "README.md",
                "streamlit run app.py"
            ]
        },
        "vscode": {
            "settings": {},
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance"
            ]
        }
    },
    # Command to update system packages and install requirements
    "updateContentCommand": "[ -f packages.txt ] && sudo apt update && sudo apt upgrade -y && sudo xargs apt install -y <packages.txt; [ -f requirements.txt ] && pip3 install --user -r requirements.txt; pip3 install --user streamlit; echo '✅ Packages installed and Requirements met'",
    # Command to run after attaching (server side)
    "postAttachCommand": {
        "server": "streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false"
    },
    "portsAttributes": {
        "8501": {
            "label": "Application",
            "onAutoForward": "openPreview"
        }
    },
    "forwardPorts": [
        8501
    ]
}


# -------------------------
# Dataclasses for generation
# -------------------------

@dataclass
class DevContainerConfig:
    name: str
    image: str
    customizations: Dict[str, Any]
    updateContentCommand: str
    postAttachCommand: Dict[str, str]
    portsAttributes: Dict[str, Any]
    forwardPorts: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "image": self.image,
            "customizations": self.customizations,
            "updateContentCommand": self.updateContentCommand,
            "postAttachCommand": self.postAttachCommand,
            "portsAttributes": self.portsAttributes,
            "forwardPorts": self.forwardPorts,
        }


# -------------------------
# Helper functions
# -------------------------

def write_json_file(obj: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"Wrote JSON to {path}")


def generate_dockerfile(image: str, out_path: Path, packages_txt: Optional[str] = "packages.txt", requirements_txt: Optional[str] = "requirements.txt") -> None:
    """
    Generate a simple Dockerfile that uses the specified base image and installs:
    - system packages from packages.txt (if present)
    - Python requirements from requirements.txt (if present)
    - streamlit (ensures it's installed)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dockerfile_lines = [
        f"FROM {image}",
        "",
        "# Create a non-root user (devcontainer default behavior often does this)",
        "ARG USERNAME=vscode",
        "ARG USER_UID=1000",
        "ARG USER_GID=$USER_UID",
        "",
        "RUN apt-get update && apt-get install -y --no-install-recommends \\",
        "    ca-certificates \\",
        "    curl \\",
        "    build-essential \\",
        "    git \\",
        "    python3-venv \\",
        "    python3-dev \\",
        "    && rm -rf /var/lib/apt/lists/*",
        "",
        "# Create user",
        "RUN groupadd --gid $USER_GID $USERNAME || true \\",
        "    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME || true",
        "",
        "WORKDIR /workspace",
        "",
        "# Copy helper files if present",
        "COPY . /workspace",
        "",
        "# Install system packages listed in packages.txt (if present)",
        "RUN if [ -f /workspace/packages.txt ]; then \\",
        "      xargs apt-get update -y < /workspace/packages.txt && \\",
        "      xargs apt-get install -y < /workspace/packages.txt; \\",
        "    fi",
        "",
        "# Install Python requirements (user install to avoid sudo inside container)",
        "RUN if [ -f /workspace/requirements.txt ]; then \\",
        "      pip3 install --no-cache-dir -r /workspace/requirements.txt; \\",
        "    fi",
        "",
        "# Ensure streamlit is installed",
        "RUN pip3 install --no-cache-dir streamlit",
        "",
        "# Expose Streamlit port",
        "EXPOSE 8501",
        "",
        "# Default command (can be overridden by devcontainer postAttachCommand)",
        "CMD [\"/bin/bash\"]",
    ]
    dockerfile_text = "\n".join(dockerfile_lines)
    out_path.write_text(dockerfile_text, encoding="utf-8")
    print(f"Wrote Dockerfile to {out_path}")


def write_requirements(out_path: Path, extras: Optional[List[str]] = None) -> None:
    """
    Write a minimal requirements.txt suitable for the Streamlit environment.
    extras: additional packages to include (e.g., zstandard, pyzipper)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base = [
        "streamlit>=1.0",
    ]
    extras = extras or []
    lines = base + extras
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote requirements.txt to {out_path}")


def write_packages_txt(out_path: Path, packages: Optional[List[str]] = None) -> None:
    """
    Write a packages.txt listing apt packages to install inside the container.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    default_pkgs = [
        "build-essential",
        "autoconf",
        "automake",
        "libtool",
        "pkg-config",
        "ca-certificates",
        "curl",
        "unzip",
        "p7zip-full",
    ]
    pkgs = packages or default_pkgs
    out_path.write_text("\n".join(pkgs) + "\n", encoding="utf-8")
    print(f"Wrote packages.txt to {out_path}")


def print_instructions(devcontainer_dir: Path) -> None:
    print("\n=== Devcontainer helper files created ===")
    print(f"Directory: {devcontainer_dir.resolve()}")
    print("Files you can use with VS Code Remote - Containers or Codespaces:")
    for p in sorted(devcontainer_dir.iterdir()):
        print(" -", p.name)
    print("\nTo use in VS Code:")
    print("  1. Move the generated devcontainer.json and Dockerfile into .devcontainer/ in your repo root.")
    print("  2. Open the repo in VS Code and choose 'Reopen in Container'.")
    print("  3. The container will build using the Dockerfile and install packages from packages.txt and requirements.txt.")
    print("\nTo run Streamlit locally (outside container):")
    print("  python -m pip install -r {}/requirements.txt".format(devcontainer_dir))
    print("  streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false")
    print()


def run_streamlit_local(requirements_path: Optional[Path] = None, app_path: Optional[Path] = None) -> int:
    """
    Install requirements (optional) and run streamlit locally in the current process.
    This is a convenience helper for local development; it does not emulate the container.
    """
    if requirements_path and requirements_path.exists():
        print(f"Installing requirements from {requirements_path} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])
    else:
        print("No requirements.txt found or specified; ensure streamlit is installed in your environment.")
    app = app_path or Path("app.py")
    if not app.exists():
        print(f"Warning: {app} not found. Create your Streamlit app at {app} or specify --app-path.")
        return 2
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


# -------------------------
# CLI
# -------------------------

def parse_args(argv: Optional[List[str]] = None):
    import argparse
    p = argparse.ArgumentParser(description="devcontainer.py — generate devcontainer.json, Dockerfile and helpers for Streamlit")
    p.add_argument("--out", "-o", help="Output directory for generated files (default: ./devcontainer)", default="./devcontainer")
    p.add_argument("--write-json", action="store_true", help="Write devcontainer.json to the output directory")
    p.add_argument("--write-dockerfile", action="store_true", help="Write a Dockerfile to the output directory")
    p.add_argument("--write-requirements", action="store_true", help="Write a requirements.txt to the output directory")
    p.add_argument("--write-packages", action="store_true", help="Write a packages.txt to the output directory")
    p.add_argument("--create", action="store_true", help="Create all helper files (json, Dockerfile, requirements, packages)")
    p.add_argument("--run-streamlit", action="store_true", help="Run streamlit locally after optionally installing requirements")
    p.add_argument("--app-path", help="Path to the Streamlit app to run (default: app.py)", default="app.py")
    p.add_argument("--requirements-extras", help="Comma-separated extra Python packages to include in requirements.txt", default="")
    p.add_argument("--packages-list", help="Comma-separated apt packages to include in packages.txt", default="")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    devcfg = DevContainerConfig(
        name=DEFAULT_DEVCONTAINER["name"],
        image=DEFAULT_DEVCONTAINER["image"],
        customizations=DEFAULT_DEVCONTAINER["customizations"],
        updateContentCommand=DEFAULT_DEVCONTAINER["updateContentCommand"],
        postAttachCommand=DEFAULT_DEVCONTAINER["postAttachCommand"],
        portsAttributes=DEFAULT_DEVCONTAINER["portsAttributes"],
        forwardPorts=DEFAULT_DEVCONTAINER["forwardPorts"],
    )

    if args.create:
        args.write_json = True
        args.write_dockerfile = True
        args.write_requirements = True
        args.write_packages = True

    if args.write_json:
        write_json_file(devcfg.to_dict(), out_dir / "devcontainer.json")

    if args.write_dockerfile:
        generate_dockerfile(devcfg.image, out_dir / "Dockerfile")

    if args.write_requirements:
        extras = [s.strip() for s in args.requirements_extras.split(",") if s.strip()]
        write_requirements(out_dir / "requirements.txt", extras)

    if args.write_packages:
        pkgs = [s.strip() for s in args.packages_list.split(",") if s.strip()]
        write_packages_txt(out_dir / "packages.txt", pkgs or None)

    if args.write_json or args.write_dockerfile or args.write_requirements or args.write_packages:
        print_instructions(out_dir)

    if args.run_streamlit:
        req_path = out_dir / "requirements.txt" if (out_dir / "requirements.txt").exists() else None
        app_path = Path(args.app_path)
        return run_streamlit_local(requirements_path=req_path, app_path=app_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
