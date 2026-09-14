"""
Módulo de Autenticación, Control de Roles y Gestión de Usuarios (ABM).
Roles disponibles:
- 'admin': Acceso total, incluyendo Configuración, Sistema y ABM de Usuarios.
- 'kinesio': Acceso a Agenda, Pacientes e Historial Clínico (sin acceso a Configuración).
"""
import hashlib
import uuid
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# ==============================================================================
# SEGURIDAD Y HASHING
# ==============================================================================

SALT = "kns_kinesiologia_salt_2026"

def hash_password(password: str) -> str:
    """Genera hash SHA-256 con salt para almacenamiento seguro de contraseñas."""
    salted = f"{SALT}_{password}_{SALT}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con el hash guardado."""
    return hash_password(plain_password) == hashed_password

# ==============================================================================
# USUARIOS INICIALES POR DEFECTO
# ==============================================================================
DEFAULT_USERS = [
    {
        "id": "u1111111-1111-1111-1111-111111111111",
        "username": "fcendra",
        "password_hash": hash_password("C4n1ch3r1426"),
        "nombre": "Federico Cendra",
        "rol": "admin", # Administrador total
        "activo": True,
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "u2222222-2222-2222-2222-222222222222",
        "username": "anita",
        "password_hash": hash_password("bella2026"),
        "nombre": "Anita",
        "rol": "kinesio", # Acceso asistencial sin configuración
        "activo": True,
        "created_at": datetime.now().isoformat()
    }
]

# ==============================================================================
# OPERACIONES DE USUARIOS (SUPABASE / LOCAL)
# ==============================================================================

def get_usuarios() -> List[Dict[str, Any]]:
    """Obtiene la lista de usuarios del sistema desde Supabase o fallback local."""
    from utils.supabase_client import init_supabase_client
    client = init_supabase_client()
    if client:
        try:
            res = client.table("usuarios").select("id, username, password_hash, nombre, rol, activo, created_at").order("username").execute()
            if res.data and len(res.data) > 0:
                return res.data
        except Exception:
            pass

    if "local_usuarios" not in st.session_state:
        st.session_state.local_usuarios = [dict(u) for u in DEFAULT_USERS]
    return st.session_state.local_usuarios

def get_usuario_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Busca un usuario por su nombre de usuario."""
    usuarios = get_usuarios()
    u_lower = username.strip().lower()
    for u in usuarios:
        if str(u.get("username", "")).strip().lower() == u_lower:
            return u
    return None

def create_usuario(username: str, password: str, nombre: str, rol: str = "kinesio") -> Tuple[bool, str]:
    """Crea un nuevo usuario en el sistema."""
    if not username or not password or not nombre:
        return False, "Todos los campos son obligatorios."
    
    u_clean = username.strip().lower()
    if get_usuario_by_username(u_clean):
        return False, f"El nombre de usuario '{u_clean}' ya está en uso."

    new_user = {
        "id": str(uuid.uuid4()),
        "username": u_clean,
        "password_hash": hash_password(password),
        "nombre": nombre.strip(),
        "rol": rol if rol in ("admin", "kinesio") else "kinesio",
        "activo": True,
        "created_at": datetime.now().isoformat()
    }

    from utils.supabase_client import init_supabase_client
    client = init_supabase_client()
    if client:
        try:
            res = client.table("usuarios").insert(new_user).execute()
            if res.data:
                return True, "Usuario creado exitosamente."
        except Exception as e:
            print(f"Error creando usuario en Supabase: {e}")

    # Fallback local
    if "local_usuarios" not in st.session_state:
        st.session_state.local_usuarios = [dict(u) for u in DEFAULT_USERS]
    st.session_state.local_usuarios.append(new_user)
    return True, "Usuario creado exitosamente."

def update_usuario(user_id: str, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza datos de un usuario (nombre, rol, contraseña, estado)."""
    clean_updates = dict(updates)
    if "password" in clean_updates and clean_updates["password"]:
        clean_updates["password_hash"] = hash_password(clean_updates.pop("password"))
    elif "password" in clean_updates:
        del clean_updates["password"]

    from utils.supabase_client import init_supabase_client
    client = init_supabase_client()
    if client:
        try:
            res = client.table("usuarios").update(clean_updates).eq("id", str(user_id)).execute()
            if res.data:
                return True, "Usuario actualizado correctamente."
        except Exception as e:
            print(f"Error actualizando usuario en Supabase: {e}")

    # Fallback local
    usuarios = get_usuarios()
    for u in usuarios:
        if str(u.get("id")) == str(user_id):
            u.update(clean_updates)
            return True, "Usuario actualizado correctamente."
    return False, "Usuario no encontrado."

def delete_usuario(user_id: str) -> Tuple[bool, str]:
    """Elimina un usuario del sistema (no permite eliminar al último admin)."""
    usuarios = get_usuarios()
    admins = [u for u in usuarios if u.get("rol") == "admin" and str(u.get("id")) != str(user_id)]
    if not admins:
        return False, "No es posible eliminar al único administrador del sistema."

    from utils.supabase_client import init_supabase_client
    client = init_supabase_client()
    if client:
        try:
            client.table("usuarios").delete().eq("id", str(user_id)).execute()
            return True, "Usuario eliminado correctamente."
        except Exception as e:
            print(f"Error eliminando usuario en Supabase: {e}")

    # Fallback local
    if "local_usuarios" in st.session_state:
        st.session_state.local_usuarios = [u for u in st.session_state.local_usuarios if str(u.get("id")) != str(user_id)]
    return True, "Usuario eliminado correctamente."

