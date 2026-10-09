# -*- coding: utf-8 -*-
"""Arma la conversación que se le envía al modelo a partir de prompt.txt.

prompt.txt tiene tres partes: las instrucciones, el GLOSARIO y los EJEMPLOS.
Un modelo chico ignora un glosario largo, así que no se le envía completo: para
cada mensaje se buscan las siglas que aparecen en él y solo esas se le entregan,
en una línea "Glosario:" pegada al mensaje. Los ejemplos se envían como turnos
ya respondidos, con ese mismo formato, para que el modelo lo imite.
"""

import re

INSTRUCCIONES_MINIMAS = "Traduce al español latino neutro el mensaje del chat. Responde solo con la traducción."
EJEMPLO = re.compile(r"^Mensaje:[ \t]*(.+)\r?\nTraducción:[ \t]*(.+)$", re.MULTILINE)
# Nombres que no se tocan: [Objetos] y <Hermandades>.
PROTEGIDO = re.compile(r"\[[^\]]*\]|<[^>]*>")
TROZO = re.compile(r"\[[^\]]*\]|<[^>]*>|[^\s\[<]+")
ALARGADA = re.compile(r"([^\W\d_])\1{3,}")   # "REEEEEE", "nooooo": gritos y memes
IGUAL = "(igual)"                            # significado especial: la palabra se deja en inglés
MAX_PISTAS = 12


def normalizar(texto):
    """Pasa a minúsculas un mensaje escrito entero en mayúsculas.

    El modelo reconoce "spec" o "tank" pero no "SPEC" o "TANK". Se conservan
    los [Objetos], las <Hermandades> y los gritos alargados (REEEEE).
    """
    if len(texto) <= 10 or not PROTEGIDO.sub("", texto).isupper():
        return texto

    def bajar(trozo):
        trozo = trozo.group()
        return trozo if trozo[0] in "[<" or ALARGADA.search(trozo) else trozo.lower()

    return TROZO.sub(bajar, texto)


def leer_glosario(texto):
    """Convierte las líneas "- sigla, otra forma: significado" en entradas."""
    glosario = []
    for linea in texto.splitlines():
        if not linea.startswith("- ") or ":" not in linea:
            continue
        claves, significado = linea[2:].split(":", 1)
        for clave in claves.split(","):
            clave = clave.strip()
            if clave:
                # Palabra completa, sin importar mayúsculas: "if" no calza dentro de "gift".
                patron = re.compile(r"(?<![\w/])" + re.escape(clave) + r"(?!\w)", re.IGNORECASE)
                glosario.append((clave, patron, significado.strip()))
    # Las siglas largas primero: "my mats" debe ganarle a "mats".
    glosario.sort(key=lambda entrada: -len(entrada[0]))
    return glosario


def turno(texto, glosario):
    """Da formato a un mensaje: pistas del glosario + mensaje + pie "Traducción:".

    El pie hace que el modelo continúe con la traducción en vez de leer el
    mensaje como una orden.
    """
    texto = normalizar(texto)
    # Las siglas no se buscan dentro de los nombres protegidos.
    resto = PROTEGIDO.sub(lambda m: " " * len(m.group()), texto)
    pistas = {}  # pista -> posición en el mensaje
    for clave, patron, significado in glosario:
        hallazgo = patron.search(resto)
        if not hallazgo:
            continue
        resto = patron.sub(lambda m: " " * len(m.group()), resto)  # no volver a calzar una parte
        # Se muestra la forma del glosario y no la del mensaje ("spec", no "SPEC").
        # Una palabra que se deja en inglés va como "spec = spec": se probó una
        # línea aparte "No traducir: ..." y el modelo la obedecía menos.
        pista = f"{clave} = {clave if significado == IGUAL else significado}"
        pistas.setdefault(pista, hallazgo.start())
    en_orden = sorted(pistas, key=pistas.get)[:MAX_PISTAS]  # en el orden del mensaje
    glosa = "Glosario: " + "; ".join(en_orden) + "\n" if en_orden else ""
    return f"{glosa}Mensaje: {texto}\nTraducción:"


RISA_ES = re.compile(r"\b(?:ja){2,}j?\b|\b(?:je){2,}j?\b", re.IGNORECASE)
RISA_EN = re.compile(r"\b(?:lol|lmao|rofl|(?:ha){2,}h?|(?:he){2,}h?|xd|kek)\b", re.IGNORECASE)


def pulir(original, traduccion):
    """Corrige en la traducción lo que el modelo no respeta siempre.

    Hoy solo una cosa: a veces escribe "jaja" pese a la regla. Se repone la risa
    del original (lol, haha...) o, si no había ninguna, se quita.
    """
    if not RISA_ES.search(traduccion):
        return traduccion
    risa = RISA_EN.search(original)
    traduccion = RISA_ES.sub(risa.group() if risa else "", traduccion)
    # Limpia lo que queda al quitar una palabra: espacios dobles y comas sueltas.
    traduccion = re.sub(r"\s+([,.!?])", r"\1", re.sub(r"\s+", " ", traduccion))
    return re.sub(r",\s*([,.!?])", r"\1", traduccion).strip(" ,")


class Prompt:
    """Se lee en cada uso: los cambios a prompt.txt se aplican sin reiniciar."""

    def __init__(self, ruta):
        self.ruta = ruta

    def leer(self):
        """Separa el archivo en (instrucciones, glosario, ejemplos)."""
        try:
            contenido = self.ruta.read_text(encoding="utf-8-sig")
        except OSError:
            contenido = ""
        ejemplos = [(m.strip(), t.strip()) for m, t in EJEMPLO.findall(contenido)]
        primero = EJEMPLO.search(contenido)
        cabeza = contenido[:primero.start()] if primero else contenido
        cabeza = re.sub(r"\n\s*EJEMPLOS\s*$", "", cabeza.rstrip())
        instrucciones, _, texto_glosario = cabeza.partition("\nGLOSARIO")
        return instrucciones.strip() or INSTRUCCIONES_MINIMAS, leer_glosario(texto_glosario), ejemplos

    def mensajes(self, texto):
        """Devuelve la lista de mensajes para /api/chat que traduce el texto."""
        instrucciones, glosario, ejemplos = self.leer()
        mensajes = [{"role": "system", "content": instrucciones}]
        for original, traduccion in ejemplos:
            mensajes.append({"role": "user", "content": turno(original, glosario)})
            mensajes.append({"role": "assistant", "content": traduccion})
        mensajes.append({"role": "user", "content": turno(texto, glosario)})
        return mensajes
