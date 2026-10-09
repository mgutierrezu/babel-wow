# babel-wow

Traductor de chat para World of Warcraft que usa un modelo de IA local. No envía nada a internet.

Son dos piezas que se comunican por el portapapeles:

1. **Addon `TraductorWoW`** (Lua): agrega "Traducir mensaje" al clic derecho sobre el nombre de un jugador en el chat y muestra una cajita con el texto listo para copiar.
2. **Programa `TraductorWoW.exe`** (Python): vigila el portapapeles, envía el mensaje a Ollama y muestra la traducción en una ventana flotante.

```
Chat de WoW ──clic derecho──> cajita con "[TR] Nombre (Canal): mensaje"
                                   │  Ctrl+C
                                   v
                             portapapeles ──> TraductorWoW.exe ──> Ollama (local)
                                                     │
                                                     v
                                            ventana flotante
```

El programa **solo lee** el portapapeles y muestra su propia ventana. No envía teclas ni clics, y no escribe nada dentro del juego.

## Instalador para compartir

Para instalar todo sin seguir los pasos manuales de más abajo, o para pasárselo a otra persona:

1. Ejecuta `Traductor\build.bat` y luego `Instalador\build.bat`.
2. Comparte la carpeta `output` completa: contiene `InstalarTraductorWoW.exe` y `LEEME.txt`.

El instalador es un solo archivo que lleva dentro el traductor y el addon. Pide la carpeta de WoW, instala Ollama si falta, descarga el modelo, copia el addon e instala el traductor en `%LOCALAPPDATA%\TraductorWoW` con un acceso directo en el Escritorio. Al terminar muestra una pantalla que verifica cada parte. Si se vuelve a ejecutar no descarga nada de nuevo, y conserva el `.env` y el `prompt.txt` que ya existan.

## Requisitos

