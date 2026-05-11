# UTP MCP Server 🎓

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

Servidor MCP (Model Context Protocol) para conectar asistentes de IA con las plataformas académicas de la **Universidad Tecnológica del Perú (UTP)**.

Compatible con **cualquier cliente MCP**: Claude Desktop, Qwen, Cursor, VS Code, etc.

## ¿Qué puede hacer?

| Tool | Descripción |
|------|------------|
| `get_courses` | Ver cursos activos (acepta filtro `career`='PREG'/'PRED') |
| `get_course_materials` | Extrae PDFs, PPTs y sílabo del curso |
| `get_pending_assignments` | Ver tareas y evaluaciones pendientes |
| `get_activity_detail` | Detalle de una tarea (calificación, etc.) |
| `get_course_content` | Contenido completo de un curso |
| `get_periods` | Todos los periodos académicos |
| `get_grade_record` | Record histórico completo de notas |
| `get_weekly_schedule` | Horario semanal con clases, horas y modalidad |
| `get_pending_payments` | Consultar deudas y cuotas pendientes |
| `get_payment_history` | Consultar el historial de pagos de un ciclo |
| `get_procedures_status` | Ver el estado de trámites académicos |
| `get_contacts` | Directorio de contactos (compañeros y docentes) |
| `search_directory` | Buscar alumnos o docentes por nombre y apellido |
| `get_messages` | Conversaciones con docentes/compañeros |
| `read_conversation` | Leer mensajes de una conversación |
| `send_message` | Enviar mensaje a docente/compañero (soporta adjuntos locales) |
| `get_course_forums` | Ver lista de foros disponibles en un curso |
| `get_forum_threads` | Leer los hilos y respuestas de un foro |
| `reply_to_forum` | Publicar una respuesta o nuevo tema en un foro |
| `delete_forum_reply` | Eliminar un comentario propio en un foro |

## Instalación

```bash
pip install mcp httpx python-dotenv
```

## Configuración

1. Copia el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Edita `.env` con tus datos:
```env
# UTP MCP Server - Credenciales
UTP_USERNAME=U12345678
UTP_PASSWORD=tu_contraseña_aqui

# Class Platform IDs (se obtienen una vez desde el browser)
CLASS_USER_UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLASS_TENANT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy
```

3. Para obtener `CLASS_USER_UUID` y `CLASS_TENANT_ID`:
   La forma más fácil y rápida es inyectar un pequeño script en tu navegador que atrape los IDs:
   - Abre https://class.utp.edu.pe/ e inicia sesión.
   - Presiona `F12` para abrir las DevTools y ve a la pestaña **Console** (Consola).
   - Pega el siguiente código y presiona Enter:
     ```javascript
     (function() {
         const XHR = XMLHttpRequest.prototype;
         const open = XHR.open;
         const send = XHR.send;
         const setRequestHeader = XHR.setRequestHeader;
         
         XHR.open = function() {
             this._requestHeaders = {};
             return open.apply(this, arguments);
         };
         
         XHR.setRequestHeader = function(header, value) {
             this._requestHeaders[header.toLowerCase()] = value;
             return setRequestHeader.apply(this, arguments);
         };
         
         XHR.send = function() {
             const uid = this._requestHeaders['user-id'];
             const tid = this._requestHeaders['x-tenant-id'];
             if(uid && tid) {
                 console.log("\n✅ ¡IDs ENCONTRADOS! Cópialos a tu .env:\n");
                 console.log("CLASS_USER_UUID=" + uid);
                 console.log("CLASS_TENANT_ID=" + tid + "\n");
             }
             return send.apply(this, arguments);
         };
         console.log("Script activado. Ahora haz clic en cualquier botón dentro de la página...");
     })();
     ```
   - Ahora, haz clic en cualquier botón dentro de la página.
   - ¡Listo! Los IDs aparecerán impresos en la consola listos para copiar.

## Uso

### Con cualquier cliente MCP (stdio)

```bash
python -m utp_mcp.server
```

### Con Claude Desktop

Agrega en `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "utp": {
      "command": "python",
      "args": ["-m", "utp_mcp.server"],
      "cwd": "C:/Users/menca/Desktop/utp-mcp",
      "env": {
        "UTP_USERNAME": "U12345678",
        "UTP_PASSWORD": "tu_contraseña",
        "CLASS_USER_UUID": "xxxxxxxx-xxxx-...",
        "CLASS_TENANT_ID": "yyyyyyyy-yyyy-..."
      }
    }
  }
}
```

### Con VS Code (Roo Code / Cline)

En la extensión Roo Code o Cline, ve a la configuración de MCP Servers y agrega:

