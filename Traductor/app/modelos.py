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
    titulo: str        # nivel: Alto, Medio o Bajo
    video_gb: float    # memoria de video que ocupa mientras el programa está abierto
    descarga_gb: float
    descripcion: str
    recomendado: bool = False

    @property
    def nivel(self):
        """Título para mostrar en listas: marca cuál es el recomendado."""
        return self.titulo + (" (recomendado)" if self.recomendado else "")

    @property
    def etiqueta(self):
        return f"{self.nivel}  ·  {self.nombre}  ·  {numero(self.video_gb)} GB de video"


def numero(valor):
    """Número con coma decimal, como se escribe en español."""
    return f"{valor:g}".replace(".", ",")


# En este orden se muestran, en el instalador y en la ventana: de mayor a menor consumo.
MODELOS = (
    Modelo("gemma3:4b", "Alto", 3.9, 3.3,
           "Las traducciones más naturales, a cambio de más memoria. Para tarjetas de video de 8 GB o más."),
    Modelo("qwen2.5:3b", "Medio", 2.4, 1.9,
           "Buen equilibrio entre calidad y memoria. Para tarjetas de 6 GB o más.", recomendado=True),
    Modelo("qwen2.5:1.5b", "Bajo", 1.3, 1.0,
           "Traducciones más toscas, pero se entienden. Para tarjetas de 4 GB, o si el juego va lento."),
)

RECOMENDADO = next(modelo for modelo in MODELOS if modelo.recomendado)
LIVIANO = MODELOS[-1]


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
    """Modelo adecuado para una tarjeta con esa memoria (compartida con el juego).
    El nivel Alto no se sugiere nunca: lo elige quien quiera gastar más memoria."""
    return LIVIANO if video_gb is not None and video_gb < 5.5 else RECOMENDADO