- Windows 10 u 11.
- World of Warcraft. El addon está hecho para TBC Anniversary (2.5.6) y también declara compatibilidad con Classic Era, MoP Classic y Retail.
- [Ollama](https://ollama.com/download).
- Tarjeta de video con 6 GB de VRAM o más para el modelo por defecto, `gemma3:4b` (ocupa unos 3 GB y comparte la memoria con el juego).
- [Python 3.10 o superior](https://www.python.org/downloads/), solo para compilar el `.exe`.

## Instalación

### 1. Ollama y el modelo

1. Instala Ollama desde <https://ollama.com/download>. Queda corriendo con un icono en la bandeja del sistema y configurado para abrirse con Windows. Como Traductor WoW lo enciende y apaga por su cuenta, puedes quitarle el inicio automático: Administrador de tareas → "Aplicaciones de arranque" → Ollama → Deshabilitar.
2. Abre una terminal (PowerShell) y descarga el modelo (unos 3 GB):

   ```
   ollama pull gemma3:4b
   ```

3. Comprueba que responde:

   ```
   ollama run gemma3:4b "Di hola"
   ```

   Esta prueba no usa el glosario ni las reglas del traductor, así que no sirve para juzgar las traducciones.

### 2. El addon

Copia la carpeta `Addon\TraductorWoW` a la carpeta `Interface\AddOns` de tu versión del juego:

| Versión | Carpeta |
| --- | --- |
| TBC Anniversary | `World of Warcraft\_anniversary_\Interface\AddOns` |
| Classic Era / Hardcore | `World of Warcraft\_classic_era_\Interface\AddOns` |
| MoP Classic | `World of Warcraft\_classic_\Interface\AddOns` |
| Retail | `World of Warcraft\_retail_\Interface\AddOns` |

Por ejemplo, desde PowerShell en la carpeta de este proyecto:

```
Copy-Item -Recurse Addon\TraductorWoW "C:\Program Files (x86)\World of Warcraft\_anniversary_\Interface\AddOns\"
```

Reinicia el juego (o escribe `/reload`) y verifica que "Traductor WoW" aparezca activado en la lista de addons. Si aparece como "desactualizado", marca "Cargar addons desactualizados".

### 3. El programa

Haz doble clic en `Traductor\build.bat`. Instala las dependencias y genera:

```
Traductor\dist\TraductorWoW.exe
Traductor\dist\.env
Traductor\dist\.env.example
Traductor\dist\prompt.txt
```

Puedes mover la carpeta `dist` a donde quieras; mantén los archivos juntos.

Para probar sin compilar: `python Traductor\traductor.py`. La primera vez crea `Traductor\.env` a partir de `.env.example`.

## Uso

1. Abre `TraductorWoW.exe`. Se abre la ventana del programa, que queda en la barra de tareas; cuando el punto se pone verde y dice "Funcionando", está listo. Puedes minimizarla.
2. En el juego, haz **clic sobre el texto del mensaje** en el chat. También sirve el clic derecho sobre el nombre del jugador → **Traducir mensaje**.
3. Se abre una cajita con el texto ya seleccionado. Presiona **Ctrl+C**. La cajita se cierra sola.
4. La ventana flotante muestra "Traduciendo..." y luego la traducción.

Otras formas de abrir la cajita:

| Acción | Resultado |
| --- | --- |
| Clic en el texto del mensaje | Traduce ese mensaje |
| Clic derecho en el nombre → Traducir mensaje | Traduce ese mensaje |
| Ctrl+clic en el nombre | Traduce ese mensaje |
| `/tr` | Traduce el último mensaje recibido |
| `/tr Nombre` | Traduce el último mensaje de ese jugador |
| `/traducir` | Igual que `/tr` |
| `/twow mensaje en español` | Traduce tu mensaje al inglés y lo deja copiado |

### Escribir en inglés

Para responder en inglés, escribe tu mensaje en español. Hay dos formas de empezar:

- **Botón del minimapa** (icono de una nota): un clic abre un cuadro; escribe ahí y presiona Enter. El botón se arrastra alrededor del minimapa y recuerda su lugar. Con clic derecho traduce el último mensaje recibido.
- **Comando:** `/twow` seguido del mensaje. Sin mensaje, abre el mismo cuadro.

Después el flujo es el mismo:

1. En el chat: `/twow hola, busco grupo para Deadmines` (o escríbelo en el cuadro del botón)
2. Se abre la cajita con tu texto. Presiona **Ctrl+C**.
3. La ventana flotante muestra la traducción ("hi, LFG Deadmines") y avisa "Copiado": ya está en el portapapeles.
4. El chat queda abierto: pega con **Ctrl+V** y presiona Enter.

Mientras traduce, el portapapeles queda vacío, así que si pegas antes de tiempo no sale nada. El programa nunca escribe en el juego: solo deja el texto listo para que lo pegues tú. Si la traducción supera los 255 caracteres que admite el chat, la ventana lo advierte en rojo.

Las reglas, el glosario y los ejemplos de este sentido están en `prompt_en.txt`, con el mismo formato que `prompt.txt`.

La ventana flotante:

- Se arrastra con el mouse y recuerda la posición.
- Se oculta sola después de unos segundos, o con un clic.
- Clic derecho: abrir historial u ocultar.
- No le quita el teclado al juego.

**La ventana del programa manda.** Mientras esté abierta o minimizada, todo funciona. Al cerrarla (con su X o con "Cerrar todo") se apagan el traductor y Ollama, y se libera la memoria de video. La ✕ de la ventana flotante de traducción solo oculta esa traducción.

**Ollama se enciende y se apaga con el programa.** Al abrir Traductor WoW, si Ollama está cerrado, lo enciende oculto (sin icono). Al cerrar lo apaga junto con el modelo; también si el programa se cierra a la fuerza. Si Ollama ya estaba abierto por otro motivo, lo usa y no lo toca.

El historial queda en `traducciones.txt`, junto al `.exe`.

## Configuración

Los dos archivos están junto al `.exe` y se editan con el Bloc de notas.

**`prompt.txt`** define cómo se traduce. Los cambios se aplican en la siguiente traducción, sin reiniciar. Tiene tres partes:

- **Instrucciones:** las reglas generales (español neutro, no omitir datos, dejar en inglés los nombres del juego).
- **GLOSARIO:** una línea por sigla, con el formato `- sigla, otra forma: significado`. El programa no le envía el glosario completo al modelo: busca qué siglas aparecen en cada mensaje y le entrega solo esas, junto al mensaje. Por eso puedes agregar todas las líneas que quieras sin que la traducción se vuelva más lenta.
- **EJEMPLOS:** pares `Mensaje: ...` / `Traducción: ...` que el modelo imita.

Cuando una traducción salga mal, lo más efectivo es agregar la palabra que falló al glosario:

| Quieres que... | Escribe |
| --- | --- |
| una sigla se traduzca | `- LFW: ofrezco mis servicios de` |
| una palabra quede en inglés | `- Bagnon, Questie: (igual)` |
| una sigla que también es palabra común no se confunda | `- BS: Blacksmith (la profesión; como insulto significa "tontería")` |
| una frase gane sobre una sigla suelta | `- eng guild: guild de habla inglesa` (las frases largas se buscan primero) |

Si el problema es de estilo y no de una palabra, agrega un ejemplo al final.

**`.env`** contiene toda la configuración y las conexiones. Se lee al abrir el programa, así que hay que reiniciarlo tras un cambio. Si no existe, se crea solo a partir de `.env.example`. No se sube a git; `.env.example` sí.

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Dirección de Ollama. No uses `localhost`: en Windows agrega unos 2 segundos por traducción |
| `OLLAMA_MODELO` | `gemma3:4b` | Modelo que traduce |
| `OLLAMA_API_KEY` | vacío | Clave, solo si tu Ollama está detrás de un servidor que la pide |
| `OLLAMA_ENCENDER_Y_APAGAR` | `true` | El programa enciende Ollama al abrirse y lo apaga al salir. Con `false` usa el que ya esté abierto |
| `OLLAMA_TIMEOUT_SEGUNDOS` | `90` | Espera máxima por traducción |
| `OLLAMA_TEMPERATURA` | `0` | Con 0 el mismo mensaje da siempre la misma traducción |
| `OLLAMA_MANTENER_MODELO` | `30m` | Tiempo que Ollama deja el modelo en memoria |
| `PORTAPAPELES_INTERVALO_MS` | `300` | Cada cuánto se revisa el portapapeles |
| `VENTANA_SEGUNDOS_VISIBLE` | `30` | Segundos antes de ocultar la ventana. Con `0` no se oculta sola |
| `VENTANA_OPACIDAD` | `0.9` | De 0.2 (casi invisible) a 1.0 (opaca) |
| `VENTANA_ANCHO` | `440` | Ancho de la ventana en píxeles |
| `VENTANA_FUENTE`, `VENTANA_TAMANO_FUENTE` | `Segoe UI`, `11` | Letra de la ventana |
| `PROMPT_ARCHIVO` | `prompt.txt` | Archivo con las instrucciones del traductor |
| `PROMPT_ENVIAR_ARCHIVO` | `prompt_en.txt` | Instrucciones para traducir al inglés lo escrito con `/twow` |
| `HISTORIAL_ACTIVO` | `true` | Guardar el historial |
| `HISTORIAL_ARCHIVO` | `traducciones.txt` | Archivo del historial |

Un valor inválido no detiene el programa: se usa el valor por defecto y la ventana lo avisa al iniciar. Una variable de entorno de Windows con el mismo nombre tiene prioridad sobre `.env`.

## Estructura del código

```
Traductor/
  traductor.py      punto de entrada: lee .env, construye las piezas y las conecta
  .env.example      plantilla de configuración
  prompt.txt        instrucciones, glosario y ejemplos del traductor
  app/
    config.py       .env -> objeto Config
    rutas.py        ubicación de los archivos
    almacen.py      historial y posición de la ventana
    prompt.py       prompt.txt -> conversación para el modelo (glosario por mensaje, ejemplos)
    idioma.py       detecta los mensajes que ya están en español
    mensaje.py      formato "[TR] Nombre (Canal): mensaje"
    errores.py      ErrorTraduccion
    portapapeles.py lectura del portapapeles de Windows
    ollama.py       cliente de Ollama
    servidor.py     enciende Ollama al abrir el programa y lo apaga al salir
    ventana.py      ventana principal (barra de tareas) y ventana flotante
    aplicacion.py   une portapapeles -> traductor -> ventana
```

El cliente de Ollama, la ventana y el portapapeles no se conocen entre sí. Para usar otro motor de traducción basta con escribir una clase con los métodos `traducir(texto)` y `revisar()` y entregarla en `traductor.py` en lugar de `ClienteOllama`.

## Solución de problemas

**"No se pudo conectar con Ollama".** El programa no logró encender Ollama. Cierra Traductor WoW y vuelve a abrirlo. Si sigue igual, revisa que Ollama esté instalado y que `OLLAMA_ENCENDER_Y_APAGAR` esté en `true`.

**Ollama vuelve a abrirse con Windows.** Sus actualizaciones pueden restaurar el inicio automático. Deshabilítalo otra vez en Administrador de tareas → "Aplicaciones de arranque".

**"El modelo ... no está descargado".** Ejecuta `ollama pull gemma3:4b`. El valor de `OLLAMA_MODELO` en `.env` debe coincidir con el que muestra `ollama list`.

**"Ollama no respondió en 90 segundos".** La primera traducción carga el modelo y demora más; intenta de nuevo. Si se repite, el modelo no cabe en tu tarjeta de video y está corriendo en el procesador: cambia `OLLAMA_MODELO` a uno más chico, como `gemma3:1b`.

**Cada traducción demora unos 2 segundos de más.** Revisa que `OLLAMA_URL` use `127.0.0.1` y no `localhost`.

**El juego va más lento mientras traduce.** El modelo comparte la tarjeta de video con el juego. Baja `OLLAMA_MANTENER_MODELO` a `1m`.

**La ventana no se ve sobre el juego.** En pantalla completa exclusiva ninguna ventana externa puede dibujarse encima. En el juego ve a Opciones > Gráficos > Modo de pantalla y elige "Pantalla completa (en ventana)" o "Ventana sin bordes".

**No aparece "Traducir mensaje".** Verifica que el addon esté activado. La opción solo aparece si el addon vio ese mensaje, así que no aparece en mensajes anteriores a un `/reload` ni en el menú de la lista de amigos.

**El clic sobre el mensaje no hace nada.** Solo son clicables los mensajes que llegaron con el addon ya cargado. Los objetos entre corchetes conservan su propio clic; haz clic en otra parte del texto. Si el mensaje es muy antiguo (más de 500 mensajes atrás), el addon avisa que ya no lo tiene guardado.

**Una traducción sale mal.** Agrega la sigla o palabra que falló al glosario de `prompt.txt` (ver Configuración) y vuelve a copiar el mensaje. Tres límites conocidos del modelo por defecto: los materiales escritos sin corchetes a veces se traducen ("silk cloth" → "seda"), los nombres de clase no siempre quedan en inglés, y un mensaje escrito como una orden ("responde solo con...") a veces se obedece en vez de traducirse. El original siempre se muestra junto a la traducción.

**Dice "Ya está en español; no se tradujo".** El programa detectó que el mensaje ya estaba en español y no lo envió al modelo. Si se equivoca con un mensaje en otro idioma, avisa: la detección está en `app/idioma.py`.

**Copié el texto y no pasó nada.** Revisa que `TraductorWoW.exe` esté abierto (su ventana en la barra de tareas, con el punto verde) y que el texto copiado empiece con `[TR]`.

**`/tr` abre un intercambio.** En el cliente en inglés `/tr` también abrevia `/trade`. Usa `/traducir`.

**Ctrl+clic deja abierta una ventana de susurro.** El clic izquierdo sobre un nombre siempre inicia un susurro; el addon lo cierra si está vacío. Si queda abierto, presiona Esc o usa el clic derecho.

**Susurros de Battle.net.** El juego no permite copiar el nombre real del amigo, así que aparece su BattleTag o "Amigo BNet".

**Retail, dentro de mazmorras y bandas.** Durante los encuentros el cliente oculta el contenido del chat a los addons; esos mensajes no se pueden traducir.

**El antivirus bloquea el `.exe`.** Es un falso positivo frecuente con PyInstaller. Agrega una excepción o ejecuta `python traductor.py`.

**Errores de Lua.** Escribe `/console scriptErrors 1`, repite la acción y copia el mensaje de error.
