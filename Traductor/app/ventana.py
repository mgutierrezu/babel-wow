# -*- coding: utf-8 -*-
"""Ventanas del programa. No saben de Ollama ni del portapapeles.

Hay dos:
- la principal, una ventana normal que aparece en la barra de tareas. Mientras
  esté abierta (o minimizada) el programa funciona; al cerrarla se apaga todo.
- la flotante, que muestra cada traducción encima del juego.
"""

import ctypes
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk

COLOR_FONDO = "#14161c"
COLOR_TITULO = "#f2c94c"
COLOR_ORIGINAL = "#9aa0aa"
COLOR_TEXTO = "#ffffff"
COLOR_ESPERA = "#7fb4ff"
COLOR_ERROR = "#ff7b72"
COLOR_OK = "#4ade80"
COLOR_BOTON = "#2a2e38"

# Estados de la ventana principal: color del punto indicador.
ESTADOS = {"espera": COLOR_TITULO, "ok": COLOR_OK, "error": COLOR_ERROR}

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
_leer_estilo = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
_fijar_estilo = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
_leer_estilo.argtypes = [wintypes.HWND, ctypes.c_int]
_leer_estilo.restype = ctypes.c_ssize_t
_fijar_estilo.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_fijar_estilo.restype = ctypes.c_ssize_t


class Indicador(tk.Canvas):
    """Circulito de estado de la ventana principal.

    "ok" es un visto bueno verde (la IA está encendida), "espera" gira en amarillo
    (encendiendo, descargando o cambiando de modelo) y "error" queda fijo en rojo.
    """

    def __init__(self, padre, lado):
        super().__init__(padre, width=lado, height=lado, bg=COLOR_FONDO, highlightthickness=0)
        self.lado, self.tipo, self.angulo, self.tarea = lado, "espera", 90, None
        self._dibujar()

    def poner(self, tipo):
        self.tipo = tipo if tipo in ESTADOS else "ok"
        self._dibujar()

    def _dibujar(self):
        if self.tarea:
            self.after_cancel(self.tarea)
            self.tarea = None
        self.delete("all")
        color, borde, centro = ESTADOS[self.tipo], self.lado * 0.16, self.lado / 2
        a, b = borde, self.lado - borde
        if self.tipo != "espera":
            self.create_oval(a, a, b, b, fill=color, outline="")
            if self.tipo == "ok":  # visto bueno
                m = self.lado
                self.create_line(m * .30, m * .52, m * .44, m * .66, m * .71, m * .36, fill=COLOR_FONDO,
                                 width=max(2, round(m * 0.12)), capstyle="round", joinstyle="round")
            return
        grosor = max(2, round(self.lado * 0.14))
        self.create_oval(a, a, b, b, outline=COLOR_BOTON, width=grosor)
        self.create_arc(a, a, b, b, start=self.angulo, extent=110, style="arc", outline=color, width=grosor)
        radio = self.lado * 0.14
        self.create_oval(centro - radio, centro - radio, centro + radio, centro + radio, fill=color, outline="")
        self.angulo = (self.angulo - 18) % 360
        self.tarea = self.after(50, self._dibujar)


