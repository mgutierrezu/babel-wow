# -*- coding: utf-8 -*-
"""Cliente de Ollama. No sabe nada de ventanas ni de archivos.

Cualquier otro motor de traducción puede reemplazarlo si ofrece los mismos dos
métodos: traducir(texto) y revisar(), y lanza ErrorTraduccion al fallar.
"""

import json
import socket
import urllib.error
import urllib.request

from .errores import ErrorTraduccion


class ClienteOllama:
    def __init__(self, url, modelo, armar_mensajes, pulir=None, timeout=90, temperatura=0,
                 mantener_modelo="30m", api_key="", max_tokens=200):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.armar_mensajes = armar_mensajes  # función: texto -> mensajes para /api/chat
        self.pulir = pulir                    # función opcional: (original, traducción) -> traducción
        self.timeout = timeout
        self.max_tokens = max_tokens    # tope de la respuesta: un mensaje de chat es corto
        self.temperatura = temperatura
        self.mantener_modelo = mantener_modelo
        self.cabeceras = {"Content-Type": "application/json"}
        if api_key:
            self.cabeceras["Authorization"] = f"Bearer {api_key}"
        # Sin proxy: un proxy del sistema solo estorbaría para una dirección local.
        self.abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def traducir(self, texto):
        """Envía el texto a /api/chat (sin streaming) y devuelve la traducción."""
        respuesta = self._pedir("/api/chat", {
            "model": self.modelo,
            "stream": False,
            "keep_alive": self.mantener_modelo,
            "options": {"temperature": self.temperatura, "num_predict": self.max_tokens},
            "messages": self.armar_mensajes(texto),
        })
        traduccion = (respuesta.get("message") or {}).get("content", "")
        traduccion = " ".join(traduccion.split()).strip('"').strip()  # siempre en una sola línea
        if self.pulir:
            traduccion = self.pulir(texto, traduccion)
        if not traduccion:
            raise ErrorTraduccion("Ollama devolvió una respuesta vacía.")
        return traduccion

    def revisar(self):
        """Lanza ErrorTraduccion si Ollama no está corriendo o falta el modelo."""
        respuesta = self._pedir("/api/tags", timeout=5)
        nombres = [m.get("name", "") for m in respuesta.get("models", [])]
        if not any(n in (self.modelo, self.modelo + ":latest") or n.split(":")[0] == self.modelo
                   for n in nombres):
            raise self._error_modelo()

    def _error_modelo(self):
        return ErrorTraduccion(
            f'El modelo "{self.modelo}" no está descargado. '
            f"Abre una terminal y ejecuta: ollama pull {self.modelo}"
        )

    def _pedir(self, ruta, cuerpo=None, timeout=None):
        """Hace una petición y convierte las fallas en errores claros."""
        timeout = timeout or self.timeout
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        peticion = urllib.request.Request(self.url + ruta, data=datos, headers=self.cabeceras)
        error_timeout = ErrorTraduccion(
            f"Ollama no respondió en {timeout:g} segundos. La primera traducción demora más "
            "porque carga el modelo; intenta de nuevo o sube OLLAMA_TIMEOUT_SEGUNDOS en .env."
        )
        try:
            with self.abridor.open(peticion, timeout=timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detalle = json.loads(error.read().decode("utf-8")).get("error", "")
            except Exception:
                detalle = ""
            if error.code in (401, 403):
                raise ErrorTraduccion("Ollama rechazó la conexión. Revisa OLLAMA_API_KEY en .env.") from None
            if error.code == 404 or "not found" in detalle.lower():
                raise self._error_modelo() from None
            raise ErrorTraduccion(f"Ollama respondió con el error {error.code}: {detalle or error.reason}") from None
        except urllib.error.URLError as error:
            if isinstance(error.reason, (socket.timeout, TimeoutError)):
                raise error_timeout from None
            raise ErrorTraduccion(
                f"No se pudo conectar con Ollama en {self.url}. "
                "Cierra Traductor WoW y vuelve a abrirlo; si sigue igual, revisa que Ollama esté instalado."
            ) from None
        except (socket.timeout, TimeoutError):
            raise error_timeout from None
        except (OSError, ValueError) as error:
            raise ErrorTraduccion(f"Respuesta inesperada de Ollama: {error}") from None
