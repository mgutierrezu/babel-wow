# Traductor WoW

Traduce el chat de World of Warcraft entre inglés y español con una inteligencia artificial que corre en tu propio computador.

- **Lees en español:** haces clic en un mensaje del chat y aparece traducido en una ventana sobre el juego.
- **Escribes en español:** escribes tu mensaje, y te lo entrega en inglés listo para pegar en el chat.
- **Entiende la jerga:** sabe que `LFM` es "buscamos más jugadores", que `WTS` es "vendo" y que `IF` es Ironforge.
- **Es privado y gratuito:** la traducción se hace en tu equipo. No usa servicios pagados ni envía tu chat a internet.
- **No toca el juego:** no envía teclas ni clics. Solo lee lo que tú copias y muestra su propia ventana.

> Proyecto hecho por un jugador, sin relación con Blizzard Entertainment. World of Warcraft es una marca de Blizzard.

## Contenido

- [Cómo funciona](#cómo-funciona)
- [Requisitos y consumo](#requisitos-y-consumo)
- [Instalación](#instalación)
- [Uso](#uso)
- [Preguntas frecuentes](#preguntas-frecuentes)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Personalización](#personalización)
- [Solución de problemas](#solución-de-problemas)
- [Desinstalar](#desinstalar)
- [Para desarrolladores](#para-desarrolladores)
- [Licencia](#licencia)

## Cómo funciona

Son dos piezas que se comunican por el portapapeles de Windows:

1. **Un addon de WoW**, que te deja elegir un mensaje del chat y lo muestra en una cajita para copiarlo.
2. **Un programa de Windows**, que detecta lo que copiaste, lo traduce con un modelo de IA local ([Ollama](https://ollama.com)) y muestra el resultado.

```
Clic en un mensaje del chat ──> cajita con el texto ──Ctrl+C──> Traductor WoW ──> IA local
                                                                      │
                                                                      v
                                                        ventana con la traducción
```

El paso de **Ctrl+C lo haces siempre tú**. Los addons de WoW no pueden sacar texto del juego por su cuenta, y este proyecto no simula teclas para lograrlo.

## Requisitos y consumo

| Necesitas | Detalle |
| --- | --- |
| Sistema | Windows 10 u 11 |
| Juego | World of Warcraft instalado |
| Disco | Unos 6 GB libres |
| Internet | Solo para instalar (descarga cerca de 4 GB). Después funciona sin conexión |
| Tarjeta de video | Recomendada, con 6 GB de memoria o más |

### Elige el modelo según tu tarjeta de video

El modelo de IA es lo que más memoria de video ocupa, y la comparte con el juego. Hay tres opciones; el instalador sugiere una según tu tarjeta, y puedes cambiarla cuando quieras desde la ventana del programa.

| Modelo | Memoria de video | Descarga | Calidad | Para quién |
| --- | --- | --- | --- | --- |
| **Alto** (`gemma3:4b`) | 3,9 GB | 3,3 GB | La mejor | Tarjetas de 8 GB o más, si quieres traducciones más naturales |
| **Medio**, recomendado (`qwen2.5:3b`) | 2,4 GB | 1,9 GB | Buena | Tarjetas de 6 GB o más |
| **Bajo** (`qwen2.5:1.5b`) | 1,3 GB | 1,0 GB | Más tosca, pero se entiende | Tarjetas de 4 GB, o si el juego va lento |

La calidad se comparó con 32 mensajes de chat en ambos sentidos. El nivel Bajo escribe bien en inglés, pero su español es menos natural. El glosario y los ejemplos del proyecto se ajustaron con el nivel Alto, así que los otros dos tienen margen de mejora.

El modelo del nivel Medio, `qwen2.5:3b`, se distribuye con la "Qwen Research License", más restrictiva que la de los otros dos. Revísala con `ollama show qwen2.5:3b --license` si piensas darle un uso que no sea personal; en ese caso puedes elegir cualquiera de los otros.

**Cuánto consume mientras lo usas**, medido con el nivel Medio en un equipo con una RTX 5070 de 12 GB:

| Recurso | Consumo |
| --- | --- |
| Memoria de video | 2,4 GB mientras el programa está abierto |
| Memoria RAM | 0,7 GB |
| Tiempo por traducción | 0,15 segundos |
| Al abrir el programa | 5 a 10 segundos: enciende la IA y carga el modelo |
| Uso de la tarjeta de video | Solo mientras traduce; el resto del tiempo, 0 % |

Con el juego abierto y el modelo cargado, ese equipo usó 6 GB de sus 12 GB de memoria de video. En una tarjeta con menos memoria, el juego y el traductor compiten por ella. El nivel Alto ocupa 1,5 GB más de video.

Sin una tarjeta de video adecuada el modelo corre en el procesador. Funciona, pero cada traducción tarda bastante más; no está medido.

Al cerrar el programa se apaga la IA y se libera toda esa memoria. No queda nada corriendo en segundo plano ni se inicia con Windows.

## Instalación

### Opción rápida: el instalador

1. Descarga `InstalarTraductorWoW.exe` desde la [página de versiones](https://github.com/mgutierrezu/babel-wow/releases).
2. Cierra World of Warcraft y abre el instalador.
3. Si Windows muestra "Windows protegió su PC", haz clic en "Más información" y luego en "Ejecutar de todas formas". El aviso aparece porque el programa no está firmado digitalmente.
4. Indica la carpeta de tu versión de WoW. El instalador intenta encontrarla solo; si no, búscala con "Examinar". Ejemplo:

   ```
   C:\Program Files (x86)\World of Warcraft\_classic_era_
   ```

   Es la carpeta que tiene dentro `Interface` y `WTF`. Cada versión del juego tiene la suya (`_retail_`, `_classic_era_`, `_classic_`, `_anniversary_`).
5. Elige el modelo de traducción. El instalador marca el sugerido para tu tarjeta de video; si dudas, déjalo así.
6. Haz clic en "Instalar" y espera. Puede tardar varios minutos por las descargas.
7. Al terminar aparece una pantalla de verificación. Cuando las cinco líneas estén en verde, está listo.

Si tiene que descargar el instalador de Ollama, antes de ejecutarlo comprueba que venga firmado digitalmente por Ollama Inc.; si no, se detiene sin ejecutarlo.

El instalador hace cuatro cosas: instala Ollama si no lo tienes, descarga el modelo de traducción, copia el addon a tu WoW, e instala el programa en `%LOCALAPPDATA%\TraductorWoW` con un acceso directo en el Escritorio. Si lo vuelves a ejecutar no descarga nada de nuevo y conserva tu configuración.

### Opción manual

Si prefieres no usar el instalador, o quieres compilarlo tú, sigue los pasos de [Para desarrolladores](#para-desarrolladores).

## Uso

### Antes de jugar

1. Abre **Traductor WoW** desde el Escritorio. Aparece su ventana en la barra de tareas. Cuando aparece el visto bueno verde y dice "LLM (Medio) funcionando", está listo. Mientras enciende, un indicador gira en amarillo; si algo falla, queda en rojo con la explicación.
2. Puedes minimizarla, pero **no la cierres**: mientras esté abierta todo funciona, y al cerrarla se apagan el traductor y la IA.
3. Abre WoW. En la pantalla de personajes entra a "AddOns" y revisa que "Traductor WoW" esté marcado.
4. En Opciones → Gráficos, pon el juego en **"Pantalla completa (en ventana)"**. En pantalla completa exclusiva ninguna ventana externa puede verse encima del juego.

### Leer un mensaje en español

1. Haz **clic sobre el texto de un mensaje** en el chat.
2. Se abre una cajita con el texto seleccionado. Presiona **Ctrl+C**.
3. Aparece la traducción en una ventana flotante.

### Escribir en inglés

1. Haz clic en el **botón del minimapa** (icono de una nota), escribe tu mensaje en español y presiona Enter. También puedes escribirlo en el chat: `/twow hola, busco grupo para Deadmines`.
2. Se abre la cajita con tu mensaje. Presiona **Ctrl+C**.
3. Aparece la traducción (`hi, LFG Deadmines`) con el aviso "Copiado": ya está en tu portapapeles.
4. El chat queda abierto. Pega con **Ctrl+V** y presiona Enter.

Mientras traduce, el portapapeles queda vacío: si pegas antes de tiempo no sale nada, en vez de enviar tu texto en español. Si la traducción supera los 255 caracteres que admite el chat de WoW, la ventana lo advierte en rojo.

Como vas a enviar un texto que quizás no entiendas del todo, léelo antes de presionar Enter. Las frases simples salen mejor.

### Todas las formas de usarlo

| Acción | Resultado |
| --- | --- |
| Clic en el texto de un mensaje | Traduce ese mensaje |
| Clic derecho en el nombre → "Traducir mensaje" | Traduce ese mensaje |
| Ctrl+clic en el nombre | Traduce ese mensaje |
| `/tr` o `/traducir` | Traduce el último mensaje recibido |
| `/tr Nombre` | Traduce el último mensaje de ese jugador |
| Botón del minimapa, clic | Abre el cuadro para escribir en español |
| Botón del minimapa, clic derecho | Traduce el último mensaje recibido |
| `/twow mensaje` | Traduce tu mensaje al inglés |
| `/twow` | Abre el cuadro para escribir en español |

El botón del minimapa se arrastra alrededor del minimapa y recuerda su lugar.

### La ventana de la traducción

- Se arrastra con el mouse y recuerda la posición.
- Se oculta sola a los 30 segundos, con un clic, o con su ✕.
- No le quita el teclado al juego.
- Muestra siempre el mensaje original junto a la traducción.

La ✕ de esta ventana solo oculta la traducción. Para salir del programa, cierra la ventana "Traductor WoW" de la barra de tareas.

## Preguntas frecuentes

**¿Me pueden sancionar por usarlo?**
El programa no envía teclas ni clics al juego, no lee su memoria y no automatiza nada: solo lee tu portapapeles después de que tú presionas Ctrl+C, y deja un texto copiado para que lo pegues tú. El addon usa únicamente las funciones que el juego ofrece a los addons. Dicho eso, este proyecto no tiene ninguna aprobación de Blizzard, y la decisión de usarlo es tuya.

**¿Envía mi chat a alguna parte?**
No. La traducción la hace un modelo que corre en tu computador. Internet solo se usa durante la instalación, para descargar Ollama y el modelo.

**¿Lee todo lo que copio?**
Sí: para saber si un texto viene del addon tiene que mirar el portapapeles cada vez que copias algo, aunque sea una contraseña. Si no empieza con `[TR]` o `[EN]` lo descarta en el momento: no lo guarda, no lo muestra y no lo envía a ninguna parte. Puedes comprobarlo en `Traductor/app/aplicacion.py`.

**¿Qué guarda en mi equipo?**
El historial de traducciones (`traducciones.txt`), que incluye los mensajes de otros jugadores con su nombre. Se limpia solo al llegar a 10 MB y se puede apagar con `HISTORIAL_ACTIVO=false`.

**¿Tiene algún costo?**
No. El programa es de código abierto, y Ollama y los modelos que usa son gratuitos.

**¿Con qué versiones de WoW funciona?**
Está probado en un cliente Classic (versión 1.60). El addon también declara compatibilidad con Classic Era, TBC Anniversary, MoP Classic y Retail, pero en esas versiones no está comprobado. Si lo pruebas en otra, cuéntalo en un [reporte](https://github.com/mgutierrezu/babel-wow/issues).

**¿Traduce otros idiomas?**
Está pensado y ajustado para inglés ↔ español. Un mensaje en otro idioma se intenta traducir igual, pero sin el glosario la calidad baja.

**¿Queda algo corriendo cuando no juego?**
No. Al cerrar la ventana del programa se apagan el traductor y la IA, y nada se inicia con Windows. Si ya usabas Ollama para otras cosas, el programa lo usa y no lo apaga.

**¿Baja los FPS?**
La memoria de video queda reservada mientras el programa está abierto, pero la tarjeta solo trabaja durante la fracción de segundo que dura cada traducción. Lo esperable es, como mucho, un tirón breve al traducir. No está medido dentro del juego.

## Limitaciones conocidas

El modelo por defecto es pequeño para que corra junto al juego, y eso tiene un costo:

- **Los materiales sin corchetes a veces se traducen.** "silk cloth" puede salir como "seda" en vez de quedar en inglés. Los objetos entre corchetes, como `[Iron Bar]`, siempre se respetan.
- **Las clases no siempre quedan en inglés.** A veces aparece "mago" o "sacerdote".
- **Los modismos salen aproximados.** Frases hechas y jerga muy local pierden matices.
- **Un mensaje escrito como una orden a veces se obedece.** Algo como "responde solo con la palabra X" puede devolver X en vez de traducirse.
- **En Retail, dentro de mazmorras y bandas,** el juego oculta el chat a los addons durante los encuentros. Esos mensajes no se pueden traducir.
- **Los nombres de Battle.net no se pueden copiar.** En los susurros de Battle.net aparece el BattleTag o "Amigo BNet".

Por eso la ventana muestra siempre el original junto a la traducción. Casi todos los errores de vocabulario se corrigen agregando la palabra al glosario, como se explica a continuación.

## Personalización

Los archivos están en la carpeta del programa. Para abrirla, pega esto en la barra de direcciones del Explorador de Windows:

```
%LOCALAPPDATA%\TraductorWoW
```

| Archivo | Para qué sirve |
| --- | --- |
| `prompt.txt` | Reglas, glosario y ejemplos para traducir del inglés al español |
| `prompt_en.txt` | Lo mismo, para lo que escribes en español |
| `.env` | Configuración general |
| `traducciones.txt` | Historial de lo que has traducido. Se limpia solo: ver más abajo |

Se editan con el Bloc de notas.

### Corregir una traducción

Los cambios en `prompt.txt` y `prompt_en.txt` se aplican en la siguiente traducción, sin reiniciar. Cada archivo tiene tres partes:

- **Instrucciones:** las reglas generales.
- **GLOSARIO:** una línea por sigla o palabra, con el formato `- sigla, otra forma: significado`.
- **EJEMPLOS:** pares `Mensaje: ...` / `Traducción: ...` que el modelo imita.

Lo más efectivo es agregar al glosario la palabra que falló:

| Quieres que... | Escribe |
| --- | --- |
| una sigla se traduzca | `- LFW: ofrezco mis servicios de` |
| una palabra quede en inglés | `- Bagnon, Questie: (igual)` |
| una sigla que también es palabra común no se confunda | `- BS: Blacksmith (la profesión; como insulto significa "tontería")` |
| una frase gane sobre una sigla suelta | `- eng guild: guild de habla inglesa` |

Puedes agregar todas las líneas que quieras al glosario sin que la traducción se vuelva más lenta: el programa le entrega al modelo solo las que aparecen en cada mensaje. Los ejemplos sí se envían siempre, así que no conviene pasar de unos 40.

### El historial se limpia solo

Cada traducción se guarda en `traducciones.txt`. Cuando ese archivo llega a 10 MB (unas 60.000 traducciones), pasa a llamarse `traducciones.anterior.txt` y se empieza uno nuevo; el "anterior" que hubiera se borra. Así siempre conservas lo más reciente y el historial nunca ocupa más de 20 MB. El límite se cambia con `HISTORIAL_MAXIMO_MB`, y el historial se apaga con `HISTORIAL_ACTIVO=false`.

### Cambiar de modelo

En la ventana del programa hay un selector "Modelo de traducción". Al elegir otro, el indicador gira en amarillo con un porcentaje mientras se hace el cambio: el programa descarga el modelo si hace falta, libera la memoria del anterior, carga el nuevo y recuerda la elección. Al terminar vuelve el visto bueno con el nombre del modelo en uso. No hay que reiniciar nada. Si la descarga falla, vuelve al modelo que estaba funcionando.

### Configuración general

El archivo `.env` se lee al abrir el programa, así que hay que reiniciarlo después de un cambio. Las opciones más útiles:

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `VENTANA_SEGUNDOS_VISIBLE` | `30` | Segundos antes de ocultar la traducción. Con `0` no se oculta sola |
| `VENTANA_OPACIDAD` | `0.9` | De 0.2 (casi invisible) a 1.0 (opaca) |
| `VENTANA_ANCHO` | `440` | Ancho de la ventana en píxeles |
| `VENTANA_FUENTE`, `VENTANA_TAMANO_FUENTE` | `Segoe UI`, `11` | Letra de la ventana |
| `OLLAMA_MODELO` | `qwen2.5:3b` | Modelo que traduce. Se cambia desde la ventana del programa; aquí puedes poner cualquier otro de Ollama |
| `OLLAMA_MANTENER_MODELO` | `30m` | Tiempo que el modelo queda en memoria sin usarse |
| `OLLAMA_ENCENDER_Y_APAGAR` | `true` | El programa enciende Ollama al abrirse y lo apaga al cerrarse. Con `false` usa el que ya esté abierto |
| `HISTORIAL_ACTIVO` | `true` | Guardar el historial |

<details>
<summary>Resto de las variables</summary>

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Dirección de Ollama. No uses `localhost`: en Windows agrega unos 2 segundos por traducción |
| `OLLAMA_API_KEY` | vacío | Clave, solo si tu Ollama está detrás de un servidor que la pide |
| `OLLAMA_TIMEOUT_SEGUNDOS` | `90` | Espera máxima por traducción |
| `OLLAMA_TEMPERATURA` | `0` | Con 0, el mismo mensaje da siempre la misma traducción |
| `PORTAPAPELES_INTERVALO_MS` | `300` | Cada cuánto se revisa el portapapeles |
| `PROMPT_ARCHIVO` | `prompt.txt` | Archivo de instrucciones, inglés a español |
| `PROMPT_ENVIAR_ARCHIVO` | `prompt_en.txt` | Archivo de instrucciones, español a inglés |
| `HISTORIAL_ARCHIVO` | `traducciones.txt` | Archivo del historial |
| `HISTORIAL_MAXIMO_MB` | `10` | Tamaño máximo del historial. Con `0` no se limita |

</details>

Un valor inválido no detiene el programa: se usa el valor por defecto y la ventana lo avisa. Una variable de entorno de Windows con el mismo nombre tiene prioridad sobre el archivo.

## Solución de problemas

### Instalación

**"Windows protegió su PC".** "Más información" → "Ejecutar de todas formas". Aparece porque el programa no está firmado.

**El antivirus bloquea el programa.** Es un falso positivo frecuente en programas hechos con Python y PyInstaller. Agrega una excepción, o compílalo tú desde el código.

**"Windows no dejó copiar el addon".** Haz clic derecho sobre el instalador y elige "Ejecutar como administrador".

**No aparece el addon en el juego.** Probablemente se instaló en la carpeta de otra versión de WoW. Vuelve a abrir el instalador y elige la correcta. Si aparece como "desactualizado", marca "Cargar addons desactualizados".

### El programa

**"No se pudo conectar con Ollama".** Cierra Traductor WoW y vuelve a abrirlo. Si sigue igual, revisa que Ollama esté instalado y que `OLLAMA_ENCENDER_Y_APAGAR` esté en `true`.

**"El modelo ... no está descargado".** Elígelo de nuevo en el selector de la ventana del programa: lo descarga solo.

**"Ollama no respondió en 90 segundos".** La primera traducción carga el modelo y demora más; intenta de nuevo. Si se repite, el modelo no cabe en tu tarjeta de video y está corriendo en el procesador: cambia a un nivel más bajo en la ventana del programa.

**Copié el texto y no pasó nada.** Revisa que Traductor WoW esté abierto, con el visto bueno verde.

**La ventana de la traducción no se ve sobre el juego.** Pon el juego en "Pantalla completa (en ventana)" en Opciones → Gráficos.

**El juego va más lento.** El modelo comparte la tarjeta de video con el juego. Cambia a un nivel más bajo en la ventana del programa, o baja la calidad gráfica.

**Ollama vuelve a abrirse con Windows.** Sus actualizaciones pueden restaurar el inicio automático. Se deshabilita en Administrador de tareas → "Aplicaciones de arranque".

### Dentro del juego

**El clic sobre un mensaje no hace nada.** Solo son clicables los mensajes que llegaron con el addon ya cargado. Los objetos entre corchetes conservan su propio clic: haz clic en otra parte del texto.

**No aparece "Traducir mensaje" en el clic derecho.** La opción solo aparece si el addon vio ese mensaje. No aparece en la lista de amigos.

**`/tr` abre un intercambio.** En el cliente en inglés, `/tr` también abrevia `/trade`. Usa `/traducir`.

**Ctrl+clic deja abierta una ventana de susurro.** El clic izquierdo sobre un nombre siempre inicia un susurro; el addon lo cierra si está vacío. Si queda abierto, presiona Esc.

**Dice "Ya está en español; no se tradujo".** El programa detectó que el mensaje ya estaba en español y no lo envió al modelo.

**Sale un error del addon.** Escribe `/console scriptErrors 1` en el chat, repite la acción y copia el mensaje en un [reporte](https://github.com/mgutierrezu/babel-wow/issues).

## Desinstalar

1. Cierra Traductor WoW.
2. Borra la carpeta `%LOCALAPPDATA%\TraductorWoW` y el acceso directo del Escritorio.
3. Borra la carpeta `TraductorWoW` dentro de `Interface\AddOns` de tu WoW.
4. Si no usas Ollama para otra cosa, desinstálalo desde Configuración → Aplicaciones de Windows. Eso libera los 3 GB del modelo.

## Para desarrolladores

### Probar desde el código

Necesitas [Python 3.10 o superior](https://www.python.org/downloads/) y [Ollama](https://ollama.com/download). El programa no usa librerías externas para funcionar.

```
ollama pull qwen2.5:3b
python Traductor\traductor.py
```

La primera vez crea `Traductor\.env` a partir de `.env.example`.

Para el addon, copia `Addon\TraductorWoW` a `Interface\AddOns` de tu versión del juego. Si vas a modificarlo, conviene un enlace de carpeta para no copiarlo en cada cambio:

```
New-Item -ItemType Junction -Path "C:\Program Files (x86)\World of Warcraft\_classic_era_\Interface\AddOns\TraductorWoW" -Target "<ruta del proyecto>\Addon\TraductorWoW"
```

Con el enlace, los cambios al `.lua` se aplican con `/reload`. Los cambios al `.toc` requieren reiniciar el juego.

### Compilar

```
Traductor\build.bat     genera Traductor\dist\TraductorWoW.exe
Instalador\build.bat    genera output\InstalarTraductorWoW.exe y output\LEEME.txt
```

El segundo necesita el resultado del primero. La carpeta `output` es lo que se comparte.

### Estructura

```
Addon/TraductorWoW/     addon de WoW (Lua)
Traductor/
  traductor.py          punto de entrada: lee .env, construye las piezas y las conecta
  prompt.txt            instrucciones, glosario y ejemplos: inglés a español
  prompt_en.txt         lo mismo: español a inglés
  .env.example          plantilla de configuración
  app/
    config.py           .env -> objeto Config
    modelos.py          modelos que se ofrecen en el instalador y en la ventana
    rutas.py            ubicación de los archivos
    almacen.py          historial y posición de la ventana
    prompt.py           archivo de prompt -> conversación para el modelo
    idioma.py           detecta los mensajes que ya están en español
    mensaje.py          formatos "[TR] Nombre (Canal): mensaje" y "[EN] mensaje"
    errores.py          ErrorTraduccion
    portapapeles.py     portapapeles de Windows
    ollama.py           cliente de Ollama
    servidor.py         enciende Ollama al abrir el programa y lo apaga al salir
    ventana.py          ventana principal y ventana flotante
    aplicacion.py       une portapapeles -> traductor -> ventana
Instalador/
  instalador.py         instalador con pantalla de verificación
  LEEME.txt             instrucciones que acompañan al instalador
```

### Decisiones de diseño

- **El portapapeles como canal.** Un addon no puede escribir archivos en tiempo real ni abrir conexiones, y el programa no debe leer la memoria del juego. Copiar con Ctrl+C es lo único que cumple ambas condiciones.
- **Glosario por mensaje.** Un modelo de 4 mil millones de parámetros ignora un glosario largo. El programa busca qué siglas aparecen en cada mensaje y le entrega solo esas, junto al mensaje. En las pruebas esto mejoró más la calidad que cualquier cambio en las reglas.
- **Ejemplos como conversación.** Los ejemplos se envían como turnos ya respondidos, no como texto dentro de las instrucciones. Así el modelo imita el formato y responde solo con la traducción.
- **Piezas reemplazables.** El cliente de Ollama, las ventanas y el portapapeles no se conocen entre sí. Para usar otro motor de traducción basta una clase con los métodos `traducir(texto)` y `revisar()`, entregada en `traductor.py` en lugar de `ClienteOllama`.
- **Ollama atado al programa.** El servidor se lanza dentro de un "job" de Windows, de modo que se cierra junto con el programa aunque este termine a la fuerza.

### Contribuir

Los reportes y las mejoras son bienvenidos en [GitHub](https://github.com/mgutierrezu/babel-wow/issues). Lo que más ayuda:

- Mensajes que se tradujeron mal, con el original y lo que salió. Normalmente se resuelven con una línea en el glosario.
- Resultados en versiones de WoW distintas de Classic.
- Mediciones de consumo y velocidad en otras tarjetas de video.

El repositorio usa ramas `feature/` integradas a `develop`, y mensajes de commit con el formato `tipo(ámbito): descripción`.

## Licencia

[MIT](LICENSE). Puedes usarlo, modificarlo y compartirlo libremente.

Este proyecto no está afiliado a Blizzard Entertainment ni cuenta con su respaldo. World of Warcraft y Warcraft son marcas de Blizzard Entertainment, Inc.
