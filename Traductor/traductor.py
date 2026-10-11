# -*- coding: utf-8 -*-
"""Traductor WoW: vigila el portapapeles y traduce con Ollama los mensajes
que el addon de WoW deja con el formato "[TR] Nombre (Canal): mensaje".

El programa solo LEE el portapapeles y muestra una ventana propia. No envía
teclas, clics ni texto al juego.

Este archivo es el punto de entrada: lee la configuración, construye cada pieza
y las conecta. La lógica vive en la carpeta app/.
"""

import ctypes

from app.almacen import Estado, Historial
from app.aplicacion import Aplicacion
from app.config import cargar_config, guardar_valor
from app.modelos import MODELOS, buscar
from app.ollama import ClienteOllama
from app.portapapeles import VigilantePortapapeles
from app.prompt import Prompt, pulir
from app.rutas import RECURSOS, preparar_archivo, resolver
from app.servidor import ServidorOllama
from app.ventana import Ventana


def main():
    # Una sola instancia: dos copias mostrarían dos ventanas por cada mensaje.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW(None, False, "TraductorWoW_instancia_unica")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # texto nítido en pantallas con escala
    except Exception:
        pass

    config, avisos = cargar_config()

    historial = Historial(resolver(config.historial_archivo), config.historial_activo)
    conexion = dict(
        url=config.ollama_url,
        modelo=config.ollama_modelo,
        timeout=config.ollama_timeout_segundos,
        temperatura=config.ollama_temperatura,
        mantener_modelo=config.ollama_mantener_modelo,
        api_key=config.ollama_api_key,
    )
    # Dos traductores sobre el mismo modelo, cada uno con su archivo de instrucciones:
    # inglés -> español para leer el chat, y español -> inglés para escribir (/twow).
    prompt = Prompt(preparar_archivo(config.prompt_archivo, plantilla="prompt.txt"))
    prompt_enviar = Prompt(preparar_archivo(config.prompt_enviar_archivo, plantilla="prompt_en.txt"))
    traductor = ClienteOllama(armar_mensajes=prompt.mensajes, pulir=pulir, **conexion)
    traductor_enviar = ClienteOllama(armar_mensajes=prompt_enviar.mensajes, **conexion)

    # Modelos que se pueden elegir en la ventana. Si el .env trae uno que no está
    # en la lista (puesto a mano), se agrega para no perderlo.
    opciones = [(m.nombre, m.titulo, m.etiqueta, m.descripcion) for m in MODELOS]
    if not buscar(config.ollama_modelo):
        opciones.append((config.ollama_modelo, config.ollama_modelo, config.ollama_modelo,
                         "Modelo configurado a mano en el archivo .env."))

    # Cerrar la ventana principal es salir: por eso la ventana necesita a la aplicación.
    aplicacion = None
    ventana = Ventana(
        estado=Estado(resolver("estado.json")),
        ancho=config.ventana_ancho,
        opacidad=config.ventana_opacidad,
        fuente=config.ventana_fuente,
        tamano_fuente=config.ventana_tamano_fuente,
        al_salir=lambda: aplicacion.salir(),
        al_abrir_historial=historial.abrir,
        icono=RECURSOS / "icono.ico",
    )
    aplicacion = Aplicacion(
        traductor=traductor,
        traductor_enviar=traductor_enviar,
        ventana=ventana,
        vigilante=VigilantePortapapeles(),
        historial=historial,
        intervalo_ms=config.portapapeles_intervalo_ms,
        segundos_visible=config.ventana_segundos_visible,
        avisos=avisos,
        servidor=ServidorOllama(config.ollama_url, gestionar=config.ollama_encender_y_apagar),
        modelos=opciones,
        al_cambiar_modelo=lambda nombre: guardar_valor(resolver(".env"), "OLLAMA_MODELO", nombre),
    )
    aplicacion.iniciar()


if __name__ == "__main__":
    main()
