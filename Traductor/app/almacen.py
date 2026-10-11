# -*- coding: utf-8 -*-
"""Archivos que el programa escribe: historial y estado de la ventana."""

import json
import os
from datetime import datetime


class Historial:
    """Registro de traducciones en un archivo de texto.

    Para que no crezca sin límite, al pasar de maximo_mb el archivo se guarda
    como "<nombre>.anterior<ext>" (reemplazando al anterior que hubiera) y se
    empieza uno nuevo. Así se conserva siempre lo más reciente, en dos archivos
    que juntos no superan el doble del máximo. Con maximo_mb=0 no se limita.
    """

    def __init__(self, ruta, activo=True, maximo_mb=10):
        self.ruta = ruta
        self.activo = activo
        self.maximo_bytes = int(maximo_mb * 1024 * 1024)
        self.ruta_anterior = ruta.with_name(f"{ruta.stem}.anterior{ruta.suffix}")

    def _rotar_si_hace_falta(self):
        if self.maximo_bytes <= 0:
            return
        try:
            if self.ruta.stat().st_size >= self.maximo_bytes:
                os.replace(self.ruta, self.ruta_anterior)  # lo que había en "anterior" se pierde
        except OSError:
            pass  # si no existe o está abierto en otro programa, se sigue escribiendo en el actual

    def guardar(self, remitente, canal, original, traduccion):
        if not self.activo:
            return
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._rotar_si_hace_falta()
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
