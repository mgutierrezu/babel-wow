# -*- coding: utf-8 -*-
"""Instalador de Traductor WoW.

Hace todo lo que el README pide hacer a mano:
  1. instala Ollama si falta y lo deja abierto,
  2. descarga el modelo de traducción,
  3. copia el addon a la carpeta de WoW que indique el usuario,
  4. instala el programa traductor y crea un acceso directo,
y al final abre una pantalla que verifica cada cosa de verdad.

Lleva dentro el traductor (TraductorWoW.exe), su configuración y el addon.
"""

import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import filedialog, ttk

OLLAMA = "http://127.0.0.1:11434"
INSTALADOR_OLLAMA = "https://ollama.com/download/OllamaSetup.exe"
EJEMPLO = r"C:\Program Files (x86)\World of Warcraft\_classic_era_"
SIN_VENTANA = 0x08000000  # para que los comandos no abran una consola

# Archivos que se instalan: dentro del .exe al compilar, o en el repositorio al correr el .py.
if getattr(sys, "frozen", False):
    _paquete = Path(sys._MEIPASS) / "paquete"
    RECURSOS = {"exe": _paquete / "TraductorWoW.exe", "env": _paquete / ".env.example",
                "prompt": _paquete / "prompt.txt", "addon": _paquete / "TraductorWoW"}
else:
    _raiz = Path(__file__).resolve().parent.parent
    RECURSOS = {"exe": _raiz / "Traductor" / "dist" / "TraductorWoW.exe", "env": _raiz / "Traductor" / ".env.example",
                "prompt": _raiz / "Traductor" / "prompt.txt", "addon": _raiz / "Addon" / "TraductorWoW"}

DESTINO = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TraductorWoW"

# La lista de modelos y la escritura del .env se comparten con el traductor, para
# que el instalador y el programa ofrezcan lo mismo. Al compilar, PyInstaller
# encuentra el paquete "app" gracias a la opción --paths de build.bat.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(_raiz / "Traductor"))
from app.config import guardar_valor, leer_env  # noqa: E402
from app.modelos import MODELOS, buscar, memoria_de_video, numero, sugerir  # noqa: E402


class ErrorInstalacion(Exception):
    """Falla con un mensaje pensado para mostrarse al usuario."""


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

_abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(ruta, cuerpo=None, timeout=5):
    """Llama a la API local de Ollama y devuelve la respuesta como diccionario."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(OLLAMA + ruta, data=datos, headers={"Content-Type": "application/json"})
    with _abridor.open(peticion, timeout=timeout) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def modelo_inicial(destino):
    """Modelo que se propone al abrir el instalador y el motivo, para mostrarlo.

    Si ya hay una instalación se respeta el que el usuario tenía; si no, se
    sugiere uno según la memoria de la tarjeta de video.
    """
    instalado = leer_env(destino / ".env").get("OLLAMA_MODELO")
    if instalado and buscar(instalado):
        return instalado, "Es el modelo que ya tienes instalado."
    video = memoria_de_video()
    if video is None:
        return sugerir(None).nombre, "No se pudo detectar tu tarjeta de video; elige según su memoria."
    return sugerir(video).nombre, f"Tu tarjeta de video tiene {numero(round(video))} GB: te sugerimos el marcado."


def version_ollama():
    """Devuelve la versión si Ollama está abierto y responde; si no, None."""
    try:
        return api("/api/version", timeout=2).get("version", "?")
    except (OSError, ValueError):
        return None


def ruta_ollama():
    """Busca el programa de Ollama instalado. Devuelve la carpeta o None."""
    candidatas = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama",
                  Path(os.environ.get("ProgramFiles", "")) / "Ollama"]
    en_path = shutil.which("ollama")
    if en_path:
        candidatas.insert(0, Path(en_path).parent)
    for carpeta in candidatas:
        if (carpeta / "ollama.exe").exists():
            return carpeta
    return None


def descargar(url, destino, progreso):
    """Descarga un archivo informando el avance (0.0 a 1.0)."""
    with urllib.request.urlopen(url, timeout=60) as respuesta, open(destino, "wb") as archivo:
        total = int(respuesta.headers.get("Content-Length") or 0)
        hecho = 0
        while True:
            trozo = respuesta.read(1 << 20)
            if not trozo:
                break
            archivo.write(trozo)
            hecho += len(trozo)
            if total:
                progreso(hecho / total)


def instalar_ollama(avisar, progreso):
    """Instala Ollama con winget; si no hay winget, descarga el instalador oficial."""
    if shutil.which("winget"):
        avisar("Instalando Ollama con winget (descarga cerca de 1 GB)...")
        progreso(None)
        resultado = subprocess.run(
            ["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, creationflags=SIN_VENTANA, timeout=3600)
        if resultado.returncode == 0 or ruta_ollama():
            return
    avisar("Descargando el instalador de Ollama (cerca de 1 GB)...")
    instalador = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
    try:
        descargar(INSTALADOR_OLLAMA, instalador, progreso)
    except OSError as error:
        raise ErrorInstalacion(f"No se pudo descargar Ollama. Revisa tu conexión a internet. ({error})") from None
    avisar("Instalando Ollama...")
    progreso(None)
    subprocess.run([str(instalador), "/VERYSILENT", "/NORESTART"], timeout=1800)
    if not ruta_ollama():
        raise ErrorInstalacion("Ollama no quedó instalado. Instálalo a mano desde https://ollama.com/download "
                               "y vuelve a abrir este instalador.")


def iniciar_ollama(avisar):
    """Enciende Ollama (oculto) si está cerrado y espera a que responda.
    Devuelve True si lo encendió este instalador."""
    if version_ollama():
        return False
    carpeta = ruta_ollama()
    if not carpeta:
        raise ErrorInstalacion("No se encontró Ollama instalado.")
    avisar("Encendiendo Ollama...")
    subprocess.Popen([str(carpeta / "ollama.exe"), "serve"], creationflags=SIN_VENTANA,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if version_ollama():
            return True
        time.sleep(1)
    raise ErrorInstalacion("Ollama no respondió. Reinicia el computador y vuelve a abrir este instalador.")


def apagar_ollama():
    """Cierra Ollama y el modelo cargado. Traductor WoW lo enciende solo al abrirse."""
    for nombre in ("ollama app.exe", "ollama.exe", "llama-server.exe"):
        subprocess.run(["taskkill", "/IM", nombre, "/T", "/F"], capture_output=True, creationflags=SIN_VENTANA)


def quitar_inicio_automatico():
    """Ollama se instala para abrirse con Windows; aquí lo maneja Traductor WoW."""
    acceso = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Ollama.lnk"
    try:
        acceso.unlink(missing_ok=True)
    except OSError:
        pass


def modelo_descargado(modelo):
    """Devuelve el tamaño en GB si el modelo ya está descargado; si no, None."""
    for instalado in api("/api/tags").get("models", []):
        nombre = instalado.get("name", "")
        if nombre in (modelo, modelo + ":latest"):
            return instalado.get("size", 0) / 1e9
    return None


def descargar_modelo(modelo, avisar, progreso):
    """Descarga el modelo con la API de Ollama, mostrando el avance."""
    avisar(f"Descargando el modelo {modelo} (puede tardar varios minutos)...")
    cuerpo = json.dumps({"model": modelo, "stream": True}).encode("utf-8")
    peticion = urllib.request.Request(OLLAMA + "/api/pull", data=cuerpo, headers={"Content-Type": "application/json"})
    try:
        with _abridor.open(peticion, timeout=120) as respuesta:
            for linea in respuesta:
                if not linea.strip():
                    continue
                paso = json.loads(linea)
                if paso.get("error"):
                    raise ErrorInstalacion(f"Ollama no pudo descargar el modelo: {paso['error']}")
                if paso.get("total"):
                    hecho, total = paso.get("completed", 0), paso["total"]
                    progreso(hecho / total)
                    avisar(f"Descargando el modelo {modelo}: {hecho / 1e9:.1f} de {total / 1e9:.1f} GB")
    except (OSError, ValueError) as error:
        raise ErrorInstalacion(f"Se cortó la descarga del modelo. Vuelve a intentar: continúa donde quedó. ({error})") from None


def modelo_responde(modelo):
    """Carga el modelo y le pide una respuesta. Devuelve los segundos que tardó."""
    inicio = time.time()
    respuesta = api("/api/chat", {
        "model": modelo, "stream": False, "keep_alive": "30m", "options": {"num_predict": 8},
        "messages": [{"role": "user", "content": "Responde solo: listo"}],
    }, timeout=600)
    if not (respuesta.get("message") or {}).get("content", "").strip():
        raise ErrorInstalacion("El modelo no devolvió ninguna respuesta.")
    return time.time() - inicio


def modelo_cargado(modelo):
    """Indica si el modelo está ahora mismo en memoria."""
    try:
        return any(m.get("name", "").split(":latest")[0] == modelo.split(":latest")[0]
                   for m in api("/api/ps", timeout=3).get("models", []))
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# WoW y el traductor
# ---------------------------------------------------------------------------

def detectar_wow():
    """Busca instalaciones de WoW en las ubicaciones habituales, la más usada primero."""
    raices = [Path(os.environ.get(variable, "")) / "World of Warcraft" for variable in ("ProgramFiles(x86)", "ProgramFiles")]
    raices += [Path(f"{letra}:\\") / carpeta / "World of Warcraft"
               for letra in "CDEF" for carpeta in ("", "Games", "Juegos")]
    halladas = {}
    for raiz in raices:
        try:
            versiones = [v for v in raiz.iterdir() if v.is_dir() and v.name.startswith("_") and v.name.endswith("_")]
        except OSError:
            continue
        for version in versiones:
            if (version / "Interface" / "AddOns").is_dir():
                config = version / "WTF" / "Config.wtf"
                halladas[str(version)] = config.stat().st_mtime if config.exists() else 0
    return sorted(halladas, key=halladas.get, reverse=True)


def carpeta_addons(texto):
    """Convierte lo que escribió el usuario en la carpeta Interface\\AddOns de su versión."""
    texto = texto.strip().strip('"')
    if not texto:
        raise ErrorInstalacion("Escribe o elige la carpeta de tu versión de WoW.")
    ruta = Path(texto)
    if not ruta.is_dir():
        raise ErrorInstalacion("Esa carpeta no existe. Revisa la ruta o usa el botón Examinar.")
    if ruta.name.lower() == "addons" and ruta.parent.name.lower() == "interface":
        return ruta
    if (ruta / "Interface" / "AddOns").is_dir():
        return ruta / "Interface" / "AddOns"
    versiones = sorted(v.name for v in ruta.iterdir() if v.is_dir() and v.name.startswith("_") and v.name.endswith("_"))
    if versiones:
        raise ErrorInstalacion("Esa es la carpeta general de WoW. Elige dentro de ella la de tu versión, "
                               f"por ejemplo:\n{ruta / versiones[0]}")
    if any(ruta.glob("Wow*.exe")):  # versión recién instalada, aún sin addons
        (ruta / "Interface" / "AddOns").mkdir(parents=True, exist_ok=True)
        return ruta / "Interface" / "AddOns"
    raise ErrorInstalacion("Esa no parece una carpeta de WoW. Debe ser la de tu versión del juego, por ejemplo:\n" + EJEMPLO)


# El programa se llamó así en sus primeras versiones. Al instalar se retira lo
# que haya quedado con ese nombre, para no tener dos addons ni dos programas.
NOMBRE_ANTERIOR = "TraductorGamer"
ACCESO_ANTERIOR = "Traductor Gamer.lnk"


def carpeta_escritorio():
    """Escritorio real del usuario (puede estar redirigido a OneDrive)."""
    ruta = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, ruta)  # CSIDL_DESKTOPDIRECTORY
    return Path(ruta.value)


def quitar_addon_anterior(addons):
    """Quita el addon con el nombre anterior: dos addons duplicarían el menú del chat."""
    viejo = addons / NOMBRE_ANTERIOR
    try:
        if os.path.isjunction(viejo) or viejo.is_symlink():
            os.rmdir(viejo)  # es un enlace: se quita el enlace, no lo enlazado
        elif viejo.is_dir():
            shutil.rmtree(viejo)
    except OSError:
        pass  # si no se puede, el addon nuevo igual queda instalado


def migrar_programa_anterior(destino, escritorio=None):
    """Trae la configuración, el glosario y el historial de la instalación con el
    nombre anterior, y luego la retira junto con su acceso directo."""
    viejo = destino.parent / NOMBRE_ANTERIOR
    if viejo.is_dir():
        subprocess.run(["taskkill", "/IM", NOMBRE_ANTERIOR + ".exe", "/F"], capture_output=True, creationflags=SIN_VENTANA)
        time.sleep(1.5)
        destino.mkdir(parents=True, exist_ok=True)
        for nombre in (".env", "prompt.txt", "estado.json", "traducciones.txt"):
            if (viejo / nombre).exists() and not (destino / nombre).exists():
                shutil.copy2(viejo / nombre, destino / nombre)
        shutil.rmtree(viejo, ignore_errors=True)
    try:
        (Path(escritorio) if escritorio else carpeta_escritorio()).joinpath(ACCESO_ANTERIOR).unlink(missing_ok=True)
    except OSError:
        pass


def instalar_addon(addons):
    """Copia el addon. Devuelve la carpeta donde quedó."""
    quitar_addon_anterior(addons)
    destino = addons / "TraductorWoW"
    try:
        shutil.copytree(RECURSOS["addon"], destino, dirs_exist_ok=True)
    except PermissionError:
        raise ErrorInstalacion("Windows no dejó copiar el addon en esa carpeta. Cierra este instalador, "
                               "haz clic derecho sobre él y elige \"Ejecutar como administrador\".") from None
    except OSError as error:
        raise ErrorInstalacion(f"No se pudo copiar el addon: {error}") from None
    return destino


def addon_instalado(addons):
    return (addons / "TraductorWoW" / "TraductorWoW.toc").exists()


def instalar_programa(destino):
    """Copia el traductor a su carpeta. Conserva la configuración si ya existía."""
    destino.mkdir(parents=True, exist_ok=True)
    ejecutable = destino / "TraductorWoW.exe"
    try:
        shutil.copyfile(RECURSOS["exe"], ejecutable)
    except PermissionError:
        # El traductor está abierto: se cierra para poder actualizarlo.
        subprocess.run(["taskkill", "/IM", "TraductorWoW.exe", "/F"], capture_output=True, creationflags=SIN_VENTANA)
        time.sleep(1.5)
        try:
            shutil.copyfile(RECURSOS["exe"], ejecutable)
        except OSError:
            raise ErrorInstalacion("Cierra la ventana de Traductor WoW y vuelve a intentar.") from None
    shutil.copyfile(RECURSOS["env"], destino / ".env.example")
    for origen, nombre in ((RECURSOS["env"], ".env"), (RECURSOS["prompt"], "prompt.txt")):
        if not (destino / nombre).exists():  # no pisar lo que el usuario haya editado
            shutil.copyfile(origen, destino / nombre)
    return ejecutable


def crear_acceso_directo(ejecutable, carpeta=None):
    """Crea "Traductor WoW" en el Escritorio (o en la carpeta indicada)."""
    entorno = dict(os.environ, TG_EXE=str(ejecutable), TG_CARPETA=str(carpeta or ""))
    comando = ("$c = if ($env:TG_CARPETA) { $env:TG_CARPETA } else { [Environment]::GetFolderPath('Desktop') }; "
               "$a = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $c 'Traductor WoW.lnk')); "
               "$a.TargetPath = $env:TG_EXE; $a.WorkingDirectory = (Split-Path $env:TG_EXE); "
               "$a.Description = 'Traductor de chat para World of Warcraft'; $a.Save()")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
                   capture_output=True, env=entorno, creationflags=SIN_VENTANA, timeout=60)


# ---------------------------------------------------------------------------
# Ventana
# ---------------------------------------------------------------------------

FONDO = "#ffffff"
GRIS = "#6b7280"
AZUL = "#2563eb"
VERDE = "#16a34a"
ROJO = "#dc2626"


class Indicador(tk.Canvas):
    """Circulito de estado: pendiente, girando, ok, error o activo (en ejecución)."""

    def __init__(self, padre, lado=24):
        super().__init__(padre, width=lado, height=lado, bg=FONDO, highlightthickness=0)
        self.lado, self.estado, self.angulo, self.tarea = lado, "pendiente", 90, None
        self._dibujar()

    def poner(self, estado):
        self.estado = estado
        self._dibujar()

    def _dibujar(self):
        if self.tarea:
            self.after_cancel(self.tarea)
            self.tarea = None
        self.delete("all")
        a, b = 4, self.lado - 4
        if self.estado == "pendiente":
            self.create_oval(a, a, b, b, outline="#d1d5db", width=2)
        elif self.estado in ("girando", "activo"):
            color = VERDE if self.estado == "activo" else AZUL
            self.create_oval(a, a, b, b, outline="#e5e7eb", width=3)
            self.create_arc(a, a, b, b, start=self.angulo, extent=110, style="arc", outline=color, width=3)
            if self.estado == "activo":  # punto central: el modelo está vivo
                centro = self.lado / 2
                self.create_oval(centro - 3, centro - 3, centro + 3, centro + 3, fill=VERDE, outline="")
            self.angulo = (self.angulo - 20) % 360
            self.tarea = self.after(50, self._dibujar)
        elif self.estado == "ok":
            self.create_oval(a, a, b, b, fill=VERDE, outline="")
            m = self.lado
            self.create_line(m * .30, m * .52, m * .45, m * .66, m * .71, m * .36, fill="white", width=2.5, capstyle="round")
        else:  # error
            self.create_oval(a, a, b, b, fill=ROJO, outline="")
            m = self.lado
            self.create_line(m * .36, m * .36, m * .64, m * .64, fill="white", width=2.5, capstyle="round")
            self.create_line(m * .64, m * .36, m * .36, m * .64, fill="white", width=2.5, capstyle="round")


FILAS = ("ollama", "modelo", "addon", "programa", "listo")


class Instalador:
    def __init__(self, destino=DESTINO, escritorio=None):
        self.destino = Path(destino)       # carpeta donde se instala el traductor
        self.escritorio = escritorio       # carpeta del acceso directo (None = Escritorio)
        self.modelo, self.motivo_modelo = modelo_inicial(self.destino)
        self.addons = None                 # carpeta AddOns elegida
        self.cola = queue.Queue()          # mensajes de los hilos hacia la ventana
        self.vigilando = False
        self.ollama_propio = False         # True si este instalador instaló o encendió Ollama

        self.root = tk.Tk()
        self.root.title("Instalar Traductor WoW")
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.root.configure(bg=FONDO)
        self.root.resizable(False, False)
        self.fuente = ("Segoe UI", 10)
        self.contenedor = tk.Frame(self.root, bg=FONDO, padx=26, pady=22)
        self.contenedor.pack()
        self._pagina_instalar()
        self.root.after(80, self._atender)

    # --- utilidades de la ventana ---

    def _texto(self, padre, texto, tam=10, color="#111827", negrita=False, ancho=520, **pack):
        etiqueta = tk.Label(padre, text=texto, bg=FONDO, fg=color, justify="left", anchor="w", wraplength=ancho,
                            font=("Segoe UI", tam, "bold" if negrita else "normal"))
        etiqueta.pack(fill="x", **pack)
        return etiqueta

    def _limpiar(self):
        for hijo in self.contenedor.winfo_children():
            hijo.destroy()

    def _atender(self):
        """Aplica en la ventana lo que piden los hilos de trabajo."""
        try:
            while True:
                orden = self.cola.get_nowait()
                tipo = orden[0]
                if tipo == "estado":
                    self.lbl_estado.config(text=orden[1], fg=GRIS)
                elif tipo == "progreso":
                    self._progreso(orden[1])
                elif tipo == "error":
                    self._progreso(0)
                    self.lbl_estado.config(text=orden[1], fg=ROJO)
                    self.btn_instalar.config(state="normal")
                elif tipo == "verificar":
                    self._pagina_verificar()
                elif tipo == "fila":
                    self._fila(*orden[1:])
                elif tipo == "fin":
                    self.btn_reintentar.config(state="normal")
                    if (self.destino / "TraductorWoW.exe").exists():
                        self.btn_abrir.config(state="normal")
        except queue.Empty:
            pass
        except tk.TclError:
            return  # la ventana cambió de página mientras llegaba un mensaje viejo
        self.root.after(80, self._atender)

    def _progreso(self, fraccion):
        """None = avance desconocido (barra en movimiento); número = porcentaje."""
        if fraccion is None:
            if str(self.barra.cget("mode")) != "indeterminate":
                self.barra.config(mode="indeterminate")
                self.barra.start(14)
        else:
            self.barra.stop()
            self.barra.config(mode="determinate", value=fraccion * 100)

    # --- página 1: instalar ---

    def _pagina_instalar(self):
        self._limpiar()
        c = self.contenedor
        self._texto(c, "Traductor WoW", tam=16, negrita=True)
        self._texto(c, "Traduce el chat de World of Warcraft al español con un modelo de IA que corre en tu "
                       "propio computador. No envía nada a internet.", color=GRIS, pady=(2, 16))

        self._texto(c, "Carpeta de tu versión de WoW", negrita=True)
        fila = tk.Frame(c, bg=FONDO)
        fila.pack(fill="x", pady=(4, 2))
        halladas = detectar_wow()
        self.ruta = tk.StringVar(value=halladas[0] if halladas else "")
        ttk.Combobox(fila, textvariable=self.ruta, values=halladas, width=58, font=self.fuente).pack(side="left", fill="x", expand=True)
        ttk.Button(fila, text="Examinar...", command=self._examinar).pack(side="left", padx=(8, 0))
        self._texto(c, "Ejemplo:  " + EJEMPLO, tam=9, color=GRIS)
        self._texto(c, "Es la carpeta que tiene dentro \"Interface\" y \"WTF\". Cada versión del juego tiene la suya: "
                       "_retail_, _classic_era_, _classic_, _anniversary_...", tam=9, color=GRIS, pady=(0, 16))

        self._texto(c, "Modelo de traducción", negrita=True)
        self._texto(c, self.motivo_modelo + " Podrás cambiarlo después desde la ventana del programa.",
                    tam=9, color=GRIS, pady=(0, 4))
        self.eleccion = tk.StringVar(value=self.modelo)
        for modelo in MODELOS:
            tk.Radiobutton(c, variable=self.eleccion, value=modelo.nombre, bg=FONDO, activebackground=FONDO,
                           anchor="w", font=("Segoe UI", 10, "bold"), highlightthickness=0,
                           text=f"{modelo.nivel}  ·  {numero(modelo.video_gb)} GB de memoria de video  ·  "
                                f"descarga {numero(modelo.descarga_gb)} GB").pack(fill="x")
            self._texto(c, modelo.descripcion, tam=9, color=GRIS, ancho=490, padx=(24, 0), pady=(0, 3))

        self._texto(c, "Además se instala Ollama (el programa que ejecuta la IA, si no lo tienes), el addon en la "
                       "carpeta de arriba y Traductor WoW con un acceso directo en el Escritorio.",
                    tam=9, color="#374151", pady=(8, 14))

        self.btn_instalar = ttk.Button(c, text="Instalar", command=self._al_instalar)
        self.btn_instalar.pack(anchor="w", ipadx=18, ipady=3)
        self.barra = ttk.Progressbar(c, length=520, mode="determinate")
        self.barra.pack(fill="x", pady=(16, 6))
        self.lbl_estado = self._texto(c, "", tam=9, color=GRIS)
        self.lbl_estado.config(height=3, anchor="nw")

    def _examinar(self):
        elegida = filedialog.askdirectory(title="Elige la carpeta de tu versión de WoW", initialdir=self.ruta.get() or None)
        if elegida:
            self.ruta.set(os.path.normpath(elegida))

    def _al_instalar(self):
        try:
            self.addons = carpeta_addons(self.ruta.get())
        except ErrorInstalacion as error:
            self.lbl_estado.config(text=str(error), fg=ROJO)
            return
        self.modelo = self.eleccion.get()
        self.btn_instalar.config(state="disabled")
        threading.Thread(target=self._instalar, daemon=True).start()

    def _instalar(self):
        """Corre en un hilo aparte: la ventana sigue respondiendo."""
        avisar = lambda texto: self.cola.put(("estado", texto))
        progreso = lambda fraccion: self.cola.put(("progreso", fraccion))
        try:
            progreso(None)
            avisar("Revisando Ollama...")
            if not version_ollama() and not ruta_ollama():
                instalar_ollama(avisar, progreso)
                quitar_inicio_automatico()
                self.ollama_propio = True  # recién instalado: nadie más lo está usando
            progreso(None)
            if iniciar_ollama(avisar):
                self.ollama_propio = True
            if modelo_descargado(self.modelo) is None:
                descargar_modelo(self.modelo, avisar, progreso)
            progreso(None)
            avisar("Copiando el addon...")
            instalar_addon(self.addons)
            avisar("Instalando el traductor...")
            migrar_programa_anterior(self.destino, self.escritorio)
            crear_acceso_directo(instalar_programa(self.destino), self.escritorio)
            guardar_valor(self.destino / ".env", "OLLAMA_MODELO", self.modelo)  # el traductor usará el elegido
            self.cola.put(("verificar",))
        except ErrorInstalacion as error:
            self.cola.put(("error", str(error)))
        except Exception as error:
            self.cola.put(("error", f"Error inesperado: {error}"))

    # --- página 2: verificar ---

    def _pagina_verificar(self):
        self._limpiar()
        c = self.contenedor
        self._texto(c, "Verificación", tam=16, negrita=True)
        self._texto(c, "Se comprueba cada parte de la instalación.", color=GRIS, pady=(2, 14))
        titulos = {"ollama": "Ollama instalado y abierto", "modelo": f"Modelo {self.modelo} descargado",
                   "addon": "Addon instalado en WoW", "programa": "Traductor instalado",
                   "listo": "Modelo en ejecución"}
        self.filas = {}
        for clave in FILAS:
            fila = tk.Frame(c, bg=FONDO)
            fila.pack(fill="x", pady=5)
            indicador = Indicador(fila)
            indicador.pack(side="left", anchor="n", padx=(0, 12), pady=2)
            textos = tk.Frame(fila, bg=FONDO)
            textos.pack(side="left", fill="x", expand=True)
            self._texto(textos, titulos[clave], negrita=True, ancho=470)
            detalle = self._texto(textos, "", tam=9, color=GRIS, ancho=470)
            self.filas[clave] = (indicador, detalle)

        self.lbl_final = self._texto(c, "", pady=(14, 12))
        botones = tk.Frame(c, bg=FONDO)
        botones.pack(fill="x")
        self.btn_abrir = ttk.Button(botones, text="Abrir Traductor WoW", command=self._abrir, state="disabled")
        self.btn_abrir.pack(side="left", ipadx=10, ipady=3)
        self.btn_reintentar = ttk.Button(botones, text="Verificar de nuevo", command=self._verificar, state="disabled")
        self.btn_reintentar.pack(side="left", padx=8, ipady=3)
        ttk.Button(botones, text="Cerrar", command=self._cerrar).pack(side="right", ipady=3)
        self._verificar()

    def _fila(self, clave, estado, detalle):
        indicador, etiqueta = self.filas[clave]
        indicador.poner(estado)
        etiqueta.config(text=detalle, fg=ROJO if estado == "error" else GRIS)
        if clave == "listo" and estado in ("activo", "error", "pendiente"):
            listo = estado == "activo"
            self.lbl_final.config(
                fg=VERDE if listo else "#374151",
                text=("Todo listo. Abre Traductor WoW y deja su ventana abierta (puedes minimizarla). Entra a WoW "
                      "(si estaba abierto, ciérralo y vuelve a abrirlo), haz clic sobre un mensaje del chat y presiona Ctrl+C.")
                if listo else "")

    def _verificar(self):
        self.vigilando = False
        self.btn_reintentar.config(state="disabled")
        for clave in FILAS:
            self._fila(clave, "pendiente", "")
        threading.Thread(target=self._comprobar, daemon=True).start()

    def _comprobar(self):
        """Comprueba el estado real de cada parte, sin fiarse de que la instalación terminó."""
        poner = lambda clave, estado, detalle: self.cola.put(("fila", clave, estado, detalle))

        poner("ollama", "girando", "")
        version = version_ollama()
        if version:
            poner("ollama", "ok", f"Versión {version}, respondiendo en {OLLAMA}")
        else:
            poner("ollama", "error", "Ollama no responde. Ábrelo desde el menú Inicio y pulsa \"Verificar de nuevo\".")

        poner("modelo", "girando", "")
        try:
            tamano = modelo_descargado(self.modelo) if version else None
        except (OSError, ValueError):
            tamano = None
        if tamano is not None:
            poner("modelo", "ok", f"{tamano:.1f} GB en disco")
        else:
            poner("modelo", "error", "El modelo no está descargado." if version else "No se puede revisar sin Ollama.")

        poner("addon", "girando", "")
        if self.addons and addon_instalado(self.addons):
            poner("addon", "ok", str(self.addons / "TraductorWoW"))
        else:
            poner("addon", "error", "No se encontró el addon en la carpeta de WoW.")

        poner("programa", "girando", "")
        ejecutable = self.destino / "TraductorWoW.exe"
        if ejecutable.exists():
            poner("programa", "ok", f"{ejecutable}  ·  acceso directo en el Escritorio")
        else:
            poner("programa", "error", "No se encontró el programa instalado.")

        if tamano is None:
            poner("listo", "error", "No se puede probar sin el modelo.")
        else:
            poner("listo", "girando", "Cargando el modelo en memoria. La primera vez puede tardar hasta un minuto...")
            try:
                segundos = modelo_responde(self.modelo)
                poner("listo", "activo", f"Respondió en {segundos:.1f} s. Listo para usarse en WoW.")
                self.vigilando = True
                threading.Thread(target=self._vigilar, daemon=True).start()
            except ErrorInstalacion as error:
                poner("listo", "error", str(error))
            except (OSError, ValueError) as error:
                poner("listo", "error", f"El modelo no respondió: {error}")
        self.cola.put(("fin",))

    def _vigilar(self):
        """Mientras la ventana siga abierta, confirma que el modelo sigue en memoria."""
        while self.vigilando:
            time.sleep(5)
            if not self.vigilando:
                return
            if modelo_cargado(self.modelo):
                self.cola.put(("fila", "listo", "activo", "En ejecución. Listo para usarse en WoW."))
            else:
                self.cola.put(("fila", "listo", "pendiente",
                               "El modelo se descargó de la memoria; vuelve a cargarse solo con la próxima traducción."))

    def _soltar_ollama(self):
        """Apaga el Ollama que usó el instalador. Uno que ya estaba abierto no se toca."""
        self.vigilando = False
        if self.ollama_propio:
            self.ollama_propio = False
            apagar_ollama()

    def _abrir(self):
        # El traductor enciende su propio Ollama y lo apaga al salir.
        self._soltar_ollama()
        self._fila("listo", "ok", "Traductor WoW abierto: él enciende el modelo al abrirse y lo apaga al salir.")
        ejecutable = self.destino / "TraductorWoW.exe"
        subprocess.Popen([str(ejecutable)], cwd=str(self.destino), close_fds=True)

    def _cerrar(self):
        self._soltar_ollama()
        self.root.destroy()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # texto nítido en pantallas con escala
    except Exception:
        pass
    Instalador().root.mainloop()


if __name__ == "__main__":
    main()
