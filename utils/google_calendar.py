"""
Utilidades para integración con Google Calendar e iCal (.ics).
Permite generar enlaces directos de 1-clic para agregar turnos a Google Calendar
y exportar calendarios completos en formato estándar RFC 5545 (.ics).
"""
import urllib.parse
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional

def generate_google_calendar_url(
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    details: str = "",
    location: str = "KNS Kinesiología"
) -> str:
    """
    Genera un enlace web directo (1-clic) para agregar un evento a Google Calendar.
    Funciona tanto en la aplicación móvil de Google Calendar como en la versión web.
    """
    fmt = "%Y%m%dT%H%M%S"
    dates_param = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"
    
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_param,
        "details": details,
        "location": location,
        "sf": "true",
        "output": "xml"
    }
    
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"https://calendar.google.com/calendar/render?{query_string}"

def generate_turno_google_url(turno: Dict[str, Any], clinic_name: str = "KNS Kinesiología") -> str:
    """Genera la URL de Google Calendar a partir de un diccionario de turno de KNS."""
    fecha_str = str(turno.get("fecha", ""))
    h_ini_str = str(turno.get("hora_inicio", "08:00"))[:5]
    h_fin_str = str(turno.get("hora_fin", "08:45"))[:5]
    p_nombre = turno.get("paciente_nombre", "Paciente")
    p_os = turno.get("paciente_obra_social", "Particular")
    notas = turno.get("notas", "")
    
    try:
        t_fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if "-" in fecha_str else date.today()
    except Exception:
        t_fecha = date.today()
        
    try:
        hi_parts = [int(p) for p in h_ini_str.split(":")]
        start_dt = datetime.combine(t_fecha, time(hi_parts[0], hi_parts[1]))
    except Exception:
        start_dt = datetime.combine(t_fecha, time(8, 0))
        
    try:
        hf_parts = [int(p) for p in h_fin_str.split(":")]
        end_dt = datetime.combine(t_fecha, time(hf_parts[0], hf_parts[1]))
    except Exception:
        end_dt = start_dt + timedelta(minutes=45)
        
    title = f"🩺 Turno Kinesiología: {p_nombre}"
    details = f"Paciente: {p_nombre}\nObra Social: {p_os}\nNotas: {notas or 'Sin notas adicionales'}\n\nAgendado en sistema KNS."
    
    return generate_google_calendar_url(
        title=title,
        start_dt=start_dt,
        end_dt=end_dt,
        details=details,
        location=clinic_name
    )

def generate_ics_content(turnos: List[Dict[str, Any]], clinic_name: str = "KNS Kinesiología") -> str:
    """
    Genera un archivo de calendario iCalendar (.ics) estándar RFC 5545
    compatible con Google Calendar, Apple Calendar, Outlook y Android.
    """
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KNS Kinesiologia//Sistema de Turnos//ES",
        f"X-WR-CALNAME:Agenda - {clinic_name}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for t in turnos:
        t_id = str(t.get("id", "0"))
        fecha_str = str(t.get("fecha", ""))
        h_ini_str = str(t.get("hora_inicio", "08:00"))[:5]
        h_fin_str = str(t.get("hora_fin", "08:45"))[:5]
        p_nombre = t.get("paciente_nombre", "Paciente")
        p_os = t.get("paciente_obra_social", "Particular")
        estado = t.get("estado", "Pendiente")
        notas = t.get("notas", "")
        
        if estado == "Cancelado":
            continue
            
        try:
            t_fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if "-" in fecha_str else date.today()
            hi_parts = [int(p) for p in h_ini_str.split(":")]
            hf_parts = [int(p) for p in h_fin_str.split(":")]
            start_dt = datetime.combine(t_fecha, time(hi_parts[0], hi_parts[1]))
            end_dt = datetime.combine(t_fecha, time(hf_parts[0], hf_parts[1]))
        except Exception:
            continue
            
        fmt_local = "%Y%m%dT%H%M%S"
        
        summary = f"🩺 Turno: {p_nombre} ({p_os})"
        desc = f"Estado: {estado}\\nObra Social: {p_os}\\nNotas: {notas or 'N/A'}"
        
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:kns-turno-{t_id}-{start_dt.strftime('%Y%m%d%H%M')}@kns",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{start_dt.strftime(fmt_local)}",
            f"DTEND:{end_dt.strftime(fmt_local)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{clinic_name}",
            f"STATUS:{'CONFIRMED' if estado != 'Cancelado' else 'CANCELLED'}",
            "END:VEVENT"
        ])
        
    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)
