# OrthoSim

OrthoSim 0.1 is an **educational 3D geometry prototype** for Windows, not a clinical treatment-planning or tooth-movement prediction system.

**[Инструкция на русском](README_RU.md)**

## Features
- 14 schematic demo objects (not anatomical teeth)
- Import separate STL, PLY and OBJ models
- Translate and rotate selected objects
- Save/restore stages within a running session
- Export transformed meshes as STL and a JSON manifest

## Windows quick start
1. Install Python 3.12 (64-bit).
2. Run `setup_windows.bat`.
3. Run `start_windows.bat`.
4. Press `Открыть демонстрационную модель`.

## Development
- `app.py`: PySide6/PyVista editor
- `geometry.py`: 4x4 rigid transformations
- `test_geometry.py`: unit tests
- `requirements.txt`: dependencies

Run `python -m unittest -v test_geometry` to test geometry logic (requires NumPy).

**Privacy:** Never commit real patient identifiers, DICOM studies or clinical scans to this repository. Do not use the prototype for clinical decisions.

## Рабочая среда и переезд на новый ПК

[Библиотека инструментов и чек-лист установки](docs/TOOLS_LIBRARY.md) — рекомендуемые программы, безопасность, порядок восстановления OrthoSim и отложенные эксперименты с ИИ-агентами.
