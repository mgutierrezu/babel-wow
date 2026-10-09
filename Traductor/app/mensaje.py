# -*- coding: utf-8 -*-
"""Formatos que el addon deja en el portapapeles.

    [TR] Nombre (Canal): mensaje    un mensaje del chat, para leerlo en español
    [EN] mensaje                    lo que escribió el jugador con /twow, para enviarlo en inglés
"""

import re
from dataclasses import dataclass

PREFIJO_LEER = "[TR]"
PREFIJO_ESCRIBIR = "[EN]"
FORMATO = re.compile(r"^\[TR\]\s*(.+?)\s*\((.+?)\):\s*(.*)$", re.DOTALL)


@dataclass(frozen=True)
class Mensaje:
    remitente: str
    canal: str
    texto: str
    para_enviar: bool = False  # True: el jugador lo escribió en español y hay que pasarlo a inglés


def es_mensaje(texto):
    """Indica si un texto copiado viene del addon. Todo lo demás se ignora."""
    return bool(texto) and texto.lstrip().startswith((PREFIJO_LEER, PREFIJO_ESCRIBIR))


def analizar(texto):
    """Convierte el texto copiado en un Mensaje."""
    texto = texto.strip()
    if texto.startswith(PREFIJO_ESCRIBIR):
        return Mensaje("Yo", "para enviar", texto[len(PREFIJO_ESCRIBIR):].strip(), para_enviar=True)
    coincidencia = FORMATO.match(texto)
    if coincidencia:
        remitente, canal, contenido = coincidencia.groups()
        return Mensaje(remitente, canal, contenido.strip())
    return Mensaje("Desconocido", "Chat", texto[len(PREFIJO_LEER):].strip())
