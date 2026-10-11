# -*- coding: utf-8 -*-
"""Une las piezas: portapapeles -> traductor -> ventana e historial.

Recibe las piezas ya construidas, así cualquiera puede reemplazarse (otro motor
de traducción, otra ventana) sin tocar este archivo.
"""

import queue
import threading
import time

from .errores import ErrorTraduccion
from .idioma import es_espanol
from .mensaje import analizar, es_mensaje
from .ventana import COLOR_ERROR, COLOR_ESPERA, COLOR_TEXTO

SEGUNDOS_CAMBIO = 2.5           # duración mínima de la animación al cambiar de modelo
SEGUNDOS_ENTRE_REVISIONES = 10  # cada cuánto se confirma que la IA sigue encendida
LARGO_MAXIMO_CHAT = 255  # límite de un mensaje de chat en WoW


class Aplicacion:
    def __init__(self, traductor, ventana, vigilante, historial,
                 intervalo_ms=300, segundos_visible=30, avisos=(), servidor=None, traductor_enviar=None,
                 modelos=(), al_cambiar_modelo=None):
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
        self.al_cambiar_modelo = al_cambiar_modelo  # función(nombre) para recordar la elección
        self.cerrando = threading.Event()  # detiene la vigilancia de la IA al salir

        self.cambio = None              # datos del cambio de modelo en curso, si lo hay

        # modelos: lista de (nombre, título, etiqueta, descripción) que el usuario puede elegir.
        self.titulos = {nombre: titulo for nombre, titulo, _, _ in modelos}
        if modelos:
            opciones = [(nombre, etiqueta, descripcion) for nombre, _, etiqueta, descripcion in modelos]
            self.ventana.poner_opciones(opciones, self.traductor.modelo, self.cambiar_modelo)
            self.ventana.bloquear_opciones(True)  # hasta que termine la revisión inicial
        self.ventana.poner_estado("Encendiendo la IA...", "espera")
        threading.Thread(target=self._revision_inicial, daemon=True).start()
        self.ventana.programar(self.intervalo_ms, self._ciclo)

    def iniciar(self):
        self.ventana.iniciar()

    def salir(self):
        """Se llama al cerrar la ventana principal: apaga la IA y termina el programa."""
        self.cerrando.set()
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
            self._asegurar_modelo()
            self._cargar_modelo()
        except ErrorTraduccion as error:
            self.cola.put(("estado", "error", str(error)))
        else:
            self._avisar_listo()
        self.cola.put(("modelo", self.traductor.modelo if hasattr(self.traductor, "modelo") else None))
        self._vigilar()

    def _vigilar(self):
        """Mantiene honesto el indicador verde: si la IA deja de responder se avisa,
        y si vuelve, también. Corre hasta que se cierra el programa."""
        responde = getattr(self.servidor, "responde", None)
        if responde is None:
            return
        viva = True
        while not self.cerrando.wait(SEGUNDOS_ENTRE_REVISIONES):
            if not self.servidor_listo.is_set():
                continue  # hay un cambio de modelo en curso: ya se está informando
            ahora = bool(responde())
            if ahora != viva:
                viva = ahora
                if viva:
                    self._avisar_listo()
                else:
                    self.cola.put(("estado", "error", "La IA dejó de responder. Cierra Traductor WoW y vuelve a abrirlo."))

    def _estado_listo(self):
        """Devuelve (tipo, texto) para mostrar cuando la IA quedó funcionando."""
        if self.avisos:
            return "error", "Funcionando, pero revisa el archivo .env:\n" + "\n".join(self.avisos)
        titulo = self.titulos.get(getattr(self.traductor, "modelo", None))
        return "ok", (f"LLM ({titulo}) funcionando" if titulo else "LLM funcionando") + ", puedes minimizar esta pantalla."

    def _avisar_listo(self):
        self.cola.put(("estado", *self._estado_listo()))

    def _cargar_modelo(self):
        """Deja el modelo en memoria, para que "funcionando" sea cierto y la
        primera traducción no tenga que esperar la carga."""
        cargar = getattr(self.traductor, "cargar", None)
        if cargar:
            cargar()

    def _asegurar_modelo(self):
        """Comprueba que el modelo esté en el equipo; si falta, lo descarga mostrando el avance."""
        descargado = getattr(self.traductor, "descargado", None)
        if descargado is None:  # un traductor sin modelos descargables
            self.traductor.revisar()
            return
        if descargado():
            return
        nombre, ultimo = self.traductor.modelo, [-1]

        def progreso(fraccion):
            porcentaje = int(fraccion * 100)
            if porcentaje != ultimo[0]:  # un aviso por cada 1 %, no uno por cada trozo
                ultimo[0] = porcentaje
                self.cola.put(("estado", "espera", f"Descargando el modelo {nombre}: {porcentaje} %"))

        self.cola.put(("estado", "espera", f"Descargando el modelo {nombre}..."))
        if self.cambio:
            self.cambio["descargando"] = True  # manda el avance real, no la animación
        try:
            self.traductor.descargar(progreso)
        finally:
            if self.cambio:
                self.cambio["descargando"] = False

    def cambiar_modelo(self, nombre):
        """El usuario eligió otro modelo en la ventana. Se aplica en un hilo aparte."""
        if nombre == self.traductor.modelo or self.cambio:
            return
        self.servidor_listo.clear()  # las traducciones esperan a que termine el cambio
        self.ventana.bloquear_opciones(True)
        self.cambio = {"inicio": time.time(), "titulo": self.titulos.get(nombre, nombre), "fin": None, "descargando": False}
        threading.Thread(target=self._cambiar_modelo, args=(nombre,), daemon=True).start()
        self._animar_cambio()

    def _cambiar_modelo(self, nombre):
        traductores = [t for t in (self.traductor, self.traductor_enviar) if t]
        anterior = self.traductor.modelo
        try:
            for traductor in traductores:
                traductor.modelo = nombre
            self._asegurar_modelo()
            self.traductor.soltar(anterior)  # libera la memoria de video del modelo anterior
            self._cargar_modelo()
            if self.al_cambiar_modelo:
                self.al_cambiar_modelo(nombre)
            fin = ("ok", "")
        except Exception as error:
            for traductor in traductores:  # se vuelve al modelo que sí funcionaba
                traductor.modelo = anterior
            fin = ("error", f"No se pudo cambiar de modelo: {error}")
        self.servidor_listo.set()
        self.cambio["fin"] = fin  # lo recoge _animar_cambio, en el hilo de la ventana

    def _animar_cambio(self):
        """Muestra el avance del cambio de modelo. El porcentaje es una animación:
        sube durante SEGUNDOS_CAMBIO y se queda en 99 % si la carga real tarda más."""
        cambio = self.cambio
        transcurrido = time.time() - cambio["inicio"]
        termino = cambio["fin"] is not None
        if not termino or (cambio["fin"][0] == "ok" and transcurrido < SEGUNDOS_CAMBIO):
            if not cambio["descargando"]:
                porcentaje = min(100 if termino else 99, int(transcurrido / SEGUNDOS_CAMBIO * 100))
                self.ventana.poner_estado(f"Cambiando a {cambio['titulo']}... {porcentaje} %", "espera")
            self.ventana.programar(60, self._animar_cambio)
            return
        if cambio["fin"][0] == "ok":
            # Se deja ver el 100 % un instante antes del mensaje final.
            self.ventana.poner_estado(f"Cambiando a {cambio['titulo']}... 100 %", "espera")
            self.ventana.programar(450, self._terminar_cambio)
        else:
            self._terminar_cambio()

    def _terminar_cambio(self):
        cambio, self.cambio = self.cambio, None
        tipo, texto = cambio["fin"]
        if tipo == "ok":
            tipo, texto = self._estado_listo()
        self.ventana.poner_estado(texto, tipo)
        self.ventana.elegir_opcion(self.traductor.modelo)  # si falló, vuelve a marcar el anterior
        self.ventana.bloquear_opciones(False)

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
                    # Durante un cambio de modelo solo pasa el avance real de una descarga.
                    if not self.cambio or self.cambio["descargando"]:
                        self.ventana.poner_estado(orden[2], orden[1])
                elif orden[0] == "modelo":  # terminó la revisión o un cambio: se refleja el modelo en uso
                    if orden[1]:
                        self.ventana.elegir_opcion(orden[1])
                    self.ventana.bloquear_opciones(False)
                elif orden[1] == self.pedido:  # se descartan respuestas de pedidos anteriores
                    tipo, _, mensaje, resultado = orden
                    if mensaje.para_enviar and tipo == "ok":
                        self._entregar(mensaje, resultado)
                    else:
                        self._mostrar(mensaje, resultado, COLOR_TEXTO if tipo == "ok" else COLOR_ERROR,
                                      self.segundos_visible)
                    if tipo == "ok" and not self.cambio:
                        self.ventana.poner_estado(*reversed(self._estado_listo()))  # se recuperó tras un error anterior
        except queue.Empty:
            pass

        texto = self.vigilante.texto_nuevo()
        if es_mensaje(texto):
            self.procesar(texto)
        self.ventana.programar(self.intervalo_ms, self._ciclo)
