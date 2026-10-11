# -*- coding: utf-8 -*-
"""Modelos de traducción que se ofrecen al usuario, en el instalador y en el programa.

Las cifras de memoria de video se midieron con el prompt del proyecto en una
RTX 5070. La calidad se comparó con 32 mensajes de chat en ambos sentidos.
"""

import subprocess
from dataclasses import dataclass

SIN_VENTANA = 0x08000000


@dataclass(frozen=True)
class Modelo:
    nombre: str        # nombre en Ollama
    titulo: str
    video_gb: float    # memoria de video que ocupa mientras el programa está abierto
    descarga_gb: float
    descripcion: str

    @property
    def etiqueta(self):
        return f"{self.titulo}  ·  {self.nombre}  ·  {numero(self.video_gb)} GB de video"


def numero(valor):
    """Número con coma decimal, como se escribe en español."""
    return f"{valor:g}".replace(".", ",")


MODELOS = (
    Modelo("gemma3:4b", "Recomendado", 3.9, 3.3,
           "La mejor calidad de traducción. Para tarjetas de video de 8 GB o más."),
    Modelo("qwen2.5:3b", "Intermedio", 2.4, 1.9,
           "Calidad cercana a la recomendada usando menos memoria. Para tarjetas de 6 GB."),
    Modelo("qwen2.5:1.5b", "Liviano", 1.3, 1.0,
           "Traducciones más toscas, pero se entienden. Para tarjetas de 4 GB, o si el juego va lento."),
)


def buscar(nombre):
    """Devuelve el Modelo con ese nombre, o None si el usuario configuró otro."""
    return next((modelo for modelo in MODELOS if modelo.nombre == nombre), None)


def memoria_de_video():
    """Memoria total de la tarjeta de video en GB, o None si no se puede saber.
    Solo se detectan tarjetas NVIDIA; con otras se ofrece el modelo recomendado."""
    try:
        salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=10, creationflags=SIN_VENTANA).stdout
        return max(int(linea) for linea in salida.split()) / 1024
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def sugerir(video_gb):
    """Modelo adecuado para una tarjeta con esa memoria (compartida con el juego)."""
    if video_gb is None or video_gb >= 7.5:
        return MODELOS[0]
    return MODELOS[1] if video_gb >= 5.5 else MODELOS[2]
