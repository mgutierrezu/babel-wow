# -*- coding: utf-8 -*-
"""Detecta mensajes que ya están en español, para no enviarlos a traducir.

Es una heurística deliberadamente prudente: ante la duda responde False y el
mensaje se traduce igual (el modelo devuelve el español tal como llegó). Lo
grave sería lo contrario: dejar sin traducir un mensaje en otro idioma.
"""

import re

SIGNOS = "ñÑ¿¡"

# Palabras muy frecuentes en español que NO existen en inglés, portugués ni
# italiano. Por eso faltan "que", "para", "como", "con", "una" o "no": también
# aparecen en esos idiomas y harían pasar por español un mensaje que no lo es.
PALABRAS = frozenset("""
    hola gracias porfa jaja jajaja
    el los las unos unas pero muy más ahora hoy bien también tambien entonces pues siempre
    alguien algún alguno nadie otro otra eso esto ese
    qué cómo sí dónde donde cuándo cuando quién quien
    soy eres estoy estás estamos están estan
    tengo tienes tiene tenemos quiero quieres quiere puedo puedes puede
    necesito necesitas hacer usted ustedes nosotros ellos
""".split())

ENTRE_CORCHETES = re.compile(r"\[[^\]]*\]|<[^>]*>")
PALABRA = re.compile(r"[a-záéíóúüñ]+")


def es_espanol(texto):
    """True solo si el mensaje está claramente en español."""
    if any(signo in texto for signo in SIGNOS):
        return True
    palabras = PALABRA.findall(ENTRE_CORCHETES.sub(" ", texto).lower())
    aciertos = {palabra for palabra in palabras if palabra in PALABRAS}
    # Dos palabras distintas, porque una sola puede ser casualidad: en el chat
    # en inglés "LoS" es línea de visión y "ESO" es otro juego. Un mensaje muy
    # corto ("hola", "gracias") cuenta si todas sus palabras son españolas.
    return len(aciertos) >= 2 or (bool(palabras) and len(aciertos) == len(set(palabras)))
