#!/usr/bin/env python3
# eleventy.config.py
"""
Conversion Python de eleventy.config.js

Fonctionnalités :
- Représente la configuration Eleventy originale sous forme de dictionnaire Python.
- Lit le logo SVG (docs/assets/dit-logo.svg) et l'intègre dans la configuration.
- Fournit des utilitaires CLI pour afficher la config, copier les assets (passthrough),
  et écrire la config en JSON.

Usage :
    python eleventy.config.py --show-config
    python eleventy.config.py --copy-assets --output-dir _site
    python eleventy.config.py --write-json eleventy_config.json
"""

from __future__ import annotations

import json
import streamlit as st
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import sys

# -------------------------
# Configuration principale
# -------------------------

SERVICE_NAME = "stream-zip"

DEFAULTS = {
    "icons": {
        "shortcut": "/assets/dit-favicon.png"
    },
    "header": {
        # html will be filled by reading the SVG file if present
        "logotype": {
            "html": None
        }
    },
    # This is documented as needing to be a full URL rather than a path
    "opengraphImageUrl": "https://stream-zip.docs.trade.gov.uk/assets/dbt-social.jpg",
    "titleSuffix": SERVICE_NAME,
    "showBreadcrumbs": False,
    "serviceNavigation": {
        "serviceName": SERVICE_NAME,
        "serviceUrl": "/",
        "navigation": [
            {"text": "Get started", "href": "/get-started/"},
            {"text": "API reference", "href": "/api/"},
            {"text": "Contributing", "href": "/contributing/"},
        ],
    },
    "footer": {
        "logo": False,
        "meta": {
            "items": [
                {
                    "href": "https://github.com/uktrade/stream-zip",
                    "text": "GitHub repository for stream-zip",
                },
                {
                    "href": "https://www.gov.uk/government/organisations/department-for-business-and-trade",
                    "text": "Created by the Department for Business and Trade (DBT)",
                },
            ]
        },
    },
    "stylesheets": ["/assets/styles.css"],
}

# Eleventy directory options equivalent
DIR_OPTIONS = {
    "dataTemplateEngine": "njk",
    "htmlTemplateEngine": "njk",
    "markdownTemplateEngine": "njk",
    "dir": {
        # Use layouts from the plugin
        "input": "docs",
    },
}


# -------------------------
# Dataclasses / Types
# -------------------------

@dataclass
class NavigationItem:
    text: str
    href: str


@dataclass
class ServiceNavigation:
    serviceName: str
    serviceUrl: str
    navigation: List[NavigationItem]


@dataclass
class FooterMetaItem:
    href: str
    text: str


@dataclass
class Footer:
    logo: bool
    meta: Dict[str, List[FooterMetaItem]]


# -------------------------
# Helpers
# -------------------------

def read_svg(path: Path) -> Optional[str]:
    """
    Lit un fichier SVG et retourne son contenu en texte.
    Retourne None si le fichier n'existe pas.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def build_eleventy_config(project_root: Path) -> Dict:
    """
    Construit la configuration Eleventy en Python, en lisant le SVG si présent.
    """
    cfg = dict(DEFAULTS)  # shallow copy
    # Read logo SVG if available
    svg_path = project_root / "docs" / "assets" / "dit-logo.svg"
    svg_html = read_svg(svg_path)
    if svg_html:
        cfg["header"] = dict(cfg.get("header", {}))
        cfg["header"]["logotype"] = {"html": svg_html}
    else:
        # Keep None if not found
        cfg["header"] = dict(cfg.get("header", {}))
        cfg["header"]["logotype"] = {"html": None}

    # Merge directory options
    cfg_out = {
        "pluginOptions": cfg,
        "eleventyOptions": DIR_OPTIONS,
    }
    return cfg_out


def copy_passthrough(src_paths: List[Path], dest_dir: Path, overwrite: bool = True) -> None:
    """
    Copie les chemins listés (fichiers ou répertoires) vers dest_dir.
    Comportement similaire à eleventyConfig.addPassthroughCopy.
    """
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    for src in src_paths:
        src = src.resolve()
        if not src.exists():
            print(f"[warn] Source introuvable, skip: {src}")
            continue

        # Determine destination path
        if src.is_dir():
            target = dest_dir / src.name
            if target.exists() and overwrite:
                shutil.rmtree(target)
            print(f"Copying directory {src} -> {target}")
            shutil.copytree(src, target)
        else:
            target = dest_dir / src.name
            if target.exists() and overwrite:
                target.unlink()
            print(f"Copying file {src} -> {target}")
            shutil.copy2(src, target)


def write_config_json(cfg: Dict, out_path: Path) -> None:
    """
    Écrit la configuration en JSON lisible.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert any non-serializable values (like None) naturally
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"Wrote config JSON to {out_path}")


# -------------------------
# CLI
# -------------------------

def parse_args(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="eleventy.config.py - équivalent Python de eleventy.config.js")
    p.add_argument("--show-config", action="store_true", help="Afficher la configuration construite (JSON) sur stdout")
    p.add_argument("--write-json", metavar="OUT", help="Écrire la configuration en JSON dans le fichier OUT")
    p.add_argument("--copy-assets", action="store_true", help="Copier docs/assets et docs/CNAME vers --output-dir")
    p.add_argument("--output-dir", metavar="DIR", default="_site", help="Répertoire de sortie pour --copy-assets (défaut: _site)")
    p.add_argument("--project-root", metavar="DIR", default=".", help="Racine du projet (défaut: .)")
    p.add_argument("--no-overwrite", action="store_true", help="Ne pas écraser les fichiers existants lors de la copie")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    project_root = Path(args.project_root).resolve()
    cfg = build_eleventy_config(project_root)

    if args.show_config:
        print(json.dumps(cfg, indent=2, ensure_ascii=False))

    if args.write_json:
        out_path = Path(args.write_json)
        write_config_json(cfg, out_path)

    if args.copy_assets:
        # Determine sources: ./docs/assets and ./docs/CNAME (if present)
        assets_dir = project_root / "docs" / "assets"
        cname_file = project_root / "docs" / "CNAME"
        sources = []
        if assets_dir.exists():
            sources.append(assets_dir)
        else:
            print(f"[warn] assets directory not found: {assets_dir}")
        if cname_file.exists():
            sources.append(cname_file)
        else:
            print(f"[warn] CNAME file not found: {cname_file}")

        output_dir = Path(args.output_dir).resolve()
        copy_passthrough(sources, output_dir, overwrite=not args.no_overwrite)
        print(f"Assets copied to {output_dir}")

    # If nothing requested, print short help
    if not (args.show_config or args.write_json or args.copy_assets):
        print("Aucune action demandée. Utilisez --help pour voir les options.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
