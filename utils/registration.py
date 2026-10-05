"""
Módulo para la gestión de enlaces públicos de alta / completado de ficha de pacientes (Self-Service Registration),
notificaciones en la app y carga digital de pedidos médicos.
"""
import os
import json
import uuid
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st

from utils.supabase_client import (
    get_paciente_by_id,
    update_paciente,
    upload_paciente_archivo,
    get_app_config,
    _get_local_store
)
from utils.whatsapp import normalize_phone_number, generate_whatsapp_url

# Archivo de persistencia compartida en disco para tokens y notificaciones
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".data")
TOKENS_FILE = os.path.join(DATA_DIR, "tokens_registro.json")
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notificaciones.json")

def _ensure_data_dir():
    """Asegura que el directorio de datos locales exista."""
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception:
            pass

def _load_json_file(file_path: str, default: Any) -> Any:
    """Carga datos desde un archivo JSON local."""
    _ensure_data_dir()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def _save_json_file(file_path: str, data: Any):
    """Guarda datos en un archivo JSON local."""
    _ensure_data_dir()
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando {file_path}: {e}")

# ==============================================================================
# GESTIÓN DE TOKENS DE REGISTRO
# ==============================================================================

def create_registration_token(
    paciente_id: str,
    turno_id: Optional[str] = None,
    nombre_inicial: Optional[str] = None,
    telefono_inicial: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera y almacena un token único para que el paciente complete su ficha online.
    """
    tokens = _load_json_file(TOKENS_FILE, {})
    
    # Si el paciente ya tiene un token pendiente, reutilizarlo o generar uno nuevo
    token = str(uuid.uuid4())
    
    paciente = get_paciente_by_id(paciente_id) or {}
    nombre = nombre_inicial or paciente.get("nombre_completo", "Paciente")
    telefono = telefono_inicial or paciente.get("telefono", "")
    
    record = {
        "token": token,
        "paciente_id": str(paciente_id),
        "turno_id": str(turno_id) if turno_id else None,
        "nombre_inicial": nombre,
        "telefono_inicial": telefono,
        "completado": False,
        "completado_at": None,
        "created_at": datetime.now().isoformat(),
        "archivos_adjuntos": []
    }
    
    tokens[token] = record
    _save_json_file(TOKENS_FILE, tokens)
    
    # También sincronizar en session_state y local store
    store = _get_local_store()
    store.setdefault("tokens_registro", {})[token] = record
    
    return record

def get_registration_token(token: str) -> Optional[Dict[str, Any]]:
    """Obtiene los datos de un token de registro."""
    if not token:
        return None
    tokens = _load_json_file(TOKENS_FILE, {})
    return tokens.get(token)

def submit_patient_registration(
    token: str,
    form_data: Dict[str, Any],
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Procesa el formulario enviado por el paciente:
    1. Actualiza los datos del paciente en la base de datos (PostgreSQL/Supabase).
    2. Sube la foto o archivo del pedido médico al bucket de almacenamiento.
    3. Marca el token como completado.
    4. Genera una notificación en la aplicación para alertar al profesional.
    """
    reg = get_registration_token(token)
    if not reg:
        return False, "El enlace de registro no es válido o ha expirado."
        
    paciente_id = reg.get("paciente_id")
    if not paciente_id:
        return False, "No se encontró el paciente asociado a este formulario."

    # 1. Preparar campos para actualizar el paciente
    nombre = form_data.get("full_name", "").strip() or reg.get("nombre_inicial", "Paciente")
    dni = form_data.get("document_number", "").strip()
    telefono = form_data.get("mobile_phone", "").strip() or reg.get("telefono_inicial", "")
    obra_social = form_data.get("medical_insurance", "Particular").strip() or "Particular"
    patologia = form_data.get("reason", "").strip()
    
    fecha_nac = form_data.get("birth_date")
    if isinstance(fecha_nac, (date, datetime)):
        fecha_nac_str = fecha_nac.isoformat()
    elif isinstance(fecha_nac, str) and fecha_nac.strip():
        fecha_nac_str = fecha_nac.strip()
    else:
        fecha_nac_str = None

    edad = form_data.get("edad")
    if edad is None and fecha_nac:
        try:
            if isinstance(fecha_nac, str):
                fn = datetime.strptime(fecha_nac, "%Y-%m-%d").date()
            else:
                fn = fecha_nac
            today = date.today()
            edad = today.year - fn.year - ((today.month, today.day) < (fn.month, fn.day))
        except Exception:
            edad = None

    paciente_updates = {
        "nombre_completo": nombre,
        "dni": dni,
        "telefono": telefono,
        "obra_social": obra_social,
        "fecha_nacimiento": fecha_nac_str,
        "edad": int(edad) if edad is not None else None,
        # Metadatos extendidos del formulario
        "tipo_doc": form_data.get("document_type", "DNI"),
        "sexo": form_data.get("gender", "No especifica"),
        "email": form_data.get("email", "").strip(),
        "plan_obra_social": form_data.get("plan", "").strip(),
        "numero_afiliado": form_data.get("affiliate_number", "").strip(),
        "direccion": form_data.get("address", "").strip(),
        "localidad": form_data.get("city", "").strip(),
        "provincia": form_data.get("state", "").strip(),
        "patologia": patologia,
        "ficha_completada": True,
        "ficha_completada_at": datetime.now().isoformat()
    }

    ok_p, msg_p = update_paciente(paciente_id, paciente_updates)
    if not ok_p:
        return False, f"Error al actualizar los datos del paciente: {msg_p}"

    # 2. Subir pedido médico si fue adjuntado / fotografiado
    adjunto_info = None
    if file_bytes and len(file_bytes) > 0:
        fname = filename or f"pedido_medico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        ok_up, msg_up, adjunto_info = upload_paciente_archivo(
            paciente_id=paciente_id,
            file_bytes=file_bytes,
            filename=fname,
            tipo_documento="Pedido Médico"
        )
        if not ok_up:
            print(f"Aviso: no se pudo guardar el archivo adjunto: {msg_up}")

    # 3. Marcar token como completado
    tokens = _load_json_file(TOKENS_FILE, {})
    if token in tokens:
        tokens[token]["completado"] = True
        tokens[token]["completado_at"] = datetime.now().isoformat()
        if adjunto_info:
            tokens[token]["archivos_adjuntos"].append(adjunto_info.get("public_url") or adjunto_info.get("nombre_archivo"))
        _save_json_file(TOKENS_FILE, tokens)

    # 4. Registrar notificación para los kinesiólogos en la app
    notif_id = str(uuid.uuid4())
    notif_record = {
        "id": notif_id,
        "tipo": "ficha_paciente_completada",
        "paciente_id": paciente_id,
        "paciente_nombre": nombre,
        "paciente_telefono": telefono,
        "tiene_pedido_medico": bool(file_bytes and len(file_bytes) > 0),
        "mensaje": f"El paciente {nombre} completó su ficha de alta{' y adjuntó su pedido médico' if file_bytes else ''}.",
        "created_at": datetime.now().isoformat(),
        "leido": False
    }
    
    notificaciones = _load_json_file(NOTIFICATIONS_FILE, [])
    notificaciones.insert(0, notif_record)
    _save_json_file(NOTIFICATIONS_FILE, notificaciones)
    
    return True, "Tus datos han sido registrados con éxito."

