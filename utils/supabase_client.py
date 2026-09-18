"""
Módulo de base de datos y persistencia (PostgreSQL y Almacenamiento de Archivos).
Implementa validaciones de negocio, cálculo de superposiciones de turnos y sincronización de sesiones.
"""
import os
import io
import uuid
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st

# Intentar importar la librería oficial de Supabase
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = Any

# ==============================================================================
# INICIALIZACIÓN DEL CLIENTE
# ==============================================================================

def get_supabase_credentials() -> Tuple[str, str, str]:
    """Obtiene URL, Key y Bucket desde st.secrets o variables de entorno."""
    url = ""
    key = ""
    bucket = "pacientes-adjuntos"
    
    if hasattr(st, "secrets") and "supabase" in st.secrets:
        url = st.secrets["supabase"].get("url", "")
        key = st.secrets["supabase"].get("key", "")
        bucket = st.secrets["supabase"].get("bucket_name", "pacientes-adjuntos")
    
    if not url:
        url = os.getenv("SUPABASE_URL", "https://kgdbgjuezooecsobfwfy.supabase.co")
    if not key:
        key = os.getenv("SUPABASE_KEY", "sb_publishable_zkq6DM_FialXcxIi78Jtkw_hnU_pneX")
    if not bucket:
        bucket = os.getenv("SUPABASE_BUCKET", "pacientes-adjuntos")
        
    return url, key, bucket

_SUPABASE_CLIENT_INSTANCE = None

def init_supabase_client() -> Optional[Any]:
    """Crea e inicializa la instancia singleton del cliente de base de datos."""
    global _SUPABASE_CLIENT_INSTANCE
    if _SUPABASE_CLIENT_INSTANCE is not None:
        return _SUPABASE_CLIENT_INSTANCE
    if not HAS_SUPABASE:
        return None
    url, key, _ = get_supabase_credentials()
    if not url or not key:
        return None
    try:
        _SUPABASE_CLIENT_INSTANCE = create_client(url, key)
        return _SUPABASE_CLIENT_INSTANCE
    except Exception as e:
        print(f"Error inicializando cliente: {e}")
        return None

# ==============================================================================
# CONFIGURACIÓN GENERAL DEL SISTEMA Y LOGO
# ==============================================================================

DEFAULT_APP_CONFIG = {
    "clinic_name": "KNS",
    "subtitle": "KINESIOLOGÍA",
    "logo_icon": "🩺",
    "custom_logo_url": None,
    "custom_logo_bytes": None,
    "phone": "+5491112345678",
    "address": "Consultorio Central",
    "work_start_hour": 8,
    "work_end_hour": 15,
    "max_simultaneous_patients": 2
}

def get_app_config() -> Dict[str, Any]:
    """Obtiene los parámetros de configuración de la app (nombre, subtítulo, logo)."""
    if "app_config" not in st.session_state:
        st.session_state.app_config = dict(DEFAULT_APP_CONFIG)
        # Intentar cargar desde base de datos
        client = init_supabase_client()
        if client:
            try:
                res = client.table("configuracion").select("*").limit(1).execute()
                if res.data and len(res.data) > 0:
                    st.session_state.app_config.update(res.data[0])
            except Exception:
                pass
    return st.session_state.app_config

def update_app_config(new_config: Dict[str, Any]) -> Tuple[bool, str]:
    """Guarda la configuración personalizada de la app (logo, nombre, etc.)."""
    if "app_config" not in st.session_state:
        st.session_state.app_config = dict(DEFAULT_APP_CONFIG)
    st.session_state.app_config.update(new_config)

    client = init_supabase_client()
    if client:
        try:
            # Guardar en base de datos si existe la tabla
            client.table("configuracion").upsert(new_config).execute()
        except Exception:
            pass
    return True, "Configuración actualizada correctamente."

# ==============================================================================
# ALMACENAMIENTO EN MEMORIA / FALLBACK LOCAL
# ==============================================================================

_GLOBAL_FALLBACK_DB: Optional[Dict[str, List[Dict[str, Any]]]] = None

