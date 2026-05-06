"""UTP MCP Server — Main entry point.

Exposes university data as MCP tools for AI assistants.
Transport: stdio (universal, works with any MCP client).
"""

import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .auth import AuthManager
from .clients import ClassClient, PortalClient

load_dotenv()

# ─── Server Init ─────────────────────────────────────────────────────────────
mcp = FastMCP("UTP Academic")

# Lazy-init clients (created on first tool call)
_auth: AuthManager | None = None
_portal: PortalClient | None = None
_class: ClassClient | None = None


def _init():
    global _auth, _portal, _class
    if _auth is not None:
        return

    username = os.getenv("UTP_USERNAME")
    password = os.getenv("UTP_PASSWORD")
    if not username or not password:
        raise RuntimeError("UTP_USERNAME and UTP_PASSWORD environment variables are required")

    _auth = AuthManager(username, password)
    _portal = PortalClient(_auth)
    _class = ClassClient(_auth)


# ─── Tools: Periods ─────────────────────────────────────────────────────────

@mcp.tool()
def get_periods() -> str:
    """Obtener todos los periodos academicos (ciclos) disponibles con ID y nombre.

    Ejemplo: [{"id": "2262", "name": "2026 - Ciclo 1 Marzo"}, ...]
    Use the period ID in other tools like get_course_summary or get_schedule.
    """
    _init()
    periods = _portal.get_periods()
    return json.dumps(periods, ensure_ascii=False, indent=2)


# ─── Tools: Courses + Grades + Schedule (Portal GraphQL) ────────────────────

@mcp.tool()
def get_course_summary(period_id: str = "2262") -> str:
    """Obtener resumen completo del ciclo: cursos, horarios, notas parciales y evaluaciones.

    Incluye para cada curso:
    - Nombre, docente, creditos, horas semanales
    - Modalidad (P=Presencial, VT=Virtual)
    - Horario semanal (dia, hora inicio/fin)
    - Evaluaciones con notas (PC1, PC2, PA, EXFN, etc.)
    - Promedio del curso

    Args:
        period_id: ID del periodo. Ej: '2262' = 2026 Ciclo 1 Marzo. Obtener de get_periods.
    """
    _init()
    data = _portal.get_course_summary(period_id)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def get_grade_record() -> str:
    """Obtener record historico COMPLETO de notas de TODOS los ciclos cursados.

    Incluye para cada ciclo: nombre del curso, nota final, creditos y estado (Aprobado/Desaprobado).
    """
    _init()
    record = _portal.get_grade_record()
    return json.dumps(record, ensure_ascii=False, indent=2)


@mcp.tool()
def get_weekly_schedule(period_id: str = "2262") -> str:
    """Obtener el horario semanal completo con clases por dia y hora.

    Muestra las clases de la semana actual con nombre del curso,
    hora inicio/fin, y modalidad (Presencial/Virtual).

    Args:
        period_id: ID del periodo. Ej: '2262' = 2026 Ciclo 1 Marzo.
    """
    _init()
    now_ms = float(int(time.time() * 1000))
    schedule = _portal.get_schedule_by_date(now_ms, [period_id])

    # Format timestamps to readable hours
    result = []
    for day in schedule.get("dates", []):
        day_items = []
        for item in day.get("items", []):
            start = datetime.fromtimestamp(item["startTime"] / 1000)
            end = datetime.fromtimestamp(item["endTime"] / 1000)
            modality = item.get("modality", {})
            day_items.append({
                "course": item["name"],
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "modality": modality.get("name", ""),
                "modality_code": modality.get("id", ""),
            })
        result.append({
            "date": day["date"],
            "day_name": datetime.strptime(day["date"], "%Y-%m-%d").strftime("%A"),
            "classes": day_items,
        })

    return json.dumps(result, ensure_ascii=False, indent=2)


# ─── Tools: Courses (Class REST) ────────────────────────────────────────────