class Ventana:
    """estado: objeto con leer() y guardar(dict) para recordar la posición de la flotante.
    al_salir: función que se llama al cerrar la ventana principal.
    al_abrir_historial: función del botón "Abrir historial".
    """

    def __init__(self, estado, ancho=440, opacidad=0.9, fuente="Segoe UI", tamano_fuente=11,
                 al_salir=None, al_abrir_historial=None, icono=None):
        self.estado = estado
        self.posicion = estado.leer()
        self.temporizador = None
        self.arrastre = None
        self.al_salir = al_salir

        self.root = tk.Tk()
        self.escala = self.root.winfo_fpixels("1i") / 96.0
        if icono:
            try:
                self.root.iconbitmap(default=str(icono))
            except tk.TclError:
                pass
        self._crear_principal(fuente, al_abrir_historial)
        self._crear_flotante(ancho, opacidad, fuente, tamano_fuente, al_abrir_historial)

    # --- ventana principal (barra de tareas) ---

    def _crear_principal(self, fuente, al_abrir_historial):
        root, e = self.root, self.escala
        root.title("Traductor WoW")
        root.configure(bg=COLOR_FONDO)
        root.resizable(False, False)
        # Cerrar esta ventana es salir del programa.
        root.protocol("WM_DELETE_WINDOW", self.al_salir or root.destroy)

        marco = tk.Frame(root, bg=COLOR_FONDO, padx=int(20 * e), pady=int(16 * e))
        marco.pack()
        ancho = int(360 * e)
        tk.Frame(marco, bg=COLOR_FONDO, width=ancho, height=1).pack()
        comunes = dict(bg=COLOR_FONDO, anchor="w", justify="left", wraplength=ancho)
        tk.Label(marco, text="Traductor WoW", fg=COLOR_TITULO, font=(fuente, 14, "bold"), **comunes).pack(fill="x")

        fila = tk.Frame(marco, bg=COLOR_FONDO)
        fila.pack(fill="x", pady=(int(8 * e), int(10 * e)))
        self.indicador = Indicador(fila, int(20 * e))
        self.indicador.pack(side="left", anchor="n", pady=(int(1 * e), 0))
        self.lbl_estado = tk.Label(fila, fg=COLOR_TEXTO, font=(fuente, 10), bg=COLOR_FONDO, anchor="w",
                                   justify="left", wraplength=ancho - int(26 * e))
        self.lbl_estado.pack(side="left", fill="x", padx=(int(8 * e), 0))

        tk.Label(marco, fg=COLOR_ORIGINAL, font=(fuente, 9), **comunes,
                 text="En WoW, haz clic sobre un mensaje del chat y presiona Ctrl+C. "
                      "Al cerrar esta ventana se apagan el traductor y la IA.").pack(fill="x")

        # Selector de modelo. Se llena con poner_opciones(); hasta entonces no se muestra.
        self.marco_opciones = tk.Frame(marco, bg=COLOR_FONDO)
        tk.Label(self.marco_opciones, text="Modelo de traducción", fg=COLOR_TEXTO, font=(fuente, 9, "bold"),
                 **comunes).pack(fill="x", pady=(int(12 * e), int(3 * e)))
        self.selector = ttk.Combobox(self.marco_opciones, state="readonly", font=(fuente, 9))
        self.selector.pack(fill="x")
        self.selector.bind("<<ComboboxSelected>>", self._al_elegir_opcion)
        self.lbl_opcion = tk.Label(self.marco_opciones, fg=COLOR_ORIGINAL, font=(fuente, 9), **comunes)
        self.lbl_opcion.pack(fill="x", pady=(int(3 * e), 0))
        self.opciones, self.al_elegir = [], None

        botones = self.marco_botones = tk.Frame(marco, bg=COLOR_FONDO)
        botones.pack(fill="x", pady=(int(14 * e), 0))
        estilo = dict(bg=COLOR_BOTON, fg=COLOR_TEXTO, activebackground="#3a3f4b", activeforeground=COLOR_TEXTO,
                      relief="flat", bd=0, font=(fuente, 9), padx=int(12 * e), pady=int(5 * e), cursor="hand2")
        if al_abrir_historial:
            tk.Button(botones, text="Abrir historial", command=al_abrir_historial, **estilo).pack(side="left")
        tk.Button(botones, text="Cerrar todo", command=self.al_salir or root.destroy, **estilo).pack(side="right")

    def poner_estado(self, texto, tipo="ok"):
        """Muestra en la ventana principal cómo está el programa: "espera", "ok" o "error"."""
        self.indicador.poner(tipo)
        self.lbl_estado.config(text=texto)

    def poner_opciones(self, opciones, actual, al_elegir):
        """Muestra el selector. opciones: lista de (clave, etiqueta, descripción);
        al_elegir(clave) se llama cuando el usuario escoge otra."""
        self.opciones, self.al_elegir = list(opciones), al_elegir
        self.selector.config(values=[etiqueta for _, etiqueta, _ in self.opciones])
        self.marco_opciones.pack(fill="x", before=self.marco_botones)
        self.elegir_opcion(actual)

    def elegir_opcion(self, clave):
        """Deja seleccionada una opción sin avisar a nadie (por ejemplo, al deshacer un cambio)."""
        for indice, (una, _, descripcion) in enumerate(self.opciones):
            if una == clave:
                self.selector.current(indice)
                self.lbl_opcion.config(text=descripcion)

    def bloquear_opciones(self, bloquear):
        """Impide cambiar de opción mientras se aplica un cambio anterior."""
        self.selector.config(state="disabled" if bloquear else "readonly")

    def _al_elegir_opcion(self, _evento):
        clave, _, descripcion = self.opciones[self.selector.current()]
        self.lbl_opcion.config(text=descripcion)
        self.selector.selection_clear()
        if self.al_elegir:
            self.al_elegir(clave)

    # --- ventana flotante (traducciones) ---

    def _crear_flotante(self, ancho, opacidad, fuente, tamano_fuente, al_abrir_historial):
        e = self.escala
        self.flotante = tk.Toplevel(self.root)
        self.flotante.withdraw()
        self.flotante.overrideredirect(True)               # sin bordes ni botón en la barra de tareas
        self.flotante.attributes("-topmost", True)         # siempre encima
        self.flotante.attributes("-alpha", opacidad)
        self.flotante.configure(bg=COLOR_FONDO)

        ancho = int(ancho * e)
        margen = int(12 * e)
        self.separacion = (0, int(3 * e))
        marco = tk.Frame(self.flotante, bg=COLOR_FONDO, padx=margen, pady=int(10 * e))
        marco.pack()
        tk.Frame(marco, bg=COLOR_FONDO, width=ancho - 2 * margen, height=1).pack()  # fija el ancho
        comunes = dict(bg=COLOR_FONDO, anchor="w", justify="left", wraplength=ancho - 2 * margen)
        self.lbl_titulo = tk.Label(marco, fg=COLOR_TITULO, font=(fuente, tamano_fuente - 1, "bold"), **comunes)
        self.lbl_original = tk.Label(marco, fg=COLOR_ORIGINAL, font=(fuente, tamano_fuente - 1), **comunes)
        self.lbl_texto = tk.Label(marco, fg=COLOR_TEXTO, font=(fuente, tamano_fuente + 1), **comunes)
        for etiqueta in (self.lbl_titulo, self.lbl_original, self.lbl_texto):
            etiqueta.pack(fill="x", pady=self.separacion)

        # Botón "x" en la esquina. No necesita comando propio: un clic sin
        # arrastrar sobre cualquier parte de la flotante ya la oculta.
        self.btn_cerrar = tk.Label(self.flotante, text="✕", bg=COLOR_FONDO, fg=COLOR_ORIGINAL,
                                   font=(fuente, tamano_fuente), cursor="hand2", padx=int(4 * e))
        self.btn_cerrar.place(relx=1.0, x=-int(4 * e), y=int(4 * e), anchor="ne")
        self.btn_cerrar.bind("<Enter>", lambda _: self.btn_cerrar.config(fg=COLOR_ERROR))
        self.btn_cerrar.bind("<Leave>", lambda _: self.btn_cerrar.config(fg=COLOR_ORIGINAL))

        self.menu = tk.Menu(self.flotante, tearoff=0)
        if al_abrir_historial:
            self.menu.add_command(label="Abrir historial", command=al_abrir_historial)
        self.menu.add_command(label="Ocultar", command=self.ocultar)
        self.menu.add_command(label="Cancelar")

        # Los eventos de los hijos llegan también a su ventana, así que basta
        # con enlazarlos aquí; la ventana principal no se ve afectada.
        self.flotante.bind("<ButtonPress-1>", self._presionar)
        self.flotante.bind("<B1-Motion>", self._arrastrar)
        self.flotante.bind("<ButtonRelease-1>", self._soltar)
        self.flotante.bind("<Button-3>", lambda ev: self.menu.tk_popup(ev.x_root, ev.y_root))
        self._colocar()

    # --- ciclo de vida ---

    def iniciar(self):
        self.root.mainloop()

    def cerrar(self):
        self.root.destroy()

    def programar(self, milisegundos, funcion):
        """Ejecuta una función más tarde, en el hilo de la ventana."""
        return self.root.after(milisegundos, funcion)

    # --- mostrar y ocultar la flotante ---

    def mostrar(self, titulo, original, texto, color=COLOR_TEXTO, segundos=None):
        """Actualiza y muestra la flotante. Con segundos=None se queda visible."""
        self._cancelar_temporizador()
        self.lbl_titulo.config(text=titulo)
        self.lbl_original.config(text=original)
        self.lbl_texto.config(text=texto, fg=color)
        if original:
            self.lbl_original.pack(fill="x", pady=self.separacion, before=self.lbl_texto)
        else:
            self.lbl_original.pack_forget()
        self.flotante.update_idletasks()
        self._no_robar_foco()
        self.flotante.deiconify()
        self.flotante.attributes("-topmost", True)
        if segundos:
            self.temporizador = self.root.after(int(segundos * 1000), self.ocultar)

    def ocultar(self):
        self._cancelar_temporizador()
        self.flotante.withdraw()

    def _cancelar_temporizador(self):
        if self.temporizador:
            self.root.after_cancel(self.temporizador)
            self.temporizador = None

    # --- posición y estilo de la flotante ---

    def _colocar(self):
        """Usa la posición guardada si sigue dentro de alguna pantalla."""
        izq, arriba = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
        ancho, alto = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
        x, y = self.posicion.get("x"), self.posicion.get("y")
        dentro = (isinstance(x, int) and isinstance(y, int)
                  and izq <= x <= izq + ancho - 100 and arriba <= y <= arriba + alto - 50)
        if not dentro:
            x = (self.flotante.winfo_screenwidth() - self.flotante.winfo_reqwidth()) // 2
            y = int(self.flotante.winfo_screenheight() * 0.12)
        self.flotante.geometry(f"+{x}+{y}")

    def _no_robar_foco(self):
        """Evita que la flotante le quite el teclado al juego al aparecer o al hacerle clic."""
        try:
            hwnd = user32.GetAncestor(self.flotante.winfo_id(), 2)
            estilo = _leer_estilo(hwnd, GWL_EXSTYLE)
            _fijar_estilo(hwnd, GWL_EXSTYLE, estilo | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        except Exception:
            pass

    # --- arrastrar la flotante con el mouse; un clic sin mover la oculta ---

    def _presionar(self, evento):
        self.arrastre = (evento.x_root, evento.y_root, self.flotante.winfo_x(), self.flotante.winfo_y(), False)

    def _arrastrar(self, evento):
        if not self.arrastre:
            return
        x0, y0, vx, vy, movio = self.arrastre
        dx, dy = evento.x_root - x0, evento.y_root - y0
        if movio or abs(dx) > 3 or abs(dy) > 3:
            self.arrastre = (x0, y0, vx, vy, True)
            self.flotante.geometry(f"+{vx + dx}+{vy + dy}")

    def _soltar(self, _evento):
        if not self.arrastre:
            return
        movio = self.arrastre[4]
        self.arrastre = None
        if movio:
            self.posicion.update(x=self.flotante.winfo_x(), y=self.flotante.winfo_y())
            self.estado.guardar(self.posicion)
        else:
            self.ocultar()