def _get_local_store() -> Dict[str, List[Dict[str, Any]]]:
    """Inicializa y devuelve almacenamiento local en sesión o fallback global."""
    global _GLOBAL_FALLBACK_DB
    today_str = date.today().isoformat()
    
    default_data = {
        "pacientes": [
            {
                "id": "a1111111-1111-1111-1111-111111111111",
                "nombre_completo": "Carlos Menéndez",
                "dni": "28456123",
                "fecha_nacimiento": "1980-05-14",
                "edad": 46,
                "telefono": "+5491144445555",
                "obra_social": "OSDE 210",
                "numero_afiliado": "0210-482910-01",
                "monto_coseguro_default": 3500.0,
                "patologia": "Lumbalgia mecánica con irradiación a miembro inferior derecho",
                "sesiones_totales": 10,
                "sesiones_realizadas": 3,
                "activo": True,
                "notas_generales": "Derivado por Dr. Rossi. Trae RMN lumbar.",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "a2222222-2222-2222-2222-222222222222",
                "nombre_completo": "Florencia Varela",
                "dni": "34123890",
                "fecha_nacimiento": "1994-08-22",
                "edad": 32,
                "telefono": "+5491155556666",
                "obra_social": "Swiss Medical",
                "numero_afiliado": "SM-9831204",
                "monto_coseguro_default": 4000.0,
                "patologia": "Tendinopatía del manguito rotador derecho",
                "sesiones_totales": 10,
                "sesiones_realizadas": 5,
                "activo": True,
                "notas_generales": "Dolor en abducción > 90°. Deportista de crossfit.",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "a3333333-3333-3333-3333-333333333333",
                "nombre_completo": "Esteban Lamponne",
                "dni": "25890432",
                "fecha_nacimiento": "1976-11-03",
                "edad": 50,
                "telefono": "+5491166667777",
                "obra_social": "Particular",
                "numero_afiliado": "",
                "monto_coseguro_default": 12000.0,
                "patologia": "Esguince de tobillo grado II (LPAA)",
                "sesiones_totales": 8,
                "sesiones_realizadas": 1,
                "activo": True,
                "notas_generales": "Fase subaguda con edema residual.",
                "created_at": datetime.now().isoformat()
            }
        ],
        "turnos": [
            {
                "id": "b1111111-1111-1111-1111-111111111111",
                "paciente_id": "a1111111-1111-1111-1111-111111111111",
                "fecha": today_str,
                "hora_inicio": "08:30:00",
                "hora_fin": "09:15:00",
                "duracion_minutos": 45,
                "estado": "Pendiente",
                "monto_coseguro": 3500.0,
                "estado_pago": "Pendiente",
                "motivo_ajuste": None,
                "notas": "Magneto + ejercicios lumbo-pélvicos",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "b2222222-2222-2222-2222-222222222222",
                "paciente_id": "a2222222-2222-2222-2222-222222222222",
                "fecha": today_str,
                "hora_inicio": "09:00:00",
                "hora_fin": "09:45:00",
                "duracion_minutos": 45,
                "estado": "Pendiente",
                "monto_coseguro": 4000.0,
                "estado_pago": "Abonado",
                "motivo_ajuste": None,
                "notas": "Ultrasonido + movilidad escapulotorácica",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "b3333333-3333-3333-3333-333333333333",
                "paciente_id": "a3333333-3333-3333-3333-333333333333",
                "fecha": today_str,
                "hora_inicio": "10:00:00",
                "hora_fin": "10:30:00",
                "duracion_minutos": 30,
                "estado": "Pendiente",
                "monto_coseguro": 12000.0,
                "estado_pago": "Pendiente",
                "motivo_ajuste": None,
                "notas": "Crioterapia + propiocepción en bosu",
                "created_at": datetime.now().isoformat()
            }
        ],
        "pagos": [
            {
                "id": "d1111111-1111-1111-1111-111111111111",
                "paciente_id": "a1111111-1111-1111-1111-111111111111",
                "turno_id": None,
                "fecha_pago": today_str,
                "monto": 3500.0,
                "monto_total_esperado": None,
                "concepto": "Coseguro Sesión 1",
                "modalidad": "Por sesión",
                "metodo_pago": "Efectivo",
                "sesiones_cubiertas": 1,
                "notas": "Coseguro primera sesión",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "d2222222-2222-2222-2222-222222222222",
                "paciente_id": "a2222222-2222-2222-2222-222222222222",
                "turno_id": None,
                "fecha_pago": today_str,
                "monto": 40000.0,
                "monto_total_esperado": 40000.0,
                "concepto": "Tratamiento Completo 10 Sesiones",
                "modalidad": "Tratamiento completo",
                "metodo_pago": "Transferencia / MP",
                "sesiones_cubiertas": 10,
                "notas": "Abonó paquete completo de 10 coseguros juntos",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "d3333333-3333-3333-3333-333333333333",
                "paciente_id": "a3333333-3333-3333-3333-333333333333",
                "turno_id": None,
                "fecha_pago": today_str,
                "monto": 30000.0,
                "monto_total_esperado": 96000.0,
                "concepto": "Seña / Pago Parcial Tratamiento Particular",
                "modalidad": "Pago parcial / Seña",
                "metodo_pago": "Transferencia / MP",
                "sesiones_cubiertas": 3,
                "notas": "Dejó seña inicial de $30.000 de un total de $96.000 por 8 sesiones particulares",
                "created_at": datetime.now().isoformat()
            }
        ],
        "evoluciones": [
            {
                "id": "c1111111-1111-1111-1111-111111111111",
                "paciente_id": "a1111111-1111-1111-1111-111111111111",
                "turno_id": "b1111111-1111-1111-1111-111111111111",
                "fecha": today_str,
                "nota_clinica": "Paciente refiere notable alivio de irradiación tras sesión anterior. Dolor focal 4/10.",
                "tratamiento_aplicado": "TENS 20m + elongación cadena posterior",
                "escala_dolor_eva": 4,
                "created_at": datetime.now().isoformat()
            }
        ],
        "archivos_pacientes": []
    }

    try:
        if hasattr(st, "session_state"):
            if "local_db" not in st.session_state:
                st.session_state.local_db = default_data
            else:
                # Asegurar que existan claves nuevas en session_state previo
                st.session_state.local_db.setdefault("pagos", default_data["pagos"])
            return st.session_state.local_db
    except Exception:
        pass

    if _GLOBAL_FALLBACK_DB is None:
        _GLOBAL_FALLBACK_DB = default_data
    return _GLOBAL_FALLBACK_DB

# ==============================================================================
# OPERACIONES CRUD: PACIENTES
# ==============================================================================

