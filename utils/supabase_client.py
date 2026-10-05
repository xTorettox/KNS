"""
Módulo de base de datos y persistencia (PostgreSQL y Almacenamiento de Archivos).
Implementa validaciones de negocio, cálculo de superposiciones de turnos,
sincronización de sesiones, pagos y gestión documental.
"""
import os
import io
import json
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
    """Obtiene URL, Key y Bucket desde st.secrets o variables de entorno de forma segura."""
    url = ""
    key = ""
    bucket = "pacientes-adjuntos"
    
    try:
        if hasattr(st, "secrets") and "supabase" in st.secrets:
            url = st.secrets["supabase"].get("url", "")
            key = st.secrets["supabase"].get("key", "")
            bucket = st.secrets["supabase"].get("bucket_name", "pacientes-adjuntos")
    except Exception:
        pass
    
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
    
    default_data = {
        "pacientes": [],
        "turnos": [],
        "pagos": [],
        "evoluciones": [],
        "archivos_pacientes": [],
        "tokens_registro": {}
    }

    try:
        if hasattr(st, "session_state"):
            if "local_db" not in st.session_state:
                st.session_state.local_db = default_data
            else:
                st.session_state.local_db.setdefault("pagos", default_data["pagos"])
                st.session_state.local_db.setdefault("tokens_registro", default_data["tokens_registro"])
            return st.session_state.local_db
    except Exception:
        pass

    if _GLOBAL_FALLBACK_DB is None:
        _GLOBAL_FALLBACK_DB = default_data
    return _GLOBAL_FALLBACK_DB

# ==============================================================================
# AUXILIARES DE METADATOS DE PACIENTES (TIPO DOC, SEXO, EMAIL, DOMICILIO, ETC.)
# ==============================================================================

PACIENTE_META_KEYS = [
    "tipo_doc", "sexo", "email", "plan_obra_social", "numero_afiliado",
    "direccion", "localidad", "provincia", "fecha_nacimiento", "monto_coseguro_default",
    "ficha_completada", "ficha_completada_at", "pedido_medico_url"
]