# ==============================================================================
# GENERACIÓN Y VALIDACIÓN DE TOKENS DE SESIÓN PERSISTENTE
# ==============================================================================

import hmac
import base64

def generate_session_token(user: Dict[str, Any]) -> str:
    """Genera un token de sesión seguro y firmado para persistencia en móviles."""
    u_id = str(user.get("id", ""))
    u_name = str(user.get("username", ""))
    u_pass_hash = str(user.get("password_hash", ""))
    
    # Firma criptográfica HMAC con la clave SALT
    raw_sig_data = f"{u_id}:{u_name}:{u_pass_hash}".encode("utf-8")
    sig = hmac.new(SALT.encode("utf-8"), raw_sig_data, hashlib.sha256).hexdigest()
    
    payload = f"{u_id}|{u_name}|{sig}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")

def validate_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Valida el token de sesión y retorna el usuario activo si es válido."""
    if not token or not isinstance(token, str):
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        parts = decoded.split("|")
        if len(parts) != 3:
            return None
        u_id, u_name, token_sig = parts
        
        user = get_usuario_by_username(u_name)
        if not user or not user.get("activo", True):
            return None
            
        u_pass_hash = str(user.get("password_hash", ""))
        expected_sig = hmac.new(SALT.encode("utf-8"), f"{u_id}:{u_name}:{u_pass_hash}".encode("utf-8"), hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(token_sig, expected_sig):
            return user
    except Exception:
        pass
    return None

# ==============================================================================
# CONTROL DE SESIÓN Y VISTA DE LOGIN
# ==============================================================================

def is_authenticated() -> bool:
    """
    Verifica si el usuario actual ha iniciado sesión.
    Si se perdió el estado en memoria (ej. bloqueo de celular o recarga),
    restaura la sesión automáticamente usando el token persistente en la URL.
    """
    if st.session_state.get("authenticated", False) and st.session_state.get("current_user"):
        return True
        
    # Verificar token persistente en st.query_params
    token = st.query_params.get("session_token")
    if token:
        user = validate_session_token(token)
        if user:
            st.session_state.authenticated = True
            st.session_state.current_user = user
            return True
        else:
            # Token inválido o expirado, remover
            try:
                del st.query_params["session_token"]
            except Exception:
                pass
                
    return False

def get_current_user() -> Optional[Dict[str, Any]]:
    """Devuelve los datos del usuario en sesión activa."""
    return st.session_state.get("current_user", None)

def is_admin() -> bool:
    """Verifica si el usuario actual tiene rol de Administrador."""
    user = get_current_user()
    return bool(user and user.get("rol") == "admin")

def logout():
    """Cierra la sesión actual del usuario y elimina el token de persistencia."""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    if "session_token" in st.query_params:
        try:
            del st.query_params["session_token"]
        except Exception:
            pass
    st.rerun()

def render_login_view():
    """Renderiza una pantalla de inicio de sesión moderna y protegida."""
    st.markdown(
        """
        <div style="max-width: 440px; margin: 4rem auto 1.5rem auto; text-align: center;">
            <div style="font-size: 3.5rem; margin-bottom: 0.2rem;">🩺</div>
            <h1 style="color: #38bdf8; font-weight: 800; font-size: 2.2rem; margin: 0; letter-spacing: -0.5px;">KNS</h1>
            <p style="color: #94a3b8; font-size: 0.95rem; font-weight: 600; margin-top: 2px;">SISTEMA DE GESTIÓN EN KINESIOLOGÍA</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_l1, col_center, col_l2 = st.columns([1, 1.4, 1])

    with col_center:
        with st.container():
            st.markdown(
                """
                <div style="background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
                    <h3 style="color: #f8fafc; font-size: 1.25rem; font-weight: 700; margin-bottom: 4px; text-align: center;">Iniciar Sesión</h3>
                    <p style="color: #64748b; font-size: 0.85rem; text-align: center; margin-bottom: 20px;">Ingresa tus credenciales autorizadas</p>
                """,
                unsafe_allow_html=True
            )

            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input("Usuario", placeholder="Tu nombre de usuario", key="login_user")
                password_input = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_pass")
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                submit_btn = st.form_submit_button("Ingresar al Sistema", type="primary", use_container_width=True)

                if submit_btn:
                    if not username_input or not password_input:
                        st.error("Por favor ingresa usuario y contraseña.")
                    else:
                        user = get_usuario_by_username(username_input)
                        if user and user.get("activo", True) and verify_password(password_input, user.get("password_hash", "")):
                            st.session_state.authenticated = True
                            st.session_state.current_user = user
                            # Generar token persistente para no desloguearse al bloquear teléfono
                            token = generate_session_token(user)
                            st.query_params["session_token"] = token
                            st.toast(f"¡Bienvenido/a, {user.get('nombre')}!", icon="👋")
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                """
                <div style="text-align: center; margin-top: 1.5rem; color: #475569; font-size: 0.75rem;">
                    Acceso protegido para profesionales y administración • KNS v1.0
                </div>
                """,
                unsafe_allow_html=True
            )

