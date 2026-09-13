"""
Módulo de conexión y operaciones CRUD con Supabase (PostgreSQL y Supabase Storage).
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
    """Crea e inicializa la instancia singleton del cliente Supabase."""
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
        print(f"Error inicializando Supabase client: {e}")
        return None

# ==============================================================================
# ALMACENAMIENTO EN MEMORIA / FALLBACK LOCAL
# ==============================================================================
# Garantiza que si la base en Supabase aún no tiene el script SQL corrido,
# la aplicación funcione en modo demostración interactivo sin romperse.

# Variable global en caso de ejecución fuera del contexto de Streamlit
_GLOBAL_FALLBACK_DB: Optional[Dict[str, List[Dict[str, Any]]]] = None

def _get_local_store() -> Dict[str, List[Dict[str, Any]]]:
    """Inicializa y devuelve almacenamiento local en sesión de Streamlit o fallback global."""
    global _GLOBAL_FALLBACK_DB
    today_str = date.today().isoformat()
    
    default_data = {
        "pacientes": [
            {
                "id": "a1111111-1111-1111-1111-111111111111",
                "nombre_completo": "Carlos Menéndez",
                "dni": "28456123",
                "edad": 46,
                "telefono": "+5491144445555",
                "obra_social": "OSDE 210",
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
                "edad": 32,
                "telefono": "+5491155556666",
                "obra_social": "Swiss Medical",
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
                "edad": 50,
                "telefono": "+5491166667777",
                "obra_social": "Galeno Silver",
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
                "motivo_ajuste": None,
                "notas": "Crioterapia + propiocepción en bosu",
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
    """Obtiene la lista de pacientes desde Supabase o fallback local."""
    client = init_supabase_client()
    if client:
        try:
            req = client.table("pacientes").select("*").order("nombre_completo")
            if activo_only:
                req = req.eq("activo", True)
            res = req.execute()
            pacientes = res.data if res.data else []
            if query:
                q = query.lower()
                pacientes = [p for p in pacientes if q in str(p.get("nombre_completo", "")).lower() or q in str(p.get("dni", "")).lower() or q in str(p.get("obra_social", "")).lower()]
            return pacientes
        except Exception:
            # Fallback a local si la tabla aún no existe
            pass

    store = _get_local_store()
    pacientes = list(store["pacientes"])
    if activo_only:
        pacientes = [p for p in pacientes if p.get("activo", True)]
    if query:
        q = query.lower()
        pacientes = [p for p in pacientes if q in str(p.get("nombre_completo", "")).lower() or q in str(p.get("dni", "")).lower() or q in str(p.get("obra_social", "")).lower()]
    return sorted(pacientes, key=lambda x: x.get("nombre_completo", ""))

def get_paciente_by_id(paciente_id: str) -> Optional[Dict[str, Any]]:
    """Busca un paciente específico por su ID."""
    if not paciente_id:
        return None
    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").select("*").eq("id", str(paciente_id)).limit(1).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    store = _get_local_store()
    for p in store["pacientes"]:
        if str(p.get("id")) == str(paciente_id):
            return p
    return None

def create_paciente(paciente_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Crea un nuevo paciente en la base de datos."""
    if not paciente_data.get("nombre_completo"):
        return False, "El nombre y apellido son obligatorios.", None

    client = init_supabase_client()
    if client:
        try:
            res = client.table("pacientes").insert(paciente_data).execute()
            if res.data:
                return True, "Paciente registrado exitosamente.", res.data[0]
        except Exception as e:
            # Si falla la llamada remota, guardar en local
            print(f"Supabase create_paciente error: {e}")

    # Fallback local
    store = _get_local_store()
    new_p = dict(paciente_data)
    if "id" not in new_p or not new_p["id"]:
        new_p["id"] = str(uuid.uuid4())
    new_p.setdefault("created_at", datetime.now().isoformat())
    new_p.setdefault("sesiones_realizadas", 0)
    new_p.setdefault("activo", True)
    store["pacientes"].append(new_p)
    return True, "Paciente guardado exitosamente.", new_p