def _unpack_paciente_data(p: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae metadatos extendidos desde notas_generales o campos nativos."""
    if not p:
        return {}
    res = dict(p)
    notas = str(res.get("notas_generales") or "")
    if "[FICHA_DATOS]" in notas and "[/FICHA_DATOS]" in notas:
        try:
            start = notas.find("[FICHA_DATOS]") + len("[FICHA_DATOS]")
            end = notas.find("[/FICHA_DATOS]")
            json_str = notas[start:end]
            meta = json.loads(json_str)
            for k, v in meta.items():
                if k not in res or res[k] is None or res[k] == "":
                    res[k] = v
            clean_notas = (notas[:notas.find("[FICHA_DATOS]")] + notas[end + len("[/FICHA_DATOS]"): ]).strip()
            res["notas_limpias"] = clean_notas
        except Exception:
            pass
    return res

def _pack_paciente_data_for_db(data: Dict[str, Any], existing_paciente: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Empaqueta campos base para columnas de Supabase y campos extendidos en notas_generales."""
    clean = dict(data)
    current_meta = {}
    
    if existing_paciente:
        unpacked = _unpack_paciente_data(existing_paciente)
        for mk in PACIENTE_META_KEYS:
            if mk in unpacked and unpacked[mk] is not None:
                current_meta[mk] = unpacked[mk]
                
    for mk in PACIENTE_META_KEYS:
        if mk in clean:
            val = clean.pop(mk)
            if val is not None:
                current_meta[mk] = val
                
    # Manejar notas_generales
    notas_base = str(clean.get("notas_generales") or "")
    if "[FICHA_DATOS]" in notas_base and "[/FICHA_DATOS]" in notas_base:
        start = notas_base.find("[FICHA_DATOS]")
        end = notas_base.find("[/FICHA_DATOS]") + len("[/FICHA_DATOS]")
        notas_base = (notas_base[:start] + notas_base[end:]).strip()
        
    if current_meta:
        meta_json = json.dumps(current_meta, ensure_ascii=False)
        final_notas = f"[FICHA_DATOS]{meta_json}[/FICHA_DATOS]" + (f"\n{notas_base}" if notas_base else "")
        clean["notas_generales"] = final_notas
        
    return clean, current_meta

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
                    unpacked = _unpack_paciente_data(p)
                    pacientes_map[str(unpacked["id"])] = unpacked
        except Exception:
            pass

    # 2. Combinar/complementar con almacenamiento local
    store = _get_local_store()
    for p in store.get("pacientes", []):
        unpacked = _unpack_paciente_data(p)
        p_id = str(unpacked.get("id"))
        if p_id in pacientes_map:
            for k, v in unpacked.items():
                if k not in pacientes_map[p_id] or pacientes_map[p_id][k] is None:
                    pacientes_map[p_id][k] = v
        else:
            if not activo_only or unpacked.get("activo", True):
                pacientes_map[p_id] = unpacked

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
            or q in str(p.get("telefono", "")).lower()
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
            local_p = _unpack_paciente_data(p)
            break

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").select("*").eq("id", str(paciente_id)).limit(1).execute()
            if res.data and len(res.data) > 0:
                remote_p = _unpack_paciente_data(res.data[0])
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
    raw_payload = dict(paciente_data)
    if "id" not in raw_payload or not raw_payload["id"]:
        raw_payload["id"] = str(uuid.uuid4())
    raw_payload.setdefault("created_at", datetime.now().isoformat())
    raw_payload.setdefault("sesiones_realizadas", 0)
    raw_payload.setdefault("activo", True)

    db_payload, meta = _pack_paciente_data_for_db(raw_payload)

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").insert(db_payload).execute()
            if res.data:
                created_row = _unpack_paciente_data(res.data[0])
                for k, v in raw_payload.items():
                    created_row.setdefault(k, v)
                store.setdefault("pacientes", []).append(created_row)
                return True, "Paciente registrado exitosamente.", created_row
        except Exception as e:
            # Reintentar solo con columnas nativas estándar
            try:
                base_keys = {'id', 'nombre_completo', 'dni', 'edad', 'telefono', 'obra_social', 'patologia', 'sesiones_totales', 'sesiones_realizadas', 'activo', 'notas_generales'}
                base_payload = {k: v for k, v in db_payload.items() if k in base_keys}
                res = client.table("pacientes").insert(base_payload).execute()
                if res.data:
                    created_row = _unpack_paciente_data(res.data[0])
                    for k, v in raw_payload.items():
                        created_row.setdefault(k, v)
                    store.setdefault("pacientes", []).append(created_row)
                    return True, "Paciente registrado exitosamente.", created_row
            except Exception:
                pass

    # Guardar en local store
    unpacked_local = _unpack_paciente_data(raw_payload)
    store.setdefault("pacientes", []).append(unpacked_local)
    return True, "Paciente registrado exitosamente.", unpacked_local

def update_paciente(paciente_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza los datos de un paciente."""
    existing = get_paciente_by_id(paciente_id)
    db_updates, meta = _pack_paciente_data_for_db(updates, existing_paciente=existing)

    client = init_supabase_client()
    if client:
        try:
            db_updates["updated_at"] = datetime.now().isoformat()
            res = client.table("pacientes").update(db_updates).eq("id", str(paciente_id)).execute()
            if res.data:
                pass
        except Exception:
            try:
                base_keys = {'nombre_completo', 'dni', 'edad', 'telefono', 'obra_social', 'patologia', 'sesiones_totales', 'sesiones_realizadas', 'activo', 'notas_generales', 'updated_at'}
                base_updates = {k: v for k, v in db_updates.items() if k in base_keys}
                client.table("pacientes").update(base_updates).eq("id", str(paciente_id)).execute()
            except Exception:
                pass

    store = _get_local_store()
    for p in store["pacientes"]:
        if str(p.get("id")) == str(paciente_id):
            p.update(updates)
            p.update(meta)
            break
            
    return True, "Paciente actualizado exitosamente."

def delete_paciente(paciente_id: str) -> Tuple[bool, str]:
    """Elimina un paciente y sus turnos/evoluciones asociadas."""
    client = init_supabase_client()
    if client:
        try:
            client.table("pacientes").delete().eq("id", str(paciente_id)).execute()
        except Exception:
            pass

    store = _get_local_store()
    store["pacientes"] = [p for p in store["pacientes"] if str(p.get("id")) != str(paciente_id)]
    store["turnos"] = [t for t in store["turnos"] if str(t.get("paciente_id")) != str(paciente_id)]
    store["evoluciones"] = [e for e in store["evoluciones"] if str(e.get("paciente_id")) != str(paciente_id)]
    store["pagos"] = [p for p in store["pagos"] if str(p.get("paciente_id")) != str(paciente_id)]
    return True, "Paciente eliminado correctamente."

# ==============================================================================
# OPERACIONES CRUD: TURNOS
# ==============================================================================

def get_turnos(
    target_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    paciente_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Obtiene los turnos combinando base de datos remota, local y pagos asociados."""
    turnos_map: Dict[str, Dict[str, Any]] = {}
    
    # Obtener pacientes y pagos para cruzarlos
    pacientes_lookup = {str(p["id"]): p for p in get_pacientes()}
    pagos_lookup: Dict[str, Dict[str, Any]] = {}
    for pg in get_pagos():
        t_pg_id = str(pg.get("turno_id") or "")
        if t_pg_id and t_pg_id not in pagos_lookup:
            pagos_lookup[t_pg_id] = pg

    client = init_supabase_client()
    if client:
        try:
            req = client.table("turnos").select("*").order("fecha").order("hora_inicio")
            if target_date:
                req = req.eq("fecha", target_date.isoformat())
            if start_date:
                req = req.gte("fecha", start_date.isoformat())
            if end_date:
                req = req.lte("fecha", end_date.isoformat())
            if paciente_id:
                req = req.eq("paciente_id", str(paciente_id))
            res = req.execute()
            if res.data:
                for t in res.data:
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
                    t["paciente_ficha_completada"] = bool(p_info.get("ficha_completada", False))
                    
                    # Cruzar con pagos
                    t_id_str = str(t["id"])
                    if t_id_str in pagos_lookup:
                        pago_asoc = pagos_lookup[t_id_str]
                        t["estado_pago"] = "Abonado"
                        t["monto_coseguro"] = float(pago_asoc.get("monto", 0) or 0)
                    else:
                        t.setdefault("monto_coseguro", float(p_info.get("monto_coseguro_default", 0) or 0))
                        t.setdefault("estado_pago", "Pendiente")
                        
                    turnos_map[t_id_str] = t
        except Exception:
            pass

    # Combinar con almacenamiento local
    store = _get_local_store()
    for t in store.get("turnos", []):
        t_id = str(t.get("id"))
        if t_id not in turnos_map:
            p = pacientes_lookup.get(str(t.get("paciente_id")), {})
            t_copy = dict(t)
            t_copy["paciente_nombre"] = p.get("nombre_completo", "Paciente")
            t_copy["paciente_telefono"] = p.get("telefono", "")
            t_copy["paciente_obra_social"] = p.get("obra_social", "Particular")
            t_copy["paciente_numero_afiliado"] = p.get("numero_afiliado", "")
            t_copy["paciente_fecha_nacimiento"] = p.get("fecha_nacimiento", None)
            t_copy["paciente_monto_coseguro_default"] = float(p.get("monto_coseguro_default", 0) or 0)
            t_copy["paciente_sesiones_totales"] = p.get("sesiones_totales", 10)
            t_copy["paciente_sesiones_realizadas"] = p.get("sesiones_realizadas", 0)
            t_copy["paciente_ficha_completada"] = bool(p.get("ficha_completada", False))
            
            if t_id in pagos_lookup:
                pago_asoc = pagos_lookup[t_id]
                t_copy["estado_pago"] = "Abonado"
                t_copy["monto_coseguro"] = float(pago_asoc.get("monto", 0) or 0)
            else:
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

def _time_to_minutes(t_val) -> int:
    """Convierte objeto time o string 'HH:MM:SS' a minutos del día."""
    if isinstance(t_val, str):
        parts = t_val.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    elif isinstance(t_val, time):
        return t_val.hour * 60 + t_val.minute
    return 0

def check_turnos_overlap(
    target_date: date,
    hora_inicio: time,
    hora_fin: time,
    exclude_turno_id: Optional[str] = None
) -> Tuple[bool, int, str]:
    """Verifica que no se supere la capacidad máxima de pacientes simultáneos."""
    app_config = get_app_config()
    max_simultaneous = app_config.get("max_simultaneous_patients", 2)
    
    turnos_dia = get_turnos(target_date=target_date)
    activos = [
        t for t in turnos_dia 
        if t.get("estado") != "Cancelado" 
        and (not exclude_turno_id or str(t.get("id")) != str(exclude_turno_id))
    ]

    new_start = _time_to_minutes(hora_inicio)
    new_end = _time_to_minutes(hora_fin)

    if new_start >= new_end:
        return False, 0, "La hora de inicio debe ser anterior a la hora de fin."

    max_coincidentes = 0
    for m in range(new_start, new_end, 5):
        coincidencias_en_minuto = 0
        for t in activos:
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
        except Exception:
            pass

    store = _get_local_store()
    for t in store["turnos"]:
        if str(t.get("id")) == str(turno_id):
            paciente_id = t.get("paciente_id")
            break
            
    store["turnos"] = [t for t in store["turnos"] if str(t.get("id")) != str(turno_id)]
    
    if paciente_id:
        _sync_sesiones_local(paciente_id)
    return True, "Turno eliminado exitosamente."

def _sync_sesiones_local(paciente_id: str):
    """Sincroniza y recalcula el contador de sesiones realizadas de un paciente."""
    if not paciente_id:
        return
    client = init_supabase_client()
    asistidos_count = 0
    if client:
        try:
            res = client.table("turnos").select("id", count="exact").eq("paciente_id", str(paciente_id)).eq("estado", "Asistió").execute()
            asistidos_count = res.count if res.count is not None else len(res.data or [])
            client.table("pacientes").update({"sesiones_realizadas": asistidos_count}).eq("id", str(paciente_id)).execute()
        except Exception:
            pass

    store = _get_local_store()
    local_count = sum(1 for t in store.get("turnos", []) if str(t.get("paciente_id")) == str(paciente_id) and t.get("estado") == "Asistió")
    final_count = max(asistidos_count, local_count)
    for p in store.get("pacientes", []):
        if str(p.get("id")) == str(paciente_id):
            p["sesiones_realizadas"] = final_count
            break

# ==============================================================================
# OPERACIONES CRUD: PAGOS Y COSEGUROS (GESTIÓN DE COBROS Y SALDOS)
# ==============================================================================

MODALIDAD_TO_DB = {
    "Por sesión": "sesion",
    "Por sesion": "sesion",
    "Tratamiento completo": "completo",
    "Pago parcial / Seña": "adelanto",
    "Pago parcial / Sena": "adelanto",
    "sesion": "sesion",
    "completo": "completo",
    "paquete": "completo",
    "adelanto": "adelanto",
    "otro": "adelanto"
}

MODALIDAD_FROM_DB = {
    "sesion": "Por sesión",
    "completo": "Tratamiento completo",
    "paquete": "Tratamiento completo",
    "adelanto": "Pago parcial / Seña",
    "otro": "Pago parcial / Seña"
}

def _normalize_pago_record(p: Dict[str, Any]) -> Dict[str, Any]:
    """Estandariza campos para asegurar interoperabilidad entre DB y vistas."""
    if not p:
        return {}
    item = dict(p)
    
    # Fecha de pago
    f = item.get("fecha") or item.get("fecha_pago") or date.today().isoformat()
    if isinstance(f, (date, datetime)):
        f = f.isoformat()
    item["fecha"] = f
    item["fecha_pago"] = f
    
    # Modalidad
    db_mod = str(item.get("modalidad", "sesion")).lower()
    item["modalidad_db"] = db_mod
    item["modalidad"] = MODALIDAD_FROM_DB.get(db_mod, item.get("modalidad", "Por sesión"))
    
    # Montos
    monto_val = float(item.get("monto", 0) or 0)
    item["monto"] = monto_val
    monto_tot = float(item.get("monto_total_tratamiento") or item.get("monto_total_esperado") or monto_val)
    item["monto_total_tratamiento"] = monto_tot
    item["monto_total_esperado"] = monto_tot
    item["saldo_restante"] = float(item.get("saldo_restante", max(0.0, monto_tot - monto_val)) or 0)
    
    # Metodo de pago
    item.setdefault("metodo_pago", "Efectivo")
    item.setdefault("sesiones_cubiertas", 1)
    return item

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
            req = client.table("pagos").select("*").order("fecha", desc=True).order("created_at", desc=True)
            if paciente_id:
                req = req.eq("paciente_id", str(paciente_id))
            if turno_id:
                req = req.eq("turno_id", str(turno_id))
            if start_date:
                req = req.gte("fecha", start_date.isoformat())
            if end_date:
                req = req.lte("fecha", end_date.isoformat())
            res = req.execute()
            if res.data is not None:
                for p in res.data:
                    norm = _normalize_pago_record(p)
                    pagos_map[str(norm["id"])] = norm
        except Exception:
            pass

    store = _get_local_store()
    for p in store.get("pagos", []):
        norm = _normalize_pago_record(p)
        p_id = str(norm.get("id"))
        if p_id not in pagos_map:
            pagos_map[p_id] = norm

    pagos = list(pagos_map.values())
    if paciente_id:
        pagos = [p for p in pagos if str(p.get("paciente_id")) == str(paciente_id)]
    if turno_id:
        pagos = [p for p in pagos if str(p.get("turno_id")) == str(turno_id)]
    if start_date:
        s_str = start_date.isoformat()
        pagos = [p for p in pagos if str(p.get("fecha", "")) >= s_str]
    if end_date:
        e_str = end_date.isoformat()
        pagos = [p for p in pagos if str(p.get("fecha", "")) <= e_str]

    return sorted(pagos, key=lambda x: (str(x.get("fecha", "")), str(x.get("created_at", ""))), reverse=True)

def get_pago_by_id(pago_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un registro de pago específico por ID."""
    if not pago_id:
        return None
    client = init_supabase_client()
    if client:
        try:
            res = client.table("pagos").select("*").eq("id", str(pago_id)).limit(1).execute()
            if res.data:
                return _normalize_pago_record(res.data[0])
        except Exception:
            pass

    store = _get_local_store()
    for p in store.get("pagos", []):
        if str(p.get("id")) == str(pago_id):
            return _normalize_pago_record(p)
    return None

def create_pago(pago_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Registra un nuevo cobro/pago en el sistema.
    Soporta cobros por sesión, paquetes completos y pagos parciales/señas.
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

    # Normalizar fecha
    fecha_val = pago_data.get("fecha") or pago_data.get("fecha_pago") or date.today().isoformat()
    if isinstance(fecha_val, (date, datetime)):
        fecha_str = fecha_val.isoformat()
    else:
        fecha_str = str(fecha_val)

    # Normalizar modalidad
    raw_mod = str(pago_data.get("modalidad", "Por sesión"))
    db_modalidad = MODALIDAD_TO_DB.get(raw_mod, "sesion")

    # Normalizar montos
    monto_tot = float(pago_data.get("monto_total_tratamiento") or pago_data.get("monto_total_esperado") or monto_val)
    saldo_rest = float(pago_data.get("saldo_restante", max(0.0, monto_tot - monto_val)))

    metodo_val = pago_data.get("metodo_pago", "Efectivo")
    if metodo_val not in ["Efectivo", "Transferencia / MP", "Tarjeta Débito", "Tarjeta Crédito", "Otro"]:
        metodo_val = "Efectivo"

    pago_id = str(uuid.uuid4())
    turno_id_val = str(pago_data["turno_id"]) if pago_data.get("turno_id") else None

    # Payload exacto para PostgreSQL / Supabase
    db_payload = {
        "id": pago_id,
        "paciente_id": str(pago_data["paciente_id"]),
        "turno_id": turno_id_val,
        "fecha": fecha_str,
        "monto": monto_val,
        "concepto": str(pago_data.get("concepto", "Cobro de Sesión")),
        "modalidad": db_modalidad,
        "sesiones_cubiertas": int(pago_data.get("sesiones_cubiertas", 1)),
        "monto_total_tratamiento": monto_tot,
        "saldo_restante": saldo_rest,
        "metodo_pago": metodo_val,
        "comprobante_nro": str(pago_data.get("comprobante_nro") or "") or None,
        "notas": str(pago_data.get("notas") or "") or None
    }

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pagos").insert(db_payload).execute()
            if res.data:
                normalized_result = _normalize_pago_record(res.data[0])
                # Guardar en local store
                store = _get_local_store()
                store.setdefault("pagos", []).append(normalized_result)
                return True, "Pago registrado exitosamente.", normalized_result
        except Exception as e:
            print(f"Aviso guardando pago en DB: {e}")

    # Fallback local
    normalized_local = _normalize_pago_record(db_payload)
    normalized_local.setdefault("created_at", datetime.now().isoformat())
    store = _get_local_store()
    store.setdefault("pagos", []).append(normalized_local)

    return True, "Pago registrado exitosamente.", normalized_local

def update_pago(pago_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza un pago existente."""
    clean_updates = dict(updates)
    if "fecha_pago" in clean_updates:
        clean_updates["fecha"] = clean_updates.pop("fecha_pago")
    if "fecha" in clean_updates and isinstance(clean_updates["fecha"], (date, datetime)):
        clean_updates["fecha"] = clean_updates["fecha"].isoformat()
    if "monto" in clean_updates:
        clean_updates["monto"] = float(clean_updates["monto"])
    if "modalidad" in clean_updates:
        clean_updates["modalidad"] = MODALIDAD_TO_DB.get(clean_updates["modalidad"], "sesion")

    client = init_supabase_client()
    if client:
        try:
            client.table("pagos").update(clean_updates).eq("id", str(pago_id)).execute()
        except Exception as e:
            print(f"Error actualizando pago en DB: {e}")

    store = _get_local_store()
    for p in store.get("pagos", []):
        if str(p.get("id")) == str(pago_id):
            p.update(clean_updates)
            p.update(_normalize_pago_record(p))
            return True, "Pago actualizado correctamente."
            
    return True, "Pago actualizado correctamente."

def delete_pago(pago_id: str) -> Tuple[bool, str]:
    """Elimina un pago registrado."""
    client = init_supabase_client()
    if client:
        try:
            client.table("pagos").delete().eq("id", str(pago_id)).execute()
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
# OPERACIONES: ARCHIVOS ADJUNTOS Y PEDIDOS MÉDICOS
# ==============================================================================

def upload_paciente_archivo(
    paciente_id: str,
    file_bytes: bytes,
    filename: str,
    tipo_documento: str = "Pedido Médico"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Guarda una imagen o documento médico vinculado al paciente."""
    if not paciente_id or not file_bytes:
        return False, "Faltan datos del archivo o paciente.", None

    url, _, bucket_name = get_supabase_credentials()
    file_ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    content_type = "application/pdf" if file_ext == "pdf" else f"image/{file_ext if file_ext in ['jpeg', 'png', 'webp'] else 'jpeg'}"
    
    unique_filename = f"{paciente_id}/{uuid.uuid4().hex[:8]}_{filename}"
    public_url = f"{url}/storage/v1/object/public/{bucket_name}/{unique_filename}"
    tamano = len(file_bytes)

    client = init_supabase_client()
    if client:
        try:
            client.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": content_type}
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
        "public_url": public_url,
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
    return [a for a in store.get("archivos_pacientes", []) if str(a.get("paciente_id")) == str(paciente_id)]

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
