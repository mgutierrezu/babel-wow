# -*- coding: utf-8 -*-
"""Ubicación de los archivos del programa."""

import shutil
import sys
from pathlib import Path

# Carpeta de los archivos editables: junto al .exe, o la carpeta Traductor/ al correr el .py.
CONGELADO = getattr(sys, "frozen", False)
CARPETA = Path(sys.executable).parent if CONGELADO else Path(__file__).resolve().parent.parent
# Carpeta de los archivos empaquetados por PyInstaller dentro del .exe.
RECURSOS = Path(getattr(sys, "_MEIPASS", CARPETA))


def resolver(nombre):
    """Convierte una ruta de la configuración en absoluta, relativa a la carpeta del programa."""
    ruta = Path(nombre)
    return ruta if ruta.is_absolute() else CARPETA / ruta


def preparar_archivo(nombre, plantilla=None):
    """Devuelve la ruta editable de un archivo. Si no existe, lo crea copiando la
    plantilla (por defecto, el archivo del mismo nombre empaquetado en el .exe)."""
    destino = resolver(nombre)
    if not destino.exists():
        origen = RECURSOS / (plantilla or nombre)
        if origen.exists() and origen != destino:
            try:
                shutil.copyfile(origen, destino)
            except OSError:
                return origen
    return destino
