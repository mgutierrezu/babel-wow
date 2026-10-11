# -*- coding: utf-8 -*-
"""Configuración del programa, leída desde el archivo .env.

Cada campo de Config corresponde a la variable con el mismo nombre en mayúsculas
(ollama_url -> OLLAMA_URL). Para agregar una opción basta con agregar el campo
aquí y documentarlo en .env.example.
"""

import os
from dataclasses import dataclass, fields

from .rutas import preparar_archivo


@dataclass(frozen=True)
class Config:
    # Conexión con Ollama
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_modelo: str = "gemma3:4b"
    ollama_api_key: str = ""
    ollama_encender_y_apagar: bool = True
    ollama_timeout_segundos: float = 90
    ollama_temperatura: float = 0
    ollama_mantener_modelo: str = "30m"
    # Portapapeles
    portapapeles_intervalo_ms: int = 300
    # Ventana flotante
    ventana_segundos_visible: float = 30
    ventana_opacidad: float = 0.9
    ventana_ancho: int = 440
    ventana_fuente: str = "Segoe UI"
    ventana_tamano_fuente: int = 11
    # Archivos
    prompt_archivo: str = "prompt.txt"
    prompt_enviar_archivo: str = "prompt_en.txt"
    historial_activo: bool = True
    historial_archivo: str = "traducciones.txt"


VERDADERO = {"1", "true", "si", "sí", "yes", "on"}
FALSO = {"0", "false", "no", "off"}


def leer_env(ruta):
    """Lee un archivo .env sencillo (CLAVE=valor) y devuelve un diccionario."""
    valores = {}
    try:
        lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return valores
    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[clave.strip().upper()] = valor
    return valores


def guardar_valor(ruta, clave, valor):
    """Cambia una variable del archivo .env sin tocar el resto (comentarios incluidos)."""
    try:
        lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        lineas = []
    nueva = f"{clave}={valor}"
    for indice, linea in enumerate(lineas):
        if linea.split("=", 1)[0].strip().upper() == clave and not linea.lstrip().startswith("#"):
            lineas[indice] = nueva
            break
    else:
        lineas.append(nueva)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _convertir(texto, tipo):
    if tipo is bool:
        if texto.lower() in VERDADERO:
            return True
        if texto.lower() in FALSO:
            return False
        raise ValueError("se esperaba true o false")
    return tipo(texto)


def cargar_config():
    """Devuelve (Config, lista de avisos). Los valores inválidos se reemplazan
    por el valor por defecto y generan un aviso."""
    # La primera vez se crea .env a partir de .env.example.
    valores = leer_env(preparar_archivo(".env", plantilla=".env.example"))
    datos, avisos = {}, []
    for campo in fields(Config):
        nombre = campo.name.upper()
        texto = os.environ.get(nombre, valores.get(nombre))
        if texto is None or (texto == "" and campo.type is not str):
            continue
        try:
            datos[campo.name] = _convertir(texto, campo.type)
        except ValueError:
            avisos.append(f'{nombre}="{texto}" no es válido en .env; se usó {campo.default}.')
    return Config(**datos), avisos