# ==============================================================================
# GESTIÓN DE NOTIFICACIONES Y AVISOS
# ==============================================================================

def get_all_notifications() -> List[Dict[str, Any]]:
    """Obtiene la lista de todas las notificaciones registradas."""
    return _load_json_file(NOTIFICATIONS_FILE, [])

def get_unread_notifications() -> List[Dict[str, Any]]:
    """Obtiene las notificaciones pendientes de lectura."""
    notificaciones = _load_json_file(NOTIFICATIONS_FILE, [])
    return [n for n in notificaciones if not n.get("leido", False)]

def mark_notification_as_read(notif_id: str) -> bool:
    """Marca una notificación específica como leída."""
    notificaciones = _load_json_file(NOTIFICATIONS_FILE, [])
    found = False
    for n in notificaciones:
        if n.get("id") == notif_id:
            n["leido"] = True
            found = True
            break
    if found:
        _save_json_file(NOTIFICATIONS_FILE, notificaciones)
    return found

def mark_all_notifications_as_read() -> bool:
    """Marca todas las notificaciones como leídas."""
    notificaciones = _load_json_file(NOTIFICATIONS_FILE, [])
    for n in notificaciones:
        n["leido"] = True
    _save_json_file(NOTIFICATIONS_FILE, notificaciones)
    return True

# ==============================================================================
# GENERADORES DE ENLACES Y MENSAJES WHATSAPP
# ==============================================================================

def get_base_url() -> str:
    """
    Obtiene la URL base donde corre la aplicación.
    Prioridad:
    1. st.secrets["BASE_URL"] o st.secrets["APP_URL"]
    2. Configuración en base de datos (app_config['base_url'])
    3. Detección automática en tiempo de ejecución vía st.context.headers
    4. Fallback a http://localhost:8501
    """
    # 1. st.secrets
    try:
        if hasattr(st, "secrets"):
            if "BASE_URL" in st.secrets and st.secrets["BASE_URL"]:
                return str(st.secrets["BASE_URL"]).rstrip("/")
            if "APP_URL" in st.secrets and st.secrets["APP_URL"]:
                return str(st.secrets["APP_URL"]).rstrip("/")
    except Exception:
        pass

    # 2. Configuración en base de datos
    try:
        cfg = get_app_config()
        if cfg and cfg.get("base_url"):
            return str(cfg["base_url"]).rstrip("/")
    except Exception:
        pass

    # 3. Streamlit Context Headers en tiempo real
    try:
        ctx = getattr(st, "context", None)
        if ctx and hasattr(ctx, "headers"):
            headers = ctx.headers
            origin = headers.get("origin") or headers.get("Origin")
            if origin:
                return str(origin).rstrip("/")
            
            host = headers.get("x-forwarded-host") or headers.get("host") or headers.get("Host")
            if host:
                proto = headers.get("x-forwarded-proto", "https" if ("streamlit.app" in str(host) or "https" in str(host)) else "http")
                return f"{proto}://{host}".rstrip("/")
                
            referer = headers.get("referer") or headers.get("Referer")
            if referer:
                import urllib.parse
                parsed = urllib.parse.urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    except Exception:
        pass

    return "http://localhost:8501"

def generate_registration_link(token: str, base_url: Optional[str] = None) -> str:
    """Genera la URL completa y clicable con la web raíz y el token de registro."""
    root = (base_url or get_base_url()).rstrip("/")
    return f"{root}/?registro={token}"

def generate_registration_whatsapp_url(
    phone: str,
    paciente_nombre: str,
    token: str,
    turno_fecha: Optional[str] = None,
    turno_hora: Optional[str] = None,
    clinic_name: str = "KION",
    base_url: Optional[str] = None
) -> str:
    """
    Crea el enlace wa.me con el texto de invitación para completar el formulario.
    """
    link = generate_registration_link(token, base_url=base_url)
    from utils.whatsapp import template_alta_paciente_link
    mensaje = template_alta_paciente_link(
        nombre_paciente=paciente_nombre,
        registro_link=link,
        consultorio=clinic_name,
        fecha_str=turno_fecha,
        hora_str=turno_hora
    )
    return generate_whatsapp_url(phone, mensaje)

