# 🗜️ Standard Ultra Compressor

## 📖 Description
**Standard Ultra Compressor** est une application **100% Python** construite avec **Streamlit**, permettant de compresser et décompresser des fichiers volumineux en utilisant l’algorithme **Zstandard (zstd)**.

Elle offre :
- ⚡ Une compression rapide
- 📦 Un excellent taux de réduction (ex : 900 MB → 15–20 MB selon les données)
- 🚀 Une décompression ultra-rapide

---

## 🚀 Fonctionnalités
- Interface web simple et intuitive (Streamlit)
- Compression de fichiers :
  - zip, rar, 7z, txt, csv, bin
- Décompression des fichiers `.zst`
- Choix du niveau de compression (1 à 22)
- Téléchargement direct des fichiers traités

---

## 🧠 À propos de ZPAQ (référence technique)

ZPAQ est un archiveur avancé orienté sauvegarde incrémentale.

### Caractéristiques :
- Archivage avec journalisation
- Sauvegarde incrémentale intelligente
- Conservation des anciennes versions
- Déduplication au niveau des fragments
- Compression multi-thread
- Chiffrement AES-256
- Format auto-descriptif

---

## 📦 Contenu de ZPAQ

| Fichier        | Version | Description |
|----------------|--------|-------------|
| zpaq.exe       | 7.15   | Archiveur Windows 32 bits |
| zpaq64.exe     | 7.15   | Archiveur Windows 64 bits |
| zpaq.cpp       | 7.15   | Code source |
| libzpaq.cpp    | 7.15   | API source |
| libzpaq.h      | 7.12   | API header |
| zpaq.pod       | 7.12   | Documentation |
| Makefile       | —      | Compilation Linux |
| COPYING        | —      | Licence |

Source : https://zip-compress.streamlit.app/

---

## ⚙️ Compilation

### Linux / Unix / Mac
```bash
make
