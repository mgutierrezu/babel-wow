"""Traductor WoW: módulos del programa vigilante.

    rutas         dónde viven los archivos editables y los empaquetados
    config        lectura de .env -> objeto Config
    almacen       historial y estado de la ventana (archivos)
    prompt        prompt.txt -> conversación para el modelo (instrucciones, glosario, ejemplos)
    mensaje       formato "[TR] Nombre (Canal): mensaje"
    idioma        detecta los mensajes que ya están en español
    errores       ErrorTraduccion, el error común de los motores de traducción
    portapapeles  lectura del portapapeles de Windows
    ollama        cliente HTTP de Ollama
    servidor      enciende Ollama al abrir el programa y lo apaga al salir
    ventana       ventana principal (barra de tareas) y ventana flotante de traducciones
    aplicacion    une todo lo anterior

El traductor, la ventana y el portapapeles no se conocen entre sí: "aplicacion"
los recibe ya construidos desde traductor.py, que es el único que lee la configuración.
"""
