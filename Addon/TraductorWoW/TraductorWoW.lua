-- TraductorWoW
-- Guarda los mensajes del chat y permite copiarlos con el formato
--   [TR] Nombre (Canal): mensaje
-- para que el programa externo (TraductorWoW.exe) los traduzca.
-- El addon no puede escribir al portapapeles: solo muestra una cajita con el
-- texto seleccionado y el jugador presiona Ctrl+C.

local MAX_MENSAJES = 500
local PREFIJO = "[TR]"
local TEXTO_MENU = "Traducir mensaje"
local AVISO = "|cff33ff99TraductorWoW|r: "

-- Evento de chat -> nombre del canal que se muestra en la traducción.
local CANALES = {
    CHAT_MSG_SAY = "Decir",
    CHAT_MSG_YELL = "Gritar",
    CHAT_MSG_WHISPER = "Susurro",
    CHAT_MSG_PARTY = "Grupo",
    CHAT_MSG_PARTY_LEADER = "Grupo",
    CHAT_MSG_RAID = "Banda",
    CHAT_MSG_RAID_LEADER = "Banda",
    CHAT_MSG_RAID_WARNING = "Aviso de banda",
    CHAT_MSG_INSTANCE_CHAT = "Instancia",
    CHAT_MSG_INSTANCE_CHAT_LEADER = "Instancia",
    CHAT_MSG_GUILD = "Hermandad",
    CHAT_MSG_OFFICER = "Oficiales",
    CHAT_MSG_CHANNEL = "Canal",
    CHAT_MSG_BN_WHISPER = "Susurro BNet",
}

-- Nombres de los iconos de banda que se escriben entre llaves: {star}, {calavera}...
local ICONOS = {
    star = true, circle = true, diamond = true, triangle = true, moon = true,
    square = true, cross = true, x = true, skull = true,
    estrella = true, ["círculo"] = true, circulo = true, diamante = true,
    ["triángulo"] = true, triangulo = true, luna = true, cuadrado = true,
    cruz = true, calavera = true,
}

---------------------------------------------------------------------------
-- Almacén de mensajes
---------------------------------------------------------------------------

local porLinea = {}             -- lineID -> registro
local orden = {}                -- lineIDs en orden de llegada
local primero, siguiente = 1, 1 -- límites de la cola dentro de "orden"
local porJugador = {}           -- nombre en minúsculas -> último registro
local ultimo                    -- último mensaje recibido de otro jugador

local function NombreCorto(nombre)
    if Ambiguate then
        local ok, corto = pcall(Ambiguate, nombre, "short")
        if ok and corto and corto ~= "" then return corto end
    end
    return (nombre:gsub("%-.*$", ""))
end