def get_pacientes(activo_only: bool = False, query: str = "") -> List[Dict[str, Any]]:
    """Obtiene la lista de pacientes combinando base de datos y fallback local."""
    pacientes_map: Dict[str, Dict[str, Any]] = {}
    
    # 1. Cargar desde base de datos remota si está disponible
    client = init_supabase_client()
    if client:
        try:
            req = client.table("pacientes").select("*").order("nombre_completo")
            if activo_only:
                req = req.eq("activo", True)
            res = req.execute()
            if res.data:
                for p in res.data:
                    pacientes_map[str(p["id"])] = dict(p)
        except Exception:
            pass

    # 2. Combinar/complementar con almacenamiento local
    store = _get_local_store()
    for p in store.get("pacientes", []):
        p_id = str(p.get("id"))
        if p_id in pacientes_map:
            for k, v in p.items():
                if k not in pacientes_map[p_id] or pacientes_map[p_id][k] is None:
                    pacientes_map[p_id][k] = v
        else:
            if not activo_only or p.get("activo", True):
                pacientes_map[p_id] = dict(p)

    pacientes = list(pacientes_map.values())
    if activo_only:
        pacientes = [p for p in pacientes if p.get("activo", True)]
    if query:
        q = query.lower()
        pacientes = [
            p for p in pacientes
            if q in str(p.get("nombre_completo", "")).lower()
            or q in str(p.get("dni", "")).lower()
            or q in str(p.get("obra_social", "")).lower()
            or q in str(p.get("numero_afiliado", "")).lower()
        ]
    return sorted(pacientes, key=lambda x: x.get("nombre_completo", ""))

def get_paciente_by_id(paciente_id: str) -> Optional[Dict[str, Any]]:
    """Busca un paciente específico por su ID en Supabase y almacenamiento local."""
    if not paciente_id:
        return None
        
    store = _get_local_store()
    local_p = None
    for p in store.get("pacientes", []):
        if str(p.get("id")) == str(paciente_id):
            local_p = dict(p)
            break

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").select("*").eq("id", str(paciente_id)).limit(1).execute()
            if res.data and len(res.data) > 0:
                remote_p = dict(res.data[0])
                if local_p:
                    for k, v in local_p.items():
                        if k not in remote_p or remote_p[k] is None:
                            remote_p[k] = v
                return remote_p
        except Exception:
            pass

    return local_p

