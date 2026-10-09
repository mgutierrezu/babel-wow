# -*- coding: utf-8 -*-
"""Enciende Ollama al abrir el programa y lo apaga al salir.

Se lanza "ollama serve" oculto (sin el icono de la bandeja) dentro de un "job"
de Windows: si este programa termina, por la vía que sea, Windows cierra Ollama
y el modelo que tenga cargado, y se libera la memoria de video.

Solo se apaga el Ollama que este programa encendió. Si ya estaba abierto (por
ejemplo, porque el usuario lo usa para otra cosa), se usa y no se toca.
"""

import ctypes
import os
import shutil
import subprocess
import time
import urllib.request
from ctypes import wintypes
from pathlib import Path

SIN_VENTANA = 0x08000000
INFO_LIMITES_EXTENDIDA = 9          # JobObjectExtendedLimitInformation
CERRAR_AL_CERRAR_JOB = 0x00002000   # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE


class _LimitesBasicos(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _LimitesExtendidos(ctypes.Structure):
    _fields_ = [("Basicos", _LimitesBasicos), ("Contadores", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateJobObjectW.restype = wintypes.HANDLE
kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def buscar_ollama():
    """Devuelve la ruta de ollama.exe, o None si no está instalado."""
    candidatas = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                  Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe"]
    en_path = shutil.which("ollama")
    if en_path:
        candidatas.insert(0, Path(en_path))
    return next((ruta for ruta in candidatas if ruta.is_file()), None)


class ServidorOllama:
    def __init__(self, url, gestionar=True):
        self.url = url.rstrip("/")
        # Solo tiene sentido encender un Ollama que corre en este mismo equipo.
        self.gestionar = gestionar and any(local in self.url for local in ("127.0.0.1", "localhost"))
        self.proceso = None
        self.job = None

    def responde(self):
        try:
            abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with abridor.open(self.url + "/api/version", timeout=2):
                return True
        except (OSError, ValueError):
            return False

    def iniciar(self, espera=30):
        """Enciende Ollama si hace falta y espera a que responda. Devuelve True si quedó listo."""
        if not self.gestionar or self.responde():
            return True
        ejecutable = buscar_ollama()
        if not ejecutable:
            return False
        self.proceso = subprocess.Popen([str(ejecutable), "serve"], creationflags=SIN_VENTANA,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._atar_al_programa()
        limite = time.time() + espera
        while time.time() < limite:
            if self.responde():
                return True
            if self.proceso.poll() is not None:  # se cerró solo: no va a responder
                return False
            time.sleep(0.3)
        return False

    def _atar_al_programa(self):
        """Mete a Ollama en un job que Windows cierra cuando este programa termina."""
        try:
            job = kernel32.CreateJobObjectW(None, None)
            limites = _LimitesExtendidos()
            limites.Basicos.LimitFlags = CERRAR_AL_CERRAR_JOB
            if (job and kernel32.SetInformationJobObject(job, INFO_LIMITES_EXTENDIDA, ctypes.byref(limites), ctypes.sizeof(limites))
                    and kernel32.AssignProcessToJobObject(job, int(self.proceso._handle))):
                self.job = job
        except Exception:
            self.job = None  # sin job igual se apaga en detener()

    def detener(self):
        """Apaga el Ollama que encendió este programa, junto con el modelo cargado."""
        if not self.proceso:
            return
        if self.job:
            kernel32.TerminateJobObject(self.job, 0)
            kernel32.CloseHandle(self.job)
            self.job = None
        elif self.proceso.poll() is None:
            # Respaldo: /T cierra también el proceso que tiene cargado el modelo.
            subprocess.run(["taskkill", "/PID", str(self.proceso.pid), "/T", "/F"],
                           capture_output=True, creationflags=SIN_VENTANA)
        self.proceso = None