local function Limpiar(texto)
    texto = texto:gsub("||", "\1")                   -- protege las barras escapadas
    texto = texto:gsub("|c%x%x%x%x%x%x%x%x", "")     -- color |cAARRGGBB
    texto = texto:gsub("|cn[^:]+:", "")              -- color con nombre |cnNOMBRE:
    texto = texto:gsub("|r", "")
    texto = texto:gsub("|H.-|h(.-)|h", "%1")         -- link -> [Objeto]
    texto = texto:gsub("|T.-|t", "")                 -- texturas
    texto = texto:gsub("|A.-|a", "")                 -- atlas
    texto = texto:gsub("|K.-|k", "")                 -- nombres protegidos de Battle.net
    texto = texto:gsub("|n", " ")
    texto = texto:gsub("{([^{}]+)}", function(nombre)
        nombre = nombre:lower()
        if ICONOS[nombre] or nombre:match("^rt%d$") then return "" end
    end)
    texto = texto:gsub("\1", "|")
    texto = texto:gsub("[\r\n]+", " "):gsub("%s+", " ")
    return (texto:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- Los nombres de Battle.net llegan como |Kq1|k y no se pueden copiar; se usa el BattleTag.
local function NombreBNet(idCuenta)
    if idCuenta and C_BattleNet and C_BattleNet.GetAccountInfoByID then
        local ok, info = pcall(C_BattleNet.GetAccountInfoByID, idCuenta)
        if ok and info and type(info.battleTag) == "string" and info.battleTag ~= "" then
            return (info.battleTag:gsub("#.*$", ""))
        end
    end
    return "Amigo BNet"
end

local function Guardar(registro)
    if registro.lineID then
        porLinea[registro.lineID] = registro
        orden[siguiente] = registro.lineID
        siguiente = siguiente + 1
        while siguiente - primero > MAX_MENSAJES do
            porLinea[orden[primero]] = nil
            orden[primero] = nil
            primero = primero + 1
        end
    end
    for _, clave in ipairs(registro.claves) do
        porJugador[clave] = registro
    end
    if not registro.propio then
        ultimo = registro
    end
end

local function AlRecibir(evento, texto, autor, _, nombreCanal, _, _, _, _, canalBase, _, lineID, guid, idBNet)
    -- En clientes nuevos el chat puede llegar como "valor secreto" durante encuentros.
    if issecretvalue and (issecretvalue(texto) or issecretvalue(autor)) then return end
    if type(texto) ~= "string" or type(autor) ~= "string" or autor == "" then return end

    local limpio = Limpiar(texto)
    if limpio == "" then return end

    local canal = CANALES[evento] or "Chat"
    if evento == "CHAT_MSG_CHANNEL" then
        local nombre = (type(canalBase) == "string" and canalBase ~= "" and canalBase) or nombreCanal
        if type(nombre) == "string" and nombre ~= "" then
            canal = (nombre:gsub("^%d+%.%s*", ""))
        end
    end

    local nombre, claves
    if evento == "CHAT_MSG_BN_WHISPER" then
        nombre = NombreBNet(idBNet)
        claves = { nombre:lower() }
    else
        nombre = NombreCorto(autor)
        claves = { autor:lower(), nombre:lower() }
    end

    Guardar({
        lineID = type(lineID) == "number" and lineID or nil,
        nombre = nombre,
        canal = canal,
        texto = limpio,
        claves = claves,
        propio = guid ~= nil and UnitGUID and guid == UnitGUID("player"),
    })
end

local function Buscar(lineID, nombre)
    lineID = tonumber(lineID)
    if lineID and porLinea[lineID] then return porLinea[lineID] end
    if type(nombre) == "string" and nombre ~= "" then
        return porJugador[nombre:lower()] or porJugador[NombreCorto(nombre):lower()]
    end
end

---------------------------------------------------------------------------
-- Cajita para copiar
---------------------------------------------------------------------------

local caja

local function Despues(segundos, funcion)
    if C_Timer and C_Timer.After then
        C_Timer.After(segundos, funcion)
    else
        funcion()
    end
end

-- Medidas de la cajita. El texto ocupa varias líneas si hace falta.
local CAJA_ANCHO = 480
local CAJA_MARGEN = 16       -- a cada lado del texto
local CAJA_ARRIBA = 28       -- espacio del título
local CAJA_ABAJO = 12
local CAJA_ALTURA = 2 / 5    -- borde inferior a 2/5 de la pantalla, medido desde abajo

-- Fondo oscuro con borde, común a las cajitas del addon.
local function PonerFondo(marco)
    if marco.SetBackdrop then
        marco:SetBackdrop({
            bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
            edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
            edgeSize = 14,
            insets = { left = 3, right = 3, top = 3, bottom = 3 },
        })
        marco:SetBackdropColor(0, 0, 0, 0.9)
    end
end

local function CrearCaja()
    local marco = CreateFrame("Frame", "TraductorWoWCaja", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    marco:SetSize(CAJA_ANCHO, 62)
    marco:SetFrameStrata("DIALOG")
    marco:SetClampedToScreen(true)
    PonerFondo(marco)
    marco:Hide()

    local titulo = marco:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    titulo:SetPoint("TOP", 0, -9)
    titulo:SetText("Presiona Ctrl+C para traducir  -  Esc para cerrar")

    -- Texto invisible con la misma letra y ancho que el editor: sirve para
    -- saber cuántas líneas ocupa el mensaje y dar ese alto a la cajita.
    local medidor = marco:CreateFontString(nil, "BACKGROUND", "ChatFontNormal")
    medidor:SetWidth(CAJA_ANCHO - 2 * CAJA_MARGEN)
    medidor:SetJustifyH("LEFT")
    medidor:SetAlpha(0)
    medidor:SetPoint("TOPLEFT", CAJA_MARGEN, -CAJA_ARRIBA)

    local editor = CreateFrame("EditBox", nil, marco)
    editor:SetMultiLine(true)
    editor:SetAutoFocus(false)
    editor:SetFontObject("ChatFontNormal")
    editor:SetPoint("TOPLEFT", CAJA_MARGEN, -CAJA_ARRIBA)
    editor:SetPoint("BOTTOMRIGHT", -CAJA_MARGEN, CAJA_ABAJO)

    local function Cerrar() marco:Hide() end
    editor:SetScript("OnEscapePressed", Cerrar)
    editor:SetScript("OnEnterPressed", Cerrar)
    -- Solo lectura: cualquier cambio del usuario se revierte.
    editor:SetScript("OnTextChanged", function(self, delUsuario)
        if delUsuario then
            self:SetText(marco.texto or "")
            self:HighlightText()
        end
    end)
    -- Tras Ctrl+C (o Cmd+C) se cierra sola; la pausa deja que el cliente copie primero.
    editor:SetScript("OnKeyDown", function(_, tecla)
        if (tecla == "C" or tecla == "X") and (IsControlKeyDown() or (IsMetaKeyDown and IsMetaKeyDown())) then
            Despues(0.15, Cerrar)
            if marco.alCopiar then Despues(0.25, marco.alCopiar) end
        end
    end)

    marco.titulo = titulo
    marco.editor = editor
    marco.medidor = medidor
    -- Permite cerrarla con Esc aunque el cursor ya no esté en la cajita.
    if UISpecialFrames then tinsert(UISpecialFrames, "TraductorWoWCaja") end
    return marco
end

-- Centra la cajita, con el borde inferior fijo a 2/5 de la pantalla. Como el
-- punto fijo es el de abajo, un mensaje largo la hace crecer hacia arriba.
local function Ubicar(marco)
    marco.medidor:SetText(marco.texto)
    local altoTexto = marco.medidor:GetStringHeight()
    if not altoTexto or altoTexto < 12 then altoTexto = 14 end
    marco:SetHeight(altoTexto + CAJA_ARRIBA + CAJA_ABAJO)
    marco:ClearAllPoints()
    marco:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, UIParent:GetHeight() * CAJA_ALTURA)
end

local TITULO_LEER = "Presiona Ctrl+C para traducir  -  Esc para cerrar"
local TITULO_ESCRIBIR = "Presiona Ctrl+C; luego pega la traducción con Ctrl+V"

-- Abre la cajita con un texto ya seleccionado. alCopiar (opcional) se ejecuta
-- después de que el jugador presiona Ctrl+C.
local function MostrarTexto(texto, tituloCaja, alCopiar)
    caja = caja or CrearCaja()
    caja.texto = texto
    caja.alCopiar = alCopiar
    caja.titulo:SetText(tituloCaja)
    if not pcall(Ubicar, caja) then
        caja:ClearAllPoints()
        caja:SetPoint("CENTER", 0, 0)
    end
    caja:Show()
    caja.editor:SetText(caja.texto)
    caja.editor:SetCursorPosition(0)
    caja.editor:SetFocus()
    caja.editor:HighlightText()
end

local function Mostrar(registro)
    if not registro then
        print(AVISO .. "no hay ningún mensaje guardado para traducir.")
        return
    end
    MostrarTexto(string.format("%s %s (%s): %s", PREFIJO, registro.nombre, registro.canal, registro.texto), TITULO_LEER)
end

---------------------------------------------------------------------------
-- Menú de clic derecho sobre el nombre en el chat
---------------------------------------------------------------------------

if Menu and Menu.ModifyMenu then
    -- Clientes modernos (Retail y los Classic actuales).
    local function Agregar(_, raiz, contexto)
        if type(contexto) ~= "table" then return end
        local ok, registro = pcall(Buscar, contexto.lineID, contexto.name)
        if not ok or not registro then return end -- p. ej. lista de amigos: no hay mensaje
        raiz:CreateDivider()
        raiz:CreateButton(TEXTO_MENU, function() Mostrar(registro) end)
    end
    for _, etiqueta in ipairs({ "MENU_UNIT_FRIEND", "MENU_UNIT_BN_FRIEND" }) do
        pcall(Menu.ModifyMenu, etiqueta, function(...) pcall(Agregar, ...) end)
    end
elseif type(UnitPopup_ShowMenu) == "function" and UIDropDownMenu_AddButton then
    -- Clientes antiguos (UIDropDownMenu). Se agrega el botón al final, sin tocar
    -- las tablas de UnitPopup para no contaminar el menú.
    pcall(hooksecurefunc, "UnitPopup_ShowMenu", function(menu, cual, _, nombre)
        pcall(function()
            if (UIDROPDOWNMENU_MENU_LEVEL or 1) ~= 1 then return end
            if cual ~= "FRIEND" and cual ~= "BN_FRIEND" then return end
            local registro = Buscar(menu and menu.lineID, nombre or (menu and menu.name))
            if not registro then return end
            local info = UIDropDownMenu_CreateInfo()
            info.text = TEXTO_MENU
            info.notCheckable = true
            info.func = function() Mostrar(registro) end
            UIDropDownMenu_AddButton(info)
        end)
    end)
end

---------------------------------------------------------------------------
-- Ctrl+clic sobre el nombre en el chat
---------------------------------------------------------------------------

-- El clic izquierdo normal abre un susurro; si quedó vacío, se cierra.
local function CerrarSusurroVacio()
    local editor
    if ChatFrameUtil and ChatFrameUtil.GetActiveWindow then
        editor = ChatFrameUtil.GetActiveWindow()
    elseif ChatEdit_GetActiveWindow then
        editor = ChatEdit_GetActiveWindow()
    end
    if not editor or editor:GetText() ~= "" then return end
    if ChatFrameUtil and ChatFrameUtil.DeactivateChat then
        ChatFrameUtil.DeactivateChat(editor)
    elseif ChatEdit_DeactivateChat then
        ChatEdit_DeactivateChat(editor)
    end
end

local function AlCtrlClic(link)
    if type(link) ~= "string" then return end
    local nombre, lineID = link:match("^player:([^:]+):(%d+)")
    if not lineID then
        lineID = link:match("^BNplayer:[^:]*:%d+:(%d+)")
    end
    if not nombre and not lineID then return end
    local registro = Buscar(lineID, nombre)
    if not registro then return end
    pcall(CerrarSusurroVacio)
    Mostrar(registro)
end

---------------------------------------------------------------------------
-- Clic sobre el texto del mensaje
---------------------------------------------------------------------------

-- El juego no deja seleccionar texto del chat. En su lugar, el texto de cada
-- mensaje se envuelve en un enlace propio del addon; al hacerle clic se abre
-- la cajita. Los enlaces que ya trae el mensaje (objetos, misiones) se respetan.
local ENLACE = "addon:TraductorWoW:"

local function HacerClicable(texto, lineID)
    local abre = "|H" .. ENLACE .. lineID .. "|h"
    local partes, posicion = {}, 1
    while true do
        local inicio, fin = texto:find("|H.-|h.-|h", posicion)
        local plano = texto:sub(posicion, (inicio or 0) - 1)
        -- Los códigos de color pegados a un objeto (|r al inicio, |cAARRGGBB al
        -- final) se dejan fuera del enlace.
        local cierre, resto = plano:match("^(|r)(.*)$")
        local cuerpo, color = (resto or plano):match("^(.-)(|c%x%x%x%x%x%x%x%x)$")
        cuerpo = cuerpo or resto or plano
        partes[#partes + 1] = cierre or ""
        if cuerpo:find("%S") then -- los trozos vacíos no se envuelven
            partes[#partes + 1] = abre .. cuerpo .. "|h"
        else
            partes[#partes + 1] = cuerpo
        end
        partes[#partes + 1] = color or ""
        if not inicio then break end
        partes[#partes + 1] = texto:sub(inicio, fin)
        posicion = fin + 1
    end
    return table.concat(partes)
end

local function FiltroChat(_, _, texto, ...)
    local lineID = select(10, ...)
    if issecretvalue and issecretvalue(texto) then return false end
    if type(texto) ~= "string" or type(lineID) ~= "number" then return false end
    local ok, nuevo = pcall(HacerClicable, texto, lineID)
    if not ok then return false end
    return false, nuevo, ...
end

local function AlClicEnMensaje(link)
    local lineID = type(link) == "string" and link:match("^" .. ENLACE .. "(%d+)")
    if not lineID then return false end
    local registro = Buscar(lineID)
    if registro then
        Mostrar(registro)
    else
        print(AVISO .. "ese mensaje es muy antiguo y ya no está guardado.")
    end
    return true
end

-- Solo en clientes que entienden los enlaces "addon:" (los que tienen EventRegistry);
-- en los antiguos un enlace desconocido daría error al hacerle clic.
local agregarFiltro = (ChatFrameUtil and ChatFrameUtil.AddMessageEventFilter) or ChatFrame_AddMessageEventFilter
if EventRegistry and agregarFiltro then
    for evento in pairs(CANALES) do
        pcall(agregarFiltro, evento, FiltroChat)
    end
end

pcall(hooksecurefunc, "SetItemRef", function(link, _, boton)
    local ok, atendido = pcall(AlClicEnMensaje, link)
    if ok and atendido then return end
    if boton == "LeftButton" and IsControlKeyDown() then
        pcall(AlCtrlClic, link)
    end
end)

---------------------------------------------------------------------------
-- Comando /tr y registro de eventos
---------------------------------------------------------------------------

local function Comando(argumento)
    local nombre = (argumento or ""):gsub("^%s+", ""):gsub("%s+$", "")
    if nombre == "" then
        Mostrar(ultimo)
    else
        local registro = Buscar(nil, nombre)
        if registro then
            Mostrar(registro)
        else
            print(AVISO .. "no hay mensajes guardados de \"" .. nombre .. "\".")
        end
    end
end

SLASH_TRADUCTORWOW1 = "/tr"
SLASH_TRADUCTORWOW2 = "/traducir"
SlashCmdList["TRADUCTORWOW"] = Comando

---------------------------------------------------------------------------
-- Comando /twow: escribir en español para enviar en inglés
---------------------------------------------------------------------------

-- El addon no puede recibir la traducción: el programa externo la deja en el
-- portapapeles y el jugador la pega. Para ahorrar un paso, tras el Ctrl+C se
-- abre la línea de chat, lista para pegar con Ctrl+V.
local PREFIJO_ESCRIBIR = "[EN]"

local function AbrirChat()
    pcall(function()
        if ChatFrameUtil and ChatFrameUtil.OpenChat then
            ChatFrameUtil.OpenChat("")
        elseif ChatFrame_OpenChat then
            ChatFrame_OpenChat("")
        end
    end)
end

local AbrirEntrada -- se define más abajo, junto al botón del minimapa

local function ComandoEscribir(argumento)
    local texto = (argumento or ""):gsub("^%s+", ""):gsub("%s+$", "")
    if texto == "" then
        AbrirEntrada() -- /twow sin texto abre el cuadro para escribirlo
        return
    end
    MostrarTexto(PREFIJO_ESCRIBIR .. " " .. texto, TITULO_ESCRIBIR, AbrirChat)
end

SLASH_TRADUCTORWOWESCRIBIR1 = "/twow"
SlashCmdList["TRADUCTORWOWESCRIBIR"] = ComandoEscribir

---------------------------------------------------------------------------
-- Cuadro para escribir en español y botón del minimapa
---------------------------------------------------------------------------

local entrada

local function CrearEntrada()
    local marco = CreateFrame("Frame", "TraductorWoWEntrada", UIParent, BackdropTemplateMixin and "BackdropTemplate" or nil)
    marco:SetSize(CAJA_ANCHO, 62)
    marco:SetFrameStrata("DIALOG")
    marco:SetClampedToScreen(true)
    PonerFondo(marco)
    marco:Hide()

    local titulo = marco:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    titulo:SetPoint("TOP", 0, -9)
    titulo:SetText("Escribe tu mensaje en español y presiona Enter  -  Esc para cerrar")

    local editor = CreateFrame("EditBox", nil, marco, "InputBoxTemplate")
    editor:SetAutoFocus(false)
    editor:SetHeight(20)
    editor:SetMaxLetters(400)
    editor:SetPoint("BOTTOMLEFT", 18, 10)
    editor:SetPoint("BOTTOMRIGHT", -14, 10)
    editor:SetScript("OnEscapePressed", function() marco:Hide() end)
    -- Enter pasa el texto al mismo flujo de /twow: cajita, Ctrl+C y pegar.
    editor:SetScript("OnEnterPressed", function(self)
        local texto = self:GetText() or ""
        marco:Hide()
        if texto:find("%S") then ComandoEscribir(texto) end
    end)

    marco.editor = editor
    if UISpecialFrames then tinsert(UISpecialFrames, "TraductorWoWEntrada") end
    return marco
end

AbrirEntrada = function()
    entrada = entrada or CrearEntrada()
    entrada:ClearAllPoints()
    entrada:SetPoint("BOTTOM", UIParent, "BOTTOM", 0, UIParent:GetHeight() * CAJA_ALTURA)
    entrada:Show()
    entrada.editor:SetText("")
    entrada.editor:SetFocus()
end

local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end

-- El botón va sobre el borde del minimapa, en el ángulo guardado.
local function UbicarBoton(boton)
    local angulo = math.rad(TraductorWoWDB.minimapa or 200)
    local radio = Minimap:GetWidth() / 2 + 5
    boton:ClearAllPoints()
    boton:SetPoint("CENTER", Minimap, "CENTER", radio * math.cos(angulo), radio * math.sin(angulo))
end

local function CrearBotonMinimapa()
    if not Minimap then return end
    -- Lo único que el addon guarda entre sesiones: dónde quedó el botón.
    TraductorWoWDB = type(TraductorWoWDB) == "table" and TraductorWoWDB or {}

    local boton = CreateFrame("Button", "TraductorWoWBotonMinimapa", Minimap)
    boton:SetSize(31, 31)
    boton:SetFrameStrata("MEDIUM")
    boton:SetFrameLevel(8)
    boton:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    boton:RegisterForDrag("LeftButton")
    boton:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")

    local icono = boton:CreateTexture(nil, "BACKGROUND")
    icono:SetTexture("Interface\\Icons\\INV_Misc_Note_01")
    icono:SetSize(19, 19)
    icono:SetPoint("TOPLEFT", 6, -6)
    local borde = boton:CreateTexture(nil, "OVERLAY")
    borde:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    borde:SetSize(53, 53)
    borde:SetPoint("TOPLEFT")

    boton:SetScript("OnClick", function(_, cual)
        if cual == "RightButton" then
            Mostrar(ultimo)
        else
            AbrirEntrada()
        end
    end)
    -- Arrastrar lo mueve alrededor del minimapa siguiendo al cursor.
    boton:SetScript("OnDragStart", function(self)
        self:SetScript("OnUpdate", function()
            local centroX, centroY = Minimap:GetCenter()
            local cursorX, cursorY = GetCursorPosition()
            local escala = Minimap:GetEffectiveScale()
            TraductorWoWDB.minimapa = math.deg(atan2(cursorY / escala - centroY, cursorX / escala - centroX))
            UbicarBoton(self)
        end)
    end)
    boton:SetScript("OnDragStop", function(self) self:SetScript("OnUpdate", nil) end)
    boton:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:AddLine("Traductor WoW")
        GameTooltip:AddLine("Clic: escribir en español para enviar en inglés", 1, 1, 1)
        GameTooltip:AddLine("Clic derecho: traducir el último mensaje recibido", 1, 1, 1)
        GameTooltip:AddLine("Arrastrar: mover el botón", 0.6, 0.6, 0.6)
        GameTooltip:Show()
    end)
    boton:SetScript("OnLeave", function() GameTooltip:Hide() end)
    UbicarBoton(boton)
end

local eventos = CreateFrame("Frame")
for evento in pairs(CANALES) do
    pcall(eventos.RegisterEvent, eventos, evento) -- algunos no existen en todos los clientes
end
eventos:RegisterEvent("PLAYER_LOGIN")
eventos:SetScript("OnEvent", function(_, evento, ...)
    if evento == "PLAYER_LOGIN" then
        -- /tr también es la abreviatura de /trade en el cliente en inglés;
        -- esto hace que gane el addon. /traducir funciona siempre.
        if type(hash_SlashCmdList) == "table" then
            hash_SlashCmdList["/TR"] = Comando
        end
        pcall(CrearBotonMinimapa)
        return
    end
    pcall(AlRecibir, evento, ...)
end)