def update_paciente(paciente_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza los datos de un paciente."""
    client = init_supabase_client()
    if client:
        try:
            updates["updated_at"] = datetime.now().isoformat()
            res = client.table("pacientes").update(updates).eq("id", str(paciente_id)).execute()
            if res.data:
                return True, "Paciente actualizado exitosamente."
        except Exception as e:
            print(f"Supabase update_paciente error: {e}")

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
            return True, "Paciente eliminado correctamente."
        except Exception as e:
            print(f"Supabase delete_paciente error: {e}")

    store = _get_local_store()
    store["pacientes"] = [p for p in store["pacientes"] if str(p.get("id")) != str(paciente_id)]
    store["turnos"] = [t for t in store["turnos"] if str(t.get("paciente_id")) != str(paciente_id)]
    store["evoluciones"] = [e for e in store["evoluciones"] if str(e.get("paciente_id")) != str(paciente_id)]
    return True, "Paciente eliminado correctamente."

# ==============================================================================
# OPERACIONES CRUD: TURNOS Y AGENDA
# ==============================================================================

def get_turnos(target_date: Optional[date] = None, paciente_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Obtiene los turnos filtrados por fecha o paciente con datos del paciente."""
    client = init_supabase_client()
    if client:
        try:
            req = client.table("turnos").select("*, pacientes(id, nombre_completo, telefono, obra_social, sesiones_totales, sesiones_realizadas)").order("hora_inicio")
            if target_date:
                req = req.eq("fecha", target_date.isoformat())
            if paciente_id:
                req = req.eq("paciente_id", str(paciente_id))
            res = req.execute()
            if res.data is not None:
                # Normalizar objeto paciente si viene anidado
                turnos = []
                for t in res.data:
                    p_info = t.get("pacientes") or {}
                    t["paciente_nombre"] = p_info.get("nombre_completo", "Paciente Desconocido")
                    t["paciente_telefono"] = p_info.get("telefono", "")
                    t["paciente_obra_social"] = p_info.get("obra_social", "")
                    t["paciente_sesiones_totales"] = p_info.get("sesiones_totales", 10)
                    t["paciente_sesiones_realizadas"] = p_info.get("sesiones_realizadas", 0)
                    turnos.append(t)
                return turnos
        except Exception:
            pass

    store = _get_local_store()
    turnos = list(store["turnos"])
    if target_date:
        t_date_str = target_date.isoformat()
        turnos = [t for t in turnos if t.get("fecha") == t_date_str]
    if paciente_id:
        turnos = [t for t in turnos if str(t.get("paciente_id")) == str(paciente_id)]
    
    # Cruzar datos con pacientes
    pacientes_map = {str(p["id"]): p for p in store["pacientes"]}
    for t in turnos:
        p = pacientes_map.get(str(t.get("paciente_id")), {})
        t["paciente_nombre"] = p.get("nombre_completo", "Paciente")
        t["paciente_telefono"] = p.get("telefono", "")
        t["paciente_obra_social"] = p.get("obra_social", "")
        t["paciente_sesiones_totales"] = p.get("sesiones_totales", 10)
        t["paciente_sesiones_realizadas"] = p.get("sesiones_realizadas", 0)
        
    return sorted(turnos, key=lambda x: str(x.get("hora_inicio", "")))

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
    # Filtrar cancelados y el turno que se está editando
    turnos_activos = [
        t for t in turnos_dia
        if t.get("estado") != "Cancelado" and (exclude_turno_id is None or str(t.get("id")) != str(exclude_turno_id))
    ]

    req_start = _time_to_minutes(hora_inicio)
    req_end = _time_to_minutes(hora_fin)

    if req_start >= req_end:
        return False, 0, "La hora de inicio debe ser anterior a la hora de finalización."

    # Revisar cada minuto del intervalo solicitado
    max_coincidentes = 0
    for m in range(req_start, req_end, 5): # Muestreo cada 5 minutos
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
    if isinstance(fecha_val, str):
        t_date = date.fromisoformat(fecha_val)
    else:
        t_date = fecha_val

    # Parsear horas
    h_inicio_val = turno_data.get("hora_inicio")
    h_fin_val = turno_data.get("hora_fin")
    
    h_inicio = time.fromisoformat(h_inicio_val) if isinstance(h_inicio_val, str) else h_inicio_val
    h_fin = time.fromisoformat(h_fin_val) if isinstance(h_fin_val, str) else h_fin_val

    # Validar overlap
    valid, count, msg = check_turnos_overlap(t_date, h_inicio, h_fin)
    if not valid:
        return False, msg, None

    # Formatear strings para base
    turno_payload = dict(turno_data)
    turno_payload["fecha"] = t_date.isoformat()
    turno_payload["hora_inicio"] = h_inicio.strftime("%H:%M:%S")
    turno_payload["hora_fin"] = h_fin.strftime("%H:%M:%S")

    client = init_supabase_client()
    if client:
        try:
            res = client.table("turnos").insert(turno_payload).execute()
            if res.data:
                # Sincronizar sesiones si fue creado directamente como 'Asistió'
                if turno_payload.get("estado") == "Asistió":
                    _sync_sesiones_local(p_id)
                return True, "Turno agendado exitosamente.", res.data[0]
        except Exception as e:
            print(f"Supabase create_turno error: {e}")

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

    # Obtener turno anterior para saber paciente
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

    # Formatear horas si vienen como objetos time/date
    clean_updates = dict(updates)
    if "fecha" in clean_updates and not isinstance(clean_updates["fecha"], str):
        clean_updates["fecha"] = clean_updates["fecha"].isoformat()
    if "hora_inicio" in clean_updates and not isinstance(clean_updates["hora_inicio"], str):
        clean_updates["hora_inicio"] = clean_updates["hora_inicio"].strftime("%H:%M:%S")
    if "hora_fin" in clean_updates and not isinstance(clean_updates["hora_fin"], str):
        clean_updates["hora_fin"] = clean_updates["hora_fin"].strftime("%H:%M:%S")

    # Si se modifica horario, validar overlap
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
        except Exception as e:
            print(f"Supabase update_turno error: {e}")

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
            if paciente_id:
                _sync_sesiones_local(paciente_id)
            return True, "Turno eliminado exitosamente."
        except Exception as e:
            print(f"Supabase delete_turno error: {e}")

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
    """Calcula y descuenta sesiones_realizadas para el paciente según turnos 'Asistió'."""
    if not paciente_id:
        return
    client = init_supabase_client()
    if client:
        try:
            # Contar asistencias en Supabase
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
            print(f"Supabase create_evolucion error: {e}")

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
# OPERACIONES: STORAGE Y ARCHIVOS ADJUNTOS
# ==============================================================================

def upload_paciente_archivo(
    paciente_id: str,
    file_bytes: bytes,
    filename: str,
    tipo_documento: str = "Orden Médica"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Sube una imagen o documento al bucket de Supabase Storage y registra su metadata."""
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
            # Subir al bucket
            client.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": f"image/{file_ext}"}
            )
            # Registrar en tabla
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
                return True, "Archivo subido exitosamente a Supabase Storage.", res.data[0]
        except Exception as e:
            print(f"Supabase Storage Upload Error: {e}")

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
        "file_bytes": file_bytes, # Guardado en memoria local
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
    """Elimina el archivo de Supabase Storage y de la base de datos."""
    client = init_supabase_client()
    _, _, bucket_name = get_supabase_credentials()

    if client:
        try:
            if storage_path:
                client.storage.from_(bucket_name).remove([storage_path])
            client.table("archivos_pacientes").delete().eq("id", str(archivo_id)).execute()
            return True, "Archivo eliminado correctamente."
        except Exception as e:
            print(f"Supabase delete archivo error: {e}")

    store = _get_local_store()
    store["archivos_pacientes"] = [a for a in store["archivos_pacientes"] if str(a.get("id")) != str(archivo_id)]
    return True, "Archivo eliminado correctamente."