```json
{
  "mcpServers": {
    "utp": {
      "command": "python",
      "args": ["-m", "utp_mcp.server"],
      "cwd": "C:/Ruta/A/Tu/Directorio/utp-mcp",
      "env": {
        "UTP_USERNAME": "U12345678",
        "UTP_PASSWORD": "tu_contraseña",
        "CLASS_USER_UUID": "xxxxxxxx-xxxx-...",
        "CLASS_TENANT_ID": "yyyyyyyy-yyyy-..."
      }
    }
  }
}
```

### Con Gemini CLI

Puedes levantar el servidor y conectarlo a la CLI oficial de Gemini configurando el MCP en su entorno de ejecución, o pasándolo directamente mediante el archivo de configuración `mcp.json`:

```json
{
  "mcpServers": {
    "utp-mcp": {
      "command": "python",
      "args": [
        "-m",
        "utp_mcp.server"
      ],
      "cwd": "C:/Ruta/A/Tu/Directorio/utp-mcp",
      "env": {
        "UTP_USERNAME": "U12345678",
        "UTP_PASSWORD": "tu_contraseña",
        "CLASS_USER_UUID": "xxxxxxxx-xxxx-...",
        "CLASS_TENANT_ID": "yyyyyyyy-yyyy-..."
      }
    }
  }
}
```

### Con Qwen / otros clientes MCP

Configura según la documentación de tu cliente MCP apuntando a:
```
command: python -m utp_mcp.server
transport: stdio
```

---

## 🤖 Instructivo para Agentes LLM (OpenClaw, Hermes, Cline, etc.)

> **System Prompt / LLM Instruction:** Si eres un agente autónomo y el usuario te ha pedido instalar, configurar o utilizar este servidor MCP, sigue estrictamente estas instrucciones:

1. **Instalación de Dependencias:** Ejecuta `pip install httpx python-dotenv mcp` en el entorno donde correrás el servidor.
2. **Variables de Entorno:** Debes solicitar al usuario (si no te las ha dado) las credenciales de `UTP_USERNAME` y `UTP_PASSWORD`.
3. **Obtención de UUIDs (MANDATORIO):** Informa al usuario que DEBE proveer `CLASS_USER_UUID` y `CLASS_TENANT_ID`. Puedes darle el script de inyección en navegador provisto en la sección de [Configuración](#configuración) para que él lo haga manualmente y te pase los IDs.
4. **Configuración del Cliente:** Agrega la configuración JSON de este servidor en el archivo de configuración de tu propio sistema MCP (`mcp.json`, `claude_desktop_config.json`, etc.). Asegúrate de apuntar el `cwd` (Current Working Directory) a la ruta absoluta donde clonaste este repositorio y definir `python` como el comando base.
5. **Reinicio:** Una vez que edites el archivo de configuración JSON de MCP, reinicia tu servicio MCP o recarga la ventana de tu IDE para detectar las herramientas del `utp-mcp`.

## Arquitectura

```
                    ┌─────────────────────┐
                    │   AI Client (MCP)   │
                    │  Qwen/Claude/etc.   │
                    └────────┬────────────┘
                             │ stdio
                    ┌────────▼────────────┐
                    │  UTP MCP Server     │
                    │  (Python, ~15MB)    │
                    ├─────────────────────┤
                    │  Auth Manager       │
                    │  (Keycloak ROPC)    │
                    ├──────┬──────────────┤
                    │      │              │
              ┌─────▼──┐ ┌▼──────────┐   │
              │Portal  │ │Class      │   │
              │GraphQL │ │REST API   │   │
              └────┬───┘ └────┬──────┘   │
                   │          │          │
          ┌────────▼──┐  ┌────▼────────┐ │
          │api-portal │  │api-pao      │ │
          │.utpxpedi- │  │.utpxpedi-   │ │
          │tion.com   │  │tion.com     │ │
          └───────────┘  └─────────────┘ │
                    └─────────────────────┘
```

## APIs Descubiertas

| Plataforma | Base URL | Tipo | Datos |
|-----------|---------|------|-------|
| Portal UTP | `api-portal.utpxpedition.com/graphql` | GraphQL | Notas, Periodos |
| Class UTP | `api-pao.utpxpedition.com` | REST | Cursos, Tareas, Mensajes, Calendario |
| SSO | `sso.utp.edu.pe/auth/realms/Xpedition` | OIDC | Autenticación |

## Licencia

Este proyecto está bajo la licencia **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**. 
Eres libre de usar, estudiar, modificar y compartir este código para cualquier propósito personal o académico, siempre y cuando **no se use con fines comerciales**, se otorgue el crédito correspondiente al autor original, y cualquier modificación o trabajo derivado se distribuya bajo esta misma licencia.
