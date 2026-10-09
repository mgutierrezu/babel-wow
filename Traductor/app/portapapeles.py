# -*- coding: utf-8 -*-
"""Portapapeles de Windows.

Se lee para detectar lo que el jugador copia desde el addon. Solo se escribe en
un caso: dejar lista la traducción al inglés que el jugador pidió con /twow,
para que la pegue él mismo. Nunca se envían teclas al juego.
"""

import ctypes
import time
from ctypes import wintypes

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalFree.argtypes = [wintypes.HANDLE]


def _abrir(intentos=10):
    """Abre el portapapeles; reintenta un momento si otro programa lo tiene ocupado."""
    for _ in range(intentos):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.03)
    return False


def _leer():
    """Devuelve (leído, texto). leído es False si el portapapeles estaba ocupado."""
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return True, None
    if not user32.OpenClipboard(None):
        return False, None
    try:
        manejador = user32.GetClipboardData(CF_UNICODETEXT)
        if not manejador:
            return True, None
        puntero = kernel32.GlobalLock(manejador)
        if not puntero:
            return True, None
        try:
            return True, ctypes.wstring_at(puntero)
        finally:
            kernel32.GlobalUnlock(manejador)
    finally:
        user32.CloseClipboard()


def _escribir(texto):
    """Reemplaza el contenido del portapapeles. Con texto vacío lo deja sin nada."""
    if not _abrir():
        return False
    try:
        user32.EmptyClipboard()
        if not texto:
            return True
        datos = ctypes.create_unicode_buffer(texto)
        tamano = ctypes.sizeof(datos)
        manejador = kernel32.GlobalAlloc(GMEM_MOVEABLE, tamano)
        puntero = kernel32.GlobalLock(manejador) if manejador else None
        if not puntero:
            return False
        ctypes.memmove(puntero, datos, tamano)
        kernel32.GlobalUnlock(manejador)
        if not user32.SetClipboardData(CF_UNICODETEXT, manejador):
            kernel32.GlobalFree(manejador)  # Windows no lo tomó: hay que liberarlo
            return False
        return True
    finally:
        user32.CloseClipboard()


class VigilantePortapapeles:
    """Detecta cuándo alguien copia un texto nuevo.

    Usa el contador de Windows que cambia con cada copia, así detecta también
    cuando se copia dos veces el mismo texto. Lo que ya estaba copiado al
    iniciar se ignora.
    """

    def __init__(self):
        self.secuencia = user32.GetClipboardSequenceNumber()

    def texto_nuevo(self):
        """Devuelve el texto recién copiado, o None si no hay nada nuevo."""
        secuencia = user32.GetClipboardSequenceNumber()
        if secuencia == self.secuencia:
            return None
        leido, texto = _leer()
        if leido:  # si estaba ocupado se reintenta en la próxima revisión
            self.secuencia = secuencia
        return texto

    def copiar(self, texto):
        """Deja un texto en el portapapeles (vacío = lo limpia). Devuelve True si pudo."""
        hecho = _escribir(texto)
        # Lo que escribe el propio programa no cuenta como una copia nueva.
        self.secuencia = user32.GetClipboardSequenceNumber()
        return hecho
