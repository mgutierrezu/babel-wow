# -*- coding: utf-8 -*-
"""Archivos que el programa escribe: historial y estado de la ventana."""

import json
import os
from datetime import datetime


class Historial:
    """Registro de traducciones en un archivo de texto."""

    def __init__(self, ruta, activo=True):
        self.ruta = ruta
        self.activo = activo

    def guardar(self, remitente, canal, original, traduccion):
        if not self.activo:
            return
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.ruta, "a", encoding="utf-8") as archivo:
                archivo.write(f"[{hora}] {remitente} ({canal})\n")
                archivo.write(f"  Original:   {original}\n")
                archivo.write(f"  Traducción: {traduccion}\n\n")
        except OSError:
            pass

    def abrir(self):
        """Abre el historial con el programa predeterminado de Windows."""
        if self.ruta.exists():
            os.startfile(self.ruta)


class Estado:
    """Datos que el programa recuerda entre sesiones (posición de la ventana)."""

    def __init__(self, ruta):
        self.ruta = ruta

    def leer(self):
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return datos if isinstance(datos, dict) else {}

    def guardar(self, datos):
        try:
            self.ruta.write_text(json.dumps(datos), encoding="utf-8")
        except OSError:
            pass
