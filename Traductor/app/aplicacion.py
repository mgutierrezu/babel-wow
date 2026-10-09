# -*- coding: utf-8 -*-
"""Une las piezas: portapapeles -> traductor -> ventana e historial.

Recibe las piezas ya construidas, así cualquiera puede reemplazarse (otro motor
de traducción, otra ventana) sin tocar este archivo.
"""

import queue
import threading

from .errores import ErrorTraduccion
from .idioma import es_espanol
from .mensaje import analizar, es_mensaje
from .ventana import COLOR_ERROR, COLOR_ESPERA, COLOR_TEXTO

LISTO = "Funcionando. En WoW, haz clic sobre un mensaje del chat y presiona Ctrl+C."
LARGO_MAXIMO_CHAT = 255  # límite de un mensaje de chat en WoW


class Aplicacion:
    def __init__(self, traductor, ventana, vigilante, historial,
                 intervalo_ms=300, segundos_visible=30, avisos=(), servidor=None, traductor_enviar=None):
        self.traductor = traductor      # objeto con traducir(texto) y revisar(): inglés -> español
        self.traductor_enviar = traductor_enviar  # opcional: español -> inglés, para /twow
        self.servidor = servidor        # opcional: objeto con iniciar() y detener()
        self.servidor_listo = threading.Event()  # las traducciones esperan a que encienda
        self.ventana = ventana
        self.vigilante = vigilante      # objeto con texto_nuevo()
        self.historial = historial
        self.intervalo_ms = intervalo_ms
        self.segundos_visible = segundos_visible
        self.avisos = list(avisos)      # problemas de configuración detectados al leer .env
        self.cola = queue.Queue()       # resultados de los hilos de trabajo
        self.pedido = 0                 # número de la traducción más reciente

        self.ventana.poner_estado("Encendiendo la IA...", "espera")
        threading.Thread(target=self._revision_inicial, daemon=True).start()
        self.ventana.programar(self.intervalo_ms, self._ciclo)

    def iniciar(self):
        self.ventana.iniciar()

    def salir(self):
        """Se llama al cerrar la ventana principal: apaga la IA y termina el programa."""
        if self.servidor:
            try:
                self.servidor.detener()
            except Exception:
                pass
        self.ventana.cerrar()

    def procesar(self, texto):
        """Recibe un texto "[TR] ..." y lanza su traducción en un hilo aparte."""
        mensaje = analizar(texto)
        if not mensaje.texto:
            return
        self.pedido += 1
        if mensaje.para_enviar:
            if not self.traductor_enviar:
                return
            # Se vacía el portapapeles: si el jugador pega antes de tiempo no sale
            # nada, en vez de enviar al chat su texto en español con el prefijo.
            self.vigilante.copiar("")
            self.ventana.mostrar("Traduciendo al inglés...", mensaje.texto, "", COLOR_ESPERA)
            threading.Thread(target=self._trabajo, args=(self.pedido, mensaje), daemon=True).start()
            return
        if es_espanol(mensaje.texto):
            # No hay nada que traducir: se avisa sin llamar al modelo.
            self._mostrar(mensaje, "Ya está en español; no se tradujo.", COLOR_ESPERA, self.segundos_visible)
            return
        self._mostrar(mensaje, "Traduciendo...", COLOR_ESPERA)
        threading.Thread(target=self._trabajo, args=(self.pedido, mensaje), daemon=True).start()

    def _mostrar(self, mensaje, texto, color, segundos=None):
        self.ventana.mostrar(f"{mensaje.remitente}  ·  {mensaje.canal}", mensaje.texto, texto, color, segundos)

    def _entregar(self, mensaje, ingles):
        """Deja la traducción al inglés en el portapapeles y la muestra. El programa
        no la escribe en el juego: la pega el jugador con Ctrl+V."""
        if not self.vigilante.copiar(ingles):
            self.ventana.mostrar("No se pudo copiar: cópiala a mano", mensaje.texto, ingles, COLOR_ERROR, self.segundos_visible)
        elif len(ingles) > LARGO_MAXIMO_CHAT:
            self.ventana.mostrar(f"Copiado, pero tiene {len(ingles)} caracteres: WoW corta en {LARGO_MAXIMO_CHAT}",
                                 mensaje.texto, ingles, COLOR_ERROR, self.segundos_visible)
        else:
            self.ventana.mostrar("Copiado · pégalo en el chat con Ctrl+V", mensaje.texto, ingles, COLOR_TEXTO, self.segundos_visible)

    # --- hilos de trabajo: no tocan la ventana, solo dejan resultados en la cola ---

    def _revision_inicial(self):
        try:
            if self.servidor:
                self.servidor.iniciar()
        except Exception:
            pass  # si no enciende, la revisión de abajo explica qué falta
        finally:
            self.servidor_listo.set()
        try:
            self.traductor.revisar()
        except ErrorTraduccion as error:
            self.cola.put(("estado", "error", str(error)))
        else:
            if self.avisos:
                self.cola.put(("estado", "error", "Funcionando, pero revisa el archivo .env:\n" + "\n".join(self.avisos)))
            else:
                self.cola.put(("estado", "ok", LISTO))

    def _trabajo(self, numero, mensaje):
        self.servidor_listo.wait(40)  # por si se pide una traducción mientras enciende
        traductor = self.traductor_enviar if mensaje.para_enviar else self.traductor
        try:
            traduccion = traductor.traducir(mensaje.texto)
        except ErrorTraduccion as error:
            self.cola.put(("error", numero, mensaje, str(error)))
        except Exception as error:
            self.cola.put(("error", numero, mensaje, f"Error inesperado: {error}"))
        else:
            self.historial.guardar(mensaje.remitente, mensaje.canal, mensaje.texto, traduccion)
            self.cola.put(("ok", numero, mensaje, traduccion))

    # --- ciclo principal, en el hilo de la ventana ---

    def _ciclo(self):
        """Atiende los resultados pendientes y revisa el portapapeles."""
        try:
            while True:
                orden = self.cola.get_nowait()
                if orden[0] == "estado":
                    self.ventana.poner_estado(orden[2], orden[1])
                elif orden[1] == self.pedido:  # se descartan respuestas de pedidos anteriores
                    tipo, _, mensaje, resultado = orden
                    if mensaje.para_enviar and tipo == "ok":
                        self._entregar(mensaje, resultado)
                    else:
                        self._mostrar(mensaje, resultado, COLOR_TEXTO if tipo == "ok" else COLOR_ERROR,
                                      self.segundos_visible)
                    if tipo == "ok" and not self.avisos:
                        self.ventana.poner_estado(LISTO, "ok")  # se recuperó tras un error anterior
        except queue.Empty:
            pass

        texto = self.vigilante.texto_nuevo()
        if es_mensaje(texto):
            self.procesar(texto)
        self.ventana.programar(self.intervalo_ms, self._ciclo)