@mcp.tool()
def get_courses(career: str = None) -> str:
    """Obtener los cursos activos del ciclo actual con informacion del docente.

    Datos del LMS (class.utp.edu.pe) con sectionId para consultar contenido y tareas.
    
    Args:
        career: Opcional. Filtrar por tipo de carrera (ej. 'PREG' para pregrado regular, 'PRED' para cursos extra).
    """
    _init()
    courses = _class.get_dashboard_courses()
    active = [c for c in courses if c.get("active")]
    
    if career:
        active = [c for c in active if c.get("acadCareer") == career]

    result = []
    for c in active:
        result.append({
            "name": c.get("name"),
            "code": c.get("courseCode"),
            "section": c.get("classNumber"),
            "modality": c.get("modality"),
            "teacher": f"{c.get('teacherFirstName', '')} {c.get('teacherLastName', '')}".strip(),
            "teacher_email": c.get("teacherEmail"),
            "period": c.get("period"),
            "progress": c.get("progress"),
            "sectionId": c.get("sectionId"),
            "courseId": c.get("courseId"),
            "career": c.get("acadCareer"),
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def get_course_content(course_id: str, section_id: str) -> str:
    """Obtener el contenido completo de un curso (unidades, temas, actividades).

    Args:
        course_id: ID del curso (obtenerlo de get_courses).
        section_id: ID de la seccion del curso (obtenerlo de get_courses).
    """
    _init()
    content = _class.get_course_content(course_id, section_id)
    return json.dumps(content.get("unities", []), ensure_ascii=False, indent=2)


@mcp.tool()
def get_course_materials(course_id: str, section_id: str) -> str:
    """Obtener los materiales (PDFs, PPTs, links) y el silabo de un curso.

    Extrae solo los archivos y enlaces del contenido del curso para facil acceso.

    Args:
        course_id: ID del curso.
        section_id: ID de la seccion del curso.
    """
    _init()
    content = _class.get_course_content(course_id, section_id)
    
    materials = []
    # Content has unities -> themes -> contents
    for unit in content.get("unities", []):
        for theme in unit.get("themes", []):
            for item in theme.get("contents", []):
                if item.get("type") in ["FILE", "LINK", "PAGE", "SCORM", "SYLLABUS", "URL"]:
                    url = None
                    meta = item.get("metadata", {})
                    if meta:
                        url = meta.get("url") or meta.get("fileUrl")
                    
                    materials.append({
                        "title": item.get("title"),
                        "type": item.get("type"),
                        "unit": unit.get("name"),
                        "topic": theme.get("name"),
                        "url": url
                    })
    return json.dumps(materials, ensure_ascii=False, indent=2)


# ─── Tools: Assignments ─────────────────────────────────────────────────────

@mcp.tool()
def get_pending_assignments() -> str:
    """Obtener todas las tareas, evaluaciones y actividades PENDIENTES.

    Incluye titulo, tipo (HOMEWORK/EXAM), fecha limite, puntaje maximo,
    si fue calificada, y la semana del ciclo.
    """
    _init()
    activities = _class.get_pending_activities()

    result = []
    for a in activities:
        result.append({
            "title": a.get("activityTitle"),
            "type": a.get("type"),
            "due_date": a.get("finishAt"),
            "published_at": a.get("publishAt"),
            "max_score": a.get("evaluationTopScore"),
            "is_graded": a.get("isQualificated"),
            "week": a.get("weekNumber"),
            "courseId": a.get("courseId"),
            "sectionId": a.get("sectionId"),
            "activityId": a.get("activityId"),
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def get_activity_detail(section_id: str, activity_id: str) -> str:
    """Obtener detalles de una actividad/tarea, incluyendo calificacion si existe.

    Args:
        section_id: ID de la seccion del curso.
        activity_id: ID de la actividad/tarea.
    """
    _init()
    detail = _class.get_activity_detail(section_id, activity_id)
    return json.dumps(detail, ensure_ascii=False, indent=2)


# ─── Tools: Messages ────────────────────────────────────────────────────────

@mcp.tool()
def get_messages(filter_type: str = "all", page: int = 1) -> str:
    """Obtener conversaciones de mensajes con docentes y companeros.

    Args:
        filter_type: 'all', 'unread', o 'read'. Default: 'all'.
        page: Numero de pagina. Default: 1.
    """
    _init()
    messages = _class.get_messages(page, filter_type)

    result = []
    for m in messages:
        to_info = m.get("to", {})
        result.append({
            "id": m.get("id"),
            "contact_name": f"{to_info.get('firstName', '')} {to_info.get('lastName', '')}".strip(),
            "last_message": m.get("lastMessage"),
            "last_received_at": m.get("lastReceivedAt"),
            "unread_count": m.get("countUnread"),
            "contact_id": to_info.get("userId"),
            "courses_in_common": [
                c.get("courseName") for c in to_info.get("commonCoursesList", [])
            ],
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def read_conversation(conversation_id: str, page: int = 1) -> str:
    """Leer los mensajes de una conversacion especifica.

    Args:
        conversation_id: ID de la conversacion (obtenerlo de get_messages).
        page: Numero de pagina. Default: 1.
    """
    _init()
    messages = _class.get_conversation(conversation_id, page)
    return json.dumps(messages, ensure_ascii=False, indent=2)


@mcp.tool()
def send_message(to_user_id: str, message: str, section_id: str) -> str:
    """Enviar un mensaje a un docente o companero.

    Args:
        to_user_id: ID del destinatario (obtenerlo de get_messages).
        message: Texto del mensaje a enviar.
        section_id: ID de la seccion del curso en comun.
    """
    _init()
    result = _class.send_message(to_user_id, message, section_id)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─── Tools: Payments & Procedures ────────────────────────────────────────────

@mcp.tool()
def get_pending_payments() -> str:
    """Consultar los pagos pendientes y deudas actuales. (Solo lectura)"""
    _init()
    payments = _portal.get_pending_payments()
    return json.dumps(payments, ensure_ascii=False, indent=2)


@mcp.tool()
def get_payment_history(period_id: str = "2262") -> str:
    """Consultar el historial de pagos realizados en un periodo especifico.
    
    Args:
        period_id: ID del periodo (ej. '2262').
    """
    _init()
    history = _portal.get_payment_history(period_id)
    return json.dumps(history, ensure_ascii=False, indent=2)


@mcp.tool()
def get_procedures_status() -> str:
    """Consultar el estado de los tramites academicos solicitados (ej. constancias, seguro)."""
    _init()
    procedures = _portal.get_procedures()
    return json.dumps(procedures, ensure_ascii=False, indent=2)


@mcp.tool()
def get_contacts() -> str:
    """Obtener tu lista de contactos (compañeros y docentes de tus cursos actuales)."""
    _init()
    messages = _class.get_messages(page=1, filter_type="all")
    contacts = {}
    for m in messages:
        to_info = m.get("to", {})
        c_id = to_info.get("userId")
        if c_id and c_id not in contacts:
            contacts[c_id] = {
                "name": f"{to_info.get('firstName', '')} {to_info.get('lastName', '')}".strip(),
                "role": to_info.get("role"),
                "courses": [c.get("courseName") for c in to_info.get("commonCoursesList", [])]
            }
    return json.dumps(list(contacts.values()), ensure_ascii=False, indent=2)


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
