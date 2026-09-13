"""
Módulo de integración con WhatsApp y generación de enlaces directos wa.me.
Incluye formateo inteligente de números telefónicos (Argentina e Internacional)
y plantillas contextuales para consultorios kinesiológicos.
"""
import urllib.parse
import re
from typing import Optional

def normalize_phone_number(raw_phone: Optional[str], default_country_code: str = "549") -> str:
    """
    Limpia y estandariza un número telefónico para la API de WhatsApp (wa.me).
    Soporta números argentinos y formatos internacionales:
    - Remueve caracteres no numéricos (+, -, (, ), espacios).
    - Maneja prefijos de Argentina (elimina el 0 inicial del código de área y el 15 de celulares).
    - Agrega el código de país (549 por defecto para Argentina) si no está presente.
    """
    if not raw_phone:
        return ""
    
    # Conservar solo dígitos
    digits = re.sub(r"\D", "", str(raw_phone))
    
    if not digits:
        return ""
    
    # Si empieza con 0 (ej: 011 15 1234-5678 o 0221 15 ... o 011 4444-5555)
    if digits.startswith("0"):
        digits = digits[1:]

    # Si empieza con 549 y tiene longitud adecuada (12-13 dígitos)
    if digits.startswith("549") and len(digits) >= 12:
        return digits
    
    # Si empieza con 54 (sin el 9 de celular móvil argentino)
    if digits.startswith("54") and len(digits) == 12:
        return f"549{digits[2:]}"
    
    # Manejar el prefijo '15' de celulares argentinos
    # En Argentina el formato con 0 y 15 es: 0 + COD_AREA + 15 + NUMERO (ej: 011 15 6789 0123 -> tras quitar 0: 111567890123)
    if digits.startswith("1115") and len(digits) == 12:
        digits = "11" + digits[4:]
    elif len(digits) == 12 and "15" in digits[2:5]:
        # Códigos de área de 3 o 4 dígitos (ej: 221 15 xxx xxxx o 223 15 xxx xxxx)
        idx_15 = digits.find("15")
        if 1 <= idx_15 <= 4:
            digits = digits[:idx_15] + digits[idx_15+2:]
        
    # Si no tiene código de país y tiene 10 dígitos (código de área + número local)
    if not digits.startswith("54") and len(digits) == 10:
        return f"{default_country_code}{digits}"
    
    return digits

def generate_whatsapp_url(phone: str, message: str) -> str:
    """Genera la URL final lista para abrir en WhatsApp Web o App móvil."""
    clean_phone = normalize_phone_number(phone)
    encoded_message = urllib.parse.quote(message)
    if not clean_phone:
        return f"https://wa.me/?text={encoded_message}"
    return f"https://wa.me/{clean_phone}?text={encoded_message}"

# ==============================================================================
# PLANTILLAS DE MENSAJES KINESIOLÓGICOS
# ==============================================================================

def template_recordatorio_turno(
    nombre_paciente: str,
    fecha_str: str,
    hora_str: str,
    consultorio: str = "KNS Consultorio"
) -> str:
    """Mensaje para recordar turno del día o de la semana."""
    return (
        f"👋 Hola {nombre_paciente}, ¿cómo estás? Te escribimos de *{consultorio}*.\n\n"
        f"📅 Te recordamos tu próximo turno de kinesiología para el día *{fecha_str}* a las *{hora_str} hs*.\n\n"
        f"📍 Te pedimos por favor puntualidad y asistir con ropa cómoda.\n"
        f"¡Muchas gracias! Si necesitás reprogramar, avisanos por este medio."
    )

def template_confirmacion_turno(
    nombre_paciente: str,
    fecha_str: str,
    hora_str: str,
    duracion_minutos: int = 45,
    consultorio: str = "KNS Consultorio"
) -> str:
    """Mensaje tras agendar un nuevo turno."""
    return (
        f"✅ Hola {nombre_paciente}! Tu turno en *{consultorio}* ha sido agendado con éxito:\n\n"
        f"🗓 *Fecha:* {fecha_str}\n"
        f"⏰ *Horario:* {hora_str} hs ({duracion_minutos} min)\n\n"
        f"Por favor recordá traer tu orden médica y estudios complementarios si es tu primera sesión.\n"
        f"¡Te esperamos!"
    )

def template_reprogramacion_turno(
    nombre_paciente: str,
    nueva_fecha_str: str,
    nueva_hora_str: str,
    motivo: Optional[str] = None,
    consultorio: str = "KNS Consultorio"
) -> str:
    """Mensaje por cambio de horario o reprogramación."""
    motivo_txt = f"\n*Motivo:* {motivo}\n" if motivo else "\n"
    return (
        f"⚠️ Hola {nombre_paciente}, te informamos una reprogramación de tu turno en *{consultorio}*:{motivo_txt}"
        f"🗓 *Nueva Fecha:* {nueva_fecha_str}\n"
        f"⏰ *Nuevo Horario:* {nueva_hora_str} hs\n\n"
        f"Por favor confirmanos si te queda cómodo este horario. ¡Muchas gracias!"
    )

def template_aviso_sesiones_completadas(
    nombre_paciente: str,
    sesiones_realizadas: int,
    sesiones_totales: int,
    obra_social: Optional[str] = None,
    consultorio: str = "KNS Consultorio"
) -> str:
    """Aviso al paciente cuando está por agotar o agotó su orden de sesiones."""
    os_text = f" ({obra_social})" if obra_social else ""
    return (
        f"📋 Estimado/a {nombre_paciente}, te escribimos de *{consultorio}*.\n\n"
        f"Queremos informarte que has completado *{sesiones_realizadas} de {sesiones_totales} sesiones* autorizadas por tu cobertura médica{os_text}.\n\n"
        f"🩺 Para poder continuar con tu tratamiento y rehabilitación, te solicitamos gestionar una *nueva orden médica* con tu traumatólogo/médico tratante.\n\n"
        f"Cualquier consulta quedamos a tu entera disposición. ¡Saludos!"
    )