def create_paciente(paciente_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Crea un nuevo paciente en el sistema."""
    if not paciente_data.get("nombre_completo"):
        return False, "El nombre y apellido son obligatorios.", None

    store = _get_local_store()
    new_p = dict(paciente_data)
    if "id" not in new_p or not new_p["id"]:
        new_p["id"] = str(uuid.uuid4())
    new_p.setdefault("created_at", datetime.now().isoformat())
    new_p.setdefault("sesiones_realizadas", 0)
    new_p.setdefault("activo", True)

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").insert(new_p).execute()
            if res.data:
                created_row = dict(res.data[0])
                for k, v in new_p.items():
                    created_row.setdefault(k, v)
                store.setdefault("pacientes", []).append(created_row)
                return True, "Paciente registrado exitosamente.", created_row
        except Exception:
            # Si falló por alguna columna que falta en Supabase remoto, intentar insertar datos base
            try:
                base_payload = {
                    "id": new_p["id"],
                    "nombre_completo": new_p.get("nombre_completo"),
                    "dni": new_p.get("dni"),
                    "edad": new_p.get("edad"),
                    "telefono": new_p.get("telefono"),
                    "obra_social": new_p.get("obra_social"),
                    "patologia": new_p.get("patologia"),
                    "sesiones_totales": new_p.get("sesiones_totales", 10),
                    "sesiones_realizadas": new_p.get("sesiones_realizadas", 0),
                    "activo": new_p.get("activo", True),
                    "notas_generales": new_p.get("notas_generales")
                }
                res = client.table("pacientes").insert(base_payload).execute()
                if res.data:
                    created_row = dict(res.data[0])
                    for k, v in new_p.items():
                        created_row.setdefault(k, v)
                    store.setdefault("pacientes", []).append(created_row)
                    return True, "Paciente registrado exitosamente.", created_row
            except Exception:
                pass

    # Guardar en local store
    store.setdefault("pacientes", []).append(new_p)
    return True, "Paciente registrado exitosamente.", new_p

def update_paciente(paciente_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza los datos de un paciente."""
    client = init_supabase_client()
    if client:
        try:
            updates["updated_at"] = datetime.now().isoformat()
            res = client.table("pacientes").update(updates).eq("id", str(paciente_id)).execute()
            if res.data:
                return True, "Paciente actualizado exitosamente."
        except Exception:
            try:
                base_keys = {'nombre_completo', 'dni', 'edad', 'telefono', 'obra_social', 'patologia', 'sesiones_totales', 'sesiones_realizadas', 'activo', 'notas_generales', 'updated_at'}
                base_updates = {k: v for k, v in updates.items() if k in base_keys}
                res = client.table("pacientes").update(base_updates).eq("id", str(paciente_id)).execute()
                if res.data:
                    return True, "Paciente actualizado exitosamente."
            except Exception:
                pass

    store = _get_local_store()
    for p in store["pacientes"]:
        if str(p.get("id")) == str(paciente_id):
            p.update(updates)
            return True, "Paciente actualizado exitosamente."
    return False, "Paciente no encontrado."

def delete_paciente(paciente_id: str) -> Tuple[bool, str]:
    """Elimina un paciente y sus turnos/evoluciones asociadas."""
    client = init_supabase_client()
    if client:
        try:
            client.table("pacientes").delete().eq("id", str(paciente_id)).execute()
        except Exception as e:
            print(f"Error eliminando paciente: {e}")

    store = _get_local_store()
    store["pacientes"] = [p for p in store.get("pacientes", []) if str(p.get("id")) != str(paciente_id)]
    store["turnos"] = [t for t in store.get("turnos", []) if str(t.get("paciente_id")) != str(paciente_id)]
    store["evoluciones"] = [e for e in store.get("evoluciones", []) if str(e.get("paciente_id")) != str(paciente_id)]
    store["pagos"] = [p for p in store.get("pagos", []) if str(p.get("paciente_id")) != str(paciente_id)]
    return True, "Paciente eliminado correctamente."

# ==============================================================================
# OPERACIONES CRUD: TURNOS Y AGENDA
# ==============================================================================

def get_turnos(
    target_date: Optional[date] = None,
    paciente_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Obtiene los turnos filtrados combinando base de datos y fallback local."""
    turnos_map: Dict[str, Dict[str, Any]] = {}
    
    client = init_supabase_client()
    if client:
        try:
            # Seleccionar todas las columnas del turno y del paciente asociado dinámicamente
            req = client.table("turnos").select("*, pacientes(*)").order("fecha").order("hora_inicio")
            if target_date:
                req = req.eq("fecha", target_date.isoformat())
            if start_date:
                req = req.gte("fecha", start_date.isoformat())
            if end_date:
                req = req.lte("fecha", end_date.isoformat())
            if paciente_id:
                req = req.eq("paciente_id", str(paciente_id))
            res = req.execute()
            if res.data is not None:
                for t in res.data:
                    p_info = t.get("pacientes") or {}
                    t["paciente_nombre"] = p_info.get("nombre_completo", "Paciente Desconocido")
                    t["paciente_telefono"] = p_info.get("telefono", "")
                    t["paciente_obra_social"] = p_info.get("obra_social", "Particular")
                    t["paciente_numero_afiliado"] = p_info.get("numero_afiliado", "")
                    t["paciente_fecha_nacimiento"] = p_info.get("fecha_nacimiento", None)
                    t["paciente_monto_coseguro_default"] = float(p_info.get("monto_coseguro_default", 0) or 0)
                    t["paciente_sesiones_totales"] = p_info.get("sesiones_totales", 10)
                    t["paciente_sesiones_realizadas"] = p_info.get("sesiones_realizadas", 0)
                    t.setdefault("monto_coseguro", float(p_info.get("monto_coseguro_default", 0) or 0))
                    t.setdefault("estado_pago", "Pendiente")
                    turnos_map[str(t["id"])] = t
        except Exception as e:
            # Fallback seguro: cargar turnos directos y cruzar con pacientes
            try:
                req2 = client.table("turnos").select("*").order("fecha").order("hora_inicio")
                if target_date:
                    req2 = req2.eq("fecha", target_date.isoformat())
                if start_date:
                    req2 = req2.gte("fecha", start_date.isoformat())
                if end_date:
                    req2 = req2.lte("fecha", end_date.isoformat())
                if paciente_id:
                    req2 = req2.eq("paciente_id", str(paciente_id))
                res2 = req2.execute()
                if res2.data:
                    pacientes_lookup = {str(p["id"]): p for p in get_pacientes()}
                    for t in res2.data:
                        p_info = pacientes_lookup.get(str(t.get("paciente_id")), {})
                        t["pacientes"] = p_info
                        t["paciente_nombre"] = p_info.get("nombre_completo", "Paciente Desconocido")
                        t["paciente_telefono"] = p_info.get("telefono", "")
                        t["paciente_obra_social"] = p_info.get("obra_social", "Particular")
                        t["paciente_numero_afiliado"] = p_info.get("numero_afiliado", "")
                        t["paciente_fecha_nacimiento"] = p_info.get("fecha_nacimiento", None)
                        t["paciente_monto_coseguro_default"] = float(p_info.get("monto_coseguro_default", 0) or 0)
                        t["paciente_sesiones_totales"] = p_info.get("sesiones_totales", 10)
                        t["paciente_sesiones_realizadas"] = p_info.get("sesiones_realizadas", 0)
                        t.setdefault("monto_coseguro", float(p_info.get("monto_coseguro_default", 0) or 0))
                        t.setdefault("estado_pago", "Pendiente")
                        turnos_map[str(t["id"])] = t
            except Exception:
                pass

    store = _get_local_store()
    pacientes_store_map = {str(p["id"]): p for p in store.get("pacientes", [])}
    for t in store.get("turnos", []):
        t_id = str(t.get("id"))
        if t_id not in turnos_map:
            p = pacientes_store_map.get(str(t.get("paciente_id")), {})
            t_copy = dict(t)
            t_copy["paciente_nombre"] = p.get("nombre_completo", "Paciente")
            t_copy["paciente_telefono"] = p.get("telefono", "")
            t_copy["paciente_obra_social"] = p.get("obra_social", "Particular")
            t_copy["paciente_numero_afiliado"] = p.get("numero_afiliado", "")
            t_copy["paciente_fecha_nacimiento"] = p.get("fecha_nacimiento", None)
            t_copy["paciente_monto_coseguro_default"] = float(p.get("monto_coseguro_default", 0) or 0)
            t_copy["paciente_sesiones_totales"] = p.get("sesiones_totales", 10)
            t_copy["paciente_sesiones_realizadas"] = p.get("sesiones_realizadas", 0)
            t_copy.setdefault("monto_coseguro", float(p.get("monto_coseguro_default", 0) or 0))
            t_copy.setdefault("estado_pago", "Pendiente")
            turnos_map[t_id] = t_copy

    turnos = list(turnos_map.values())
    if target_date:
        t_date_str = target_date.isoformat()
        turnos = [t for t in turnos if t.get("fecha") == t_date_str]
    if start_date:
        s_date_str = start_date.isoformat()
        turnos = [t for t in turnos if str(t.get("fecha", "")) >= s_date_str]
    if end_date:
        e_date_str = end_date.isoformat()
        turnos = [t for t in turnos if str(t.get("fecha", "")) <= e_date_str]
    if paciente_id:
        turnos = [t for t in turnos if str(t.get("paciente_id")) == str(paciente_id)]

    return sorted(turnos, key=lambda x: (str(x.get("fecha", "")), str(x.get("hora_inicio", ""))))

def _time_to_minutes(t_val: Any) -> int:
    """Convierte un objeto time o string 'HH:MM:SS' a minutos desde la medianoche."""
    if isinstance(t_val, str):
        parts = t_val.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    elif isinstance(t_val, time):
        return t_val.hour * 60 + t_val.minute
    return 0

def check_turnos_overlap(
    target_date: date,
    hora_inicio: time,
    hora_fin: time,
    exclude_turno_id: Optional[str] = None,
    max_simultaneous: int = 2
) -> Tuple[bool, int, str]:
    """
    Valida que no haya más de `max_simultaneous` (2) pacientes en simultáneo
    en cualquier intervalo horario del nuevo turno solicitado.
    """
    turnos_dia = get_turnos(target_date=target_date)
    turnos_activos = [
        t for t in turnos_dia
        if t.get("estado") != "Cancelado" and (exclude_turno_id is None or str(t.get("id")) != str(exclude_turno_id))
    ]

    req_start = _time_to_minutes(hora_inicio)
    req_end = _time_to_minutes(hora_fin)

    if req_start >= req_end:
        return False, 0, "La hora de inicio debe ser anterior a la hora de finalización."

    max_coincidentes = 0
    for m in range(req_start, req_end, 5):
        coincidencias_en_minuto = 0
        for t in turnos_activos:
            t_start = _time_to_minutes(t.get("hora_inicio"))
            t_end = _time_to_minutes(t.get("hora_fin"))
            if t_start <= m < t_end:
                coincidencias_en_minuto += 1
        
        if coincidencias_en_minuto > max_coincidentes:
            max_coincidentes = coincidencias_en_minuto
        
        if coincidencias_en_minuto >= max_simultaneous:
            return False, coincidencias_en_minuto, (
                f"Cupo superado: Ya existen {coincidencias_en_minuto} pacientes en simultáneo "
                f"en el rango {hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')} hs "
                f"(Capacidad máxima: {max_simultaneous})."
            )

    return True, max_coincidentes, "Horario disponible."

def create_turno(turno_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Crea un nuevo turno validando superposición de horarios."""
    p_id = turno_data.get("paciente_id")
    if not p_id:
        return False, "Debe seleccionar un paciente.", None
    
    fecha_val = turno_data.get("fecha")
    t_date = date.fromisoformat(fecha_val) if isinstance(fecha_val, str) else fecha_val

    h_inicio_val = turno_data.get("hora_inicio")
    h_fin_val = turno_data.get("hora_fin")
    
    h_inicio = time.fromisoformat(h_inicio_val) if isinstance(h_inicio_val, str) else h_inicio_val
    h_fin = time.fromisoformat(h_fin_val) if isinstance(h_fin_val, str) else h_fin_val

    valid, count, msg = check_turnos_overlap(t_date, h_inicio, h_fin)
    if not valid:
        return False, msg, None

    turno_payload = dict(turno_data)
    turno_payload["fecha"] = t_date.isoformat()
    turno_payload["hora_inicio"] = h_inicio.strftime("%H:%M:%S")
    turno_payload["hora_fin"] = h_fin.strftime("%H:%M:%S")

    client = init_supabase_client()
    if client:
        try:
            res = client.table("turnos").insert(turno_payload).execute()
            if res.data:
                if turno_payload.get("estado") == "Asistió":
                    _sync_sesiones_local(p_id)
                return True, "Turno agendado exitosamente.", res.data[0]
        except Exception:
            try:
                base_turno = {
                    "paciente_id": turno_payload.get("paciente_id"),
                    "fecha": turno_payload.get("fecha"),
                    "hora_inicio": turno_payload.get("hora_inicio"),
                    "hora_fin": turno_payload.get("hora_fin"),
                    "duracion_minutos": turno_payload.get("duracion_minutos", 45),
                    "estado": turno_payload.get("estado", "Pendiente"),
                    "motivo_ajuste": turno_payload.get("motivo_ajuste"),
                    "notas": turno_payload.get("notas")
                }
                res = client.table("turnos").insert(base_turno).execute()
                if res.data:
                    if turno_payload.get("estado") == "Asistió":
                        _sync_sesiones_local(p_id)
                    return True, "Turno agendado exitosamente.", res.data[0]
            except Exception:
                pass

    # Fallback local
    store = _get_local_store()
    if "id" not in turno_payload or not turno_payload["id"]:
        turno_payload["id"] = str(uuid.uuid4())
    turno_payload.setdefault("created_at", datetime.now().isoformat())
    store["turnos"].append(turno_payload)
    if turno_payload.get("estado") == "Asistió":
        _sync_sesiones_local(p_id)
    return True, "Turno agendado exitosamente.", turno_payload

def update_turno(turno_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza horario, estado o notas de un turno y descuenta/sincroniza sesiones."""
    client = init_supabase_client()
    turno_actual = None

    if client:
        try:
            r = client.table("turnos").select("*").eq("id", str(turno_id)).execute()
            if r.data:
                turno_actual = r.data[0]
        except Exception:
            pass

    if not turno_actual:
        store = _get_local_store()
        for t in store["turnos"]:
            if str(t.get("id")) == str(turno_id):
                turno_actual = t
                break

    if not turno_actual:
        return False, "Turno no encontrado."

    paciente_id = turno_actual.get("paciente_id")

    clean_updates = dict(updates)
    if "fecha" in clean_updates and not isinstance(clean_updates["fecha"], str):
        clean_updates["fecha"] = clean_updates["fecha"].isoformat()
    if "hora_inicio" in clean_updates and not isinstance(clean_updates["hora_inicio"], str):
        clean_updates["hora_inicio"] = clean_updates["hora_inicio"].strftime("%H:%M:%S")
    if "hora_fin" in clean_updates and not isinstance(clean_updates["hora_fin"], str):
        clean_updates["hora_fin"] = clean_updates["hora_fin"].strftime("%H:%M:%S")

    if "hora_inicio" in clean_updates or "hora_fin" in clean_updates or "fecha" in clean_updates:
        chk_fecha = date.fromisoformat(clean_updates.get("fecha", turno_actual.get("fecha")))
        chk_hi = time.fromisoformat(clean_updates.get("hora_inicio", turno_actual.get("hora_inicio")))
        chk_hf = time.fromisoformat(clean_updates.get("hora_fin", turno_actual.get("hora_fin")))
        valid, _, msg = check_turnos_overlap(chk_fecha, chk_hi, chk_hf, exclude_turno_id=turno_id)
        if not valid:
            return False, msg

    clean_updates["updated_at"] = datetime.now().isoformat()

    if client:
        try:
            res = client.table("turnos").update(clean_updates).eq("id", str(turno_id)).execute()
            if res.data:
                _sync_sesiones_local(paciente_id)
                return True, "Turno actualizado correctamente."
        except Exception:
            try:
                base_keys = {'paciente_id', 'fecha', 'hora_inicio', 'hora_fin', 'duracion_minutos', 'estado', 'motivo_ajuste', 'notas', 'updated_at'}
                base_updates = {k: v for k, v in clean_updates.items() if k in base_keys}
                res = client.table("turnos").update(base_updates).eq("id", str(turno_id)).execute()
                if res.data:
                    _sync_sesiones_local(paciente_id)
                    return True, "Turno actualizado correctamente."
            except Exception:
                pass

    store = _get_local_store()
    for t in store["turnos"]:
        if str(t.get("id")) == str(turno_id):
            t.update(clean_updates)
            _sync_sesiones_local(paciente_id)
            return True, "Turno actualizado correctamente."
    return False, "Error al actualizar turno."

def delete_turno(turno_id: str) -> Tuple[bool, str]:
    """Elimina un turno y recalcula asistencias del paciente."""
    client = init_supabase_client()
    paciente_id = None

    if client:
        try:
            r = client.table("turnos").select("paciente_id").eq("id", str(turno_id)).execute()
            if r.data:
                paciente_id = r.data[0].get("paciente_id")
            client.table("turnos").delete().eq("id", str(turno_id)).execute()
        except Exception as e:
            print(f"Error eliminando turno: {e}")

    store = _get_local_store()
    for t in store.get("turnos", []):
        if str(t.get("id")) == str(turno_id):
            if not paciente_id:
                paciente_id = t.get("paciente_id")
            break
    store["turnos"] = [t for t in store.get("turnos", []) if str(t.get("id")) != str(turno_id)]
    if paciente_id:
        _sync_sesiones_local(paciente_id)
    return True, "Turno eliminado exitosamente."

def _sync_sesiones_local(paciente_id: str):
    """Calcula y descuenta sesiones_realizadas para el paciente según turnos 'Asistió'."""
    if not paciente_id:
        return
    client = init_supabase_client()
    if client:
        try:
            asist_res = client.table("turnos").select("id", count="exact").eq("paciente_id", str(paciente_id)).eq("estado", "Asistió").execute()
            total_asist = asist_res.count if asist_res.count is not None else 0
            client.table("pacientes").update({"sesiones_realizadas": total_asist}).eq("id", str(paciente_id)).execute()
        except Exception:
            pass

    store = _get_local_store()
    asistencias = sum(1 for t in store["turnos"] if str(t.get("paciente_id")) == str(paciente_id) and t.get("estado") == "Asistió")
    for p in store["pacientes"]:
        if str(p.get("id")) == str(paciente_id):
            p["sesiones_realizadas"] = asistencias
            break

# ==============================================================================
# OPERACIONES CRUD: PAGOS Y COSEGUROS (GESTIÓN DE COBROS Y SALDOS)
# ==============================================================================

def get_pagos(
    paciente_id: Optional[str] = None,
    turno_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Obtiene el listado de cobros y pagos registrados combinando base de datos y local."""
    pagos_map: Dict[str, Dict[str, Any]] = {}
    
    client = init_supabase_client()
    if client:
        try:
            req = client.table("pagos").select("*").order("fecha_pago", desc=True).order("created_at", desc=True)
            if paciente_id:
                req = req.eq("paciente_id", str(paciente_id))
            if turno_id:
                req = req.eq("turno_id", str(turno_id))
            if start_date:
                req = req.gte("fecha_pago", start_date.isoformat())
            if end_date:
                req = req.lte("fecha_pago", end_date.isoformat())
            res = req.execute()
            if res.data is not None:
                for p in res.data:
                    pagos_map[str(p["id"])] = dict(p)
        except Exception:
            pass

    store = _get_local_store()
    for p in store.get("pagos", []):
        p_id = str(p.get("id"))
        if p_id not in pagos_map:
            pagos_map[p_id] = dict(p)

    pagos = list(pagos_map.values())
    if paciente_id:
        pagos = [p for p in pagos if str(p.get("paciente_id")) == str(paciente_id)]
    if turno_id:
        pagos = [p for p in pagos if str(p.get("turno_id")) == str(turno_id)]
    if start_date:
        s_str = start_date.isoformat()
        pagos = [p for p in pagos if str(p.get("fecha_pago", "")) >= s_str]
    if end_date:
        e_str = end_date.isoformat()
        pagos = [p for p in pagos if str(p.get("fecha_pago", "")) <= e_str]

    return sorted(pagos, key=lambda x: (str(x.get("fecha_pago", "")), str(x.get("created_at", ""))), reverse=True)

def get_pago_by_id(pago_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un registro de pago específico por ID."""
    if not pago_id:
        return None
    client = init_supabase_client()
    if client:
        try:
            res = client.table("pagos").select("*").eq("id", str(pago_id)).limit(1).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    store = _get_local_store()
    for p in store.get("pagos", []):
        if str(p.get("id")) == str(pago_id):
            return p
    return None

def create_pago(pago_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registra un nuevo cobro/pago en el sistema.
    Permite montos manuales, frecuencias por sesión o tratamiento completo, y pagos parciales/señas.
    """
    if not pago_data.get("paciente_id"):
        return False, "Debe especificar el paciente.", None

    try:
        monto_val = float(pago_data.get("monto", 0))
        if monto_val < 0:
            return False, "El monto no puede ser negativo.", None
    except (ValueError, TypeError):
        return False, "El monto ingresado no es un número válido.", None

    if not pago_data.get("concepto"):
        return False, "Debe especificar el concepto o motivo del cobro.", None

    pago_payload = dict(pago_data)
    pago_payload["monto"] = monto_val
    if "fecha_pago" in pago_payload and isinstance(pago_payload["fecha_pago"], (date, datetime)):
        pago_payload["fecha_pago"] = pago_payload["fecha_pago"].isoformat()
    elif "fecha_pago" not in pago_payload:
        pago_payload["fecha_pago"] = date.today().isoformat()

    pago_payload.setdefault("modalidad", "Por sesión")
    pago_payload.setdefault("metodo_pago", "Efectivo")
    pago_payload.setdefault("sesiones_cubiertas", 1)
    
    if pago_payload.get("monto_total_esperado") is not None:
        try:
            pago_payload["monto_total_esperado"] = float(pago_payload["monto_total_esperado"])
        except (ValueError, TypeError):
            pago_payload["monto_total_esperado"] = None

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pagos").insert(pago_payload).execute()
            if res.data:
                # Si está vinculado a un turno, actualizar estado de pago del turno
                if pago_payload.get("turno_id"):
                    client.table("turnos").update({"estado_pago": "Abonado"}).eq("id", str(pago_payload["turno_id"])).execute()
                return True, "Pago registrado exitosamente.", res.data[0]
        except Exception as e:
            print(f"Error creando pago en Supabase: {e}")

    # Fallback local
    store = _get_local_store()
    if "id" not in pago_payload or not pago_payload["id"]:
        pago_payload["id"] = str(uuid.uuid4())
    pago_payload.setdefault("created_at", datetime.now().isoformat())
    store.setdefault("pagos", []).append(pago_payload)

    # Actualizar turno localmente si existe
    if pago_payload.get("turno_id"):
        for t in store.get("turnos", []):
            if str(t.get("id")) == str(pago_payload["turno_id"]):
                t["estado_pago"] = "Abonado"
                break

    return True, "Pago registrado exitosamente.", pago_payload

def update_pago(pago_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza un pago existente."""
    client = init_supabase_client()
    clean_updates = dict(updates)
    if "fecha_pago" in clean_updates and isinstance(clean_updates["fecha_pago"], (date, datetime)):
        clean_updates["fecha_pago"] = clean_updates["fecha_pago"].isoformat()
    if "monto" in clean_updates:
        clean_updates["monto"] = float(clean_updates["monto"])

    if client:
        try:
            res = client.table("pagos").update(clean_updates).eq("id", str(pago_id)).execute()
            if res.data:
                return True, "Pago actualizado correctamente."
        except Exception as e:
            print(f"Error actualizando pago: {e}")

    store = _get_local_store()
    for p in store.get("pagos", []):
        if str(p.get("id")) == str(pago_id):
            p.update(clean_updates)
            return True, "Pago actualizado correctamente."
    return False, "Pago no encontrado."

def delete_pago(pago_id: str) -> Tuple[bool, str]:
    """Elimina un pago registrado."""
    client = init_supabase_client()
    if client:
        try:
            client.table("pagos").delete().eq("id", str(pago_id)).execute()
            return True, "Pago eliminado exitosamente."
        except Exception as e:
            print(f"Error eliminando pago: {e}")

    store = _get_local_store()
    store["pagos"] = [p for p in store.get("pagos", []) if str(p.get("id")) != str(pago_id)]
    return True, "Pago eliminado exitosamente."

def get_resumen_financiero_paciente(paciente_id: str) -> Dict[str, Any]:
    """
    Calcula el resumen de cobros, total abonado, modalidad y saldos pendientes
    para un paciente particular o con obra social.
    """
    pagos = get_pagos(paciente_id=paciente_id)
    paciente = get_paciente_by_id(paciente_id) or {}
    
    total_abonado = sum(float(p.get("monto", 0) or 0) for p in pagos)
    sesiones_cubiertas = sum(int(p.get("sesiones_cubiertas", 1) or 1) for p in pagos)
    
    # Determinar si hay un monto total pactado (seña o paquete global)
    monto_total_pactado = None
    for p in pagos:
        if p.get("monto_total_esperado") and float(p.get("monto_total_esperado", 0)) > 0:
            if monto_total_pactado is None or float(p["monto_total_esperado"]) > monto_total_pactado:
                monto_total_pactado = float(p["monto_total_esperado"])

    saldo_pendiente = 0.0
    if monto_total_pactado is not None and monto_total_pactado > 0:
        saldo_pendiente = max(0.0, monto_total_pactado - total_abonado)
    else:
        # Si no hay paquete global pactado, estimamos en base a coseguro default y sesiones realizadas
        ses_realizadas = int(paciente.get("sesiones_realizadas", 0) or 0)
        coseguro_unitario = float(paciente.get("monto_coseguro_default", 0) or 0)
        if coseguro_unitario > 0 and ses_realizadas > 0:
            total_devengado = ses_realizadas * coseguro_unitario
            saldo_pendiente = max(0.0, total_devengado - total_abonado)

    return {
        "total_abonado": total_abonado,
        "cantidad_pagos": len(pagos),
        "pagos": pagos,
        "ultimo_pago": pagos[0] if pagos else None,
        "sesiones_cubiertas": sesiones_cubiertas,
        "monto_total_pactado": monto_total_pactado,
        "saldo_pendiente": saldo_pendiente
    }

# ==============================================================================
# OPERACIONES CRUD: EVOLUCIONES CLÍNICAS
# ==============================================================================

def get_evoluciones(paciente_id: str) -> List[Dict[str, Any]]:
    """Obtiene el historial clínico de evoluciones de un paciente."""
    if not paciente_id:
        return []
    client = init_supabase_client()
    if client:
        try:
            res = client.table("evoluciones").select("*").eq("paciente_id", str(paciente_id)).order("fecha", desc=True).execute()
            if res.data:
                return res.data
        except Exception:
            pass

    store = _get_local_store()
    evols = [e for e in store["evoluciones"] if str(e.get("paciente_id")) == str(paciente_id)]
    return sorted(evols, key=lambda x: str(x.get("fecha", "")), reverse=True)

def create_evolucion(evolucion_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Registra una nueva evolución médica."""
    if not evolucion_data.get("paciente_id") or not evolucion_data.get("nota_clinica"):
        return False, "La nota clínica y el paciente son obligatorios."

    client = init_supabase_client()
    if client:
        try:
            res = client.table("evoluciones").insert(evolucion_data).execute()
            if res.data:
                return True, "Evolución registrada exitosamente."
        except Exception as e:
            print(f"Error creando evolucion: {e}")

    store = _get_local_store()
    new_ev = dict(evolucion_data)
    if "id" not in new_ev or not new_ev["id"]:
        new_ev["id"] = str(uuid.uuid4())
    new_ev.setdefault("created_at", datetime.now().isoformat())
    store["evoluciones"].append(new_ev)
    return True, "Evolución registrada exitosamente."

def delete_evolucion(evolucion_id: str) -> Tuple[bool, str]:
    """Elimina una evolución clínica."""
    client = init_supabase_client()
    if client:
        try:
            client.table("evoluciones").delete().eq("id", str(evolucion_id)).execute()
            return True, "Evolución eliminada."
        except Exception:
            pass

    store = _get_local_store()
    store["evoluciones"] = [e for e in store["evoluciones"] if str(e.get("id")) != str(evolucion_id)]
    return True, "Evolución eliminada."

# ==============================================================================
# OPERACIONES: ARCHIVOS ADJUNTOS Y ESTUDIOS MÉDICOS
# ==============================================================================

def upload_paciente_archivo(
    paciente_id: str,
    file_bytes: bytes,
    filename: str,
    tipo_documento: str = "Orden Médica"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Guarda una imagen o documento médico vinculado al paciente."""
    if not paciente_id or not file_bytes:
        return False, "Faltan datos del archivo o paciente.", None

    url, _, bucket_name = get_supabase_credentials()
    file_ext = filename.split(".")[-1] if "." in filename else "jpg"
    unique_filename = f"{paciente_id}/{uuid.uuid4().hex[:8]}_{filename}"
    public_url = f"{url}/storage/v1/object/public/{bucket_name}/{unique_filename}"
    tamano = len(file_bytes)

    client = init_supabase_client()
    if client:
        try:
            client.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": f"image/{file_ext}"}
            )
            record = {
                "paciente_id": str(paciente_id),
                "nombre_archivo": filename,
                "storage_path": unique_filename,
                "tipo_documento": tipo_documento,
                "tamano_bytes": tamano,
                "public_url": public_url
            }
            res = client.table("archivos_pacientes").insert(record).execute()
            if res.data:
                return True, "Archivo guardado exitosamente.", res.data[0]
        except Exception as e:
            print(f"Error subiendo archivo: {e}")

    # Fallback local
    store = _get_local_store()
    record = {
        "id": str(uuid.uuid4()),
        "paciente_id": str(paciente_id),
        "nombre_archivo": filename,
        "storage_path": unique_filename,
        "tipo_documento": tipo_documento,
        "tamano_bytes": tamano,
        "public_url": None,
        "file_bytes": file_bytes,
        "created_at": datetime.now().isoformat()
    }
    store["archivos_pacientes"].append(record)
    return True, "Archivo guardado exitosamente.", record

def get_paciente_archivos(paciente_id: str) -> List[Dict[str, Any]]:
    """Obtiene los archivos subidos para un paciente."""
    if not paciente_id:
        return []
    client = init_supabase_client()
    if client:
        try:
            res = client.table("archivos_pacientes").select("*").eq("paciente_id", str(paciente_id)).order("created_at", desc=True).execute()
            if res.data:
                return res.data
        except Exception:
            pass

    store = _get_local_store()
    return [a for a in store["archivos_pacientes"] if str(a.get("paciente_id")) == str(paciente_id)]

def delete_paciente_archivo(archivo_id: str, storage_path: Optional[str] = None) -> Tuple[bool, str]:
    """Elimina el archivo de la base de datos."""
    client = init_supabase_client()
    _, _, bucket_name = get_supabase_credentials()

    if client:
        try:
            if storage_path:
                client.storage.from_(bucket_name).remove([storage_path])
            client.table("archivos_pacientes").delete().eq("id", str(archivo_id)).execute()
            return True, "Archivo eliminado correctamente."
        except Exception as e:
            print(f"Error eliminando archivo: {e}")

    store = _get_local_store()
    store["archivos_pacientes"] = [a for a in store["archivos_pacientes"] if str(a.get("id")) != str(archivo_id)]
    return True, "Archivo eliminado correctamente."
