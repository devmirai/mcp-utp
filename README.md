# UTP MCP Server 🎓

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
| `get_messages` | Conversaciones con docentes/compañeros |
| `read_conversation` | Leer mensajes de una conversación |
| `send_message` | Enviar mensaje a docente/compañero |

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

### Con Qwen / otros clientes MCP

Configura según la documentación de tu cliente MCP apuntando a:
```
command: python -m utp_mcp.server
transport: stdio
```

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
