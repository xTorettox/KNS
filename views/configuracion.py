"""
Vista de Configuración, Personalización de Logo, Gestión de Usuarios (ABM) y Sistema.
Acceso exclusivo para el rol de Administrador.
"""
import streamlit as st
import os
import json
from PIL import Image
import io

from utils.supabase_client import (
    get_supabase_credentials,
    init_supabase_client,
    get_app_config,
    update_app_config
)
from utils.auth import (
    is_admin,
    get_usuarios,
    create_usuario,
    update_usuario,
    delete_usuario,
    get_current_user
)
from utils.quotes import load_all_quotes, get_random_quote
from utils.ui import render_header, render_kpi_card, render_daily_quote_box, st_html

def render_configuracion_view():
    """Renderiza la vista de configuración y administración."""
    # Control de acceso por rol
    if not is_admin():
        st.error("⛔ Acceso Restringido: Esta sección requiere privilegios de Administrador.")
        st.info("Inicia sesión con una cuenta de Administrador para acceder a la configuración del sistema.")
        return

    render_header("Configuración y Sistema", "Personalización del logo, ABM de usuarios, estado del sistema y Easter Egg", icon="⚙️")

    tab_logo, tab_usuarios, tab_diag, tab_sql, tab_quotes = st.tabs([
        "🎨 Logo y Marca",
        "👥 ABM de Usuarios",
        "🔌 Estado del Sistema",
        "📜 Script de Base de Datos",
        "📼 Frases de Culto (80s/90s)"
    ])

    # ==============================================================================
    # TAB 1: PERSONALIZACIÓN DE LOGO Y MARCA
    # ==============================================================================
    with tab_logo:
        st.markdown("#### Personalización de la Identidad Visual")
        st.caption("Modifica el logo, ícono o nombre que se muestra en la barra lateral y encabezados de la aplicación.")

        current_config = get_app_config()

        col_logo_prev, col_logo_form = st.columns([1.2, 2])

        with col_logo_prev:
            st.markdown("##### Vista Previa Actual")
            custom_bytes = current_config.get("custom_logo_bytes")
            if custom_bytes:
                st.image(custom_bytes, width=120)
                icon_markup = ""
            else:
                icon_markup = f"<div style='font-size: 3rem; margin-bottom: 4px;'>{current_config.get('logo_icon', '🩺')}</div>"

            st_html(
                f"""
                <div style="background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; text-align: center;">
                    {icon_markup}
                    <h3 style="margin: 0; color: #38bdf8; font-weight: 800;">{current_config.get('clinic_name', 'KNS')}</h3>
                    <p style="margin: 0; font-size: 0.8rem; color: #94a3b8; font-weight: 600;">{current_config.get('subtitle', 'KINESIOLOGÍA')}</p>
                </div>
                """
            )

        with col_logo_form:
            st.markdown("##### Ajustar Parámetros")
            with st.form("form_brand_config"):
                c_n1, c_n2 = st.columns([1.5, 2])
                with c_n1:
                    new_clinic_name = st.text_input("Nombre de la Marca / Sigla", value=current_config.get("clinic_name", "KNS"))
                with c_n2:
                    new_subtitle = st.text_input("Subtítulo", value=current_config.get("subtitle", "KINESIOLOGÍA"))

                st.markdown("##### Seleccionar Ícono o Subir Logo Propio")
                icon_options = ["🩺", "🦴", "🏃", "⚡", "🖐️", "🧘", "🏥", "💪", "🩹", "🧬"]
                curr_icon = current_config.get("logo_icon", "🩺")
                idx_icon = icon_options.index(curr_icon) if curr_icon in icon_options else 0
                new_icon = st.selectbox("Ícono Predeterminado", icon_options, index=idx_icon)

                uploaded_logo = st.file_uploader("Subir imagen de Logo personalizada (PNG, JPG)", type=["png", "jpg", "jpeg", "webp"])
                
                remove_custom_logo = False
                if current_config.get("custom_logo_bytes") is not None:
                    remove_custom_logo = st.checkbox("Eliminar imagen personalizada y volver al ícono estándar")

                btn_save_brand = st.form_submit_button("Guardar Identidad Visual", type="primary")
                if btn_save_brand:
                    updates = {
                        "clinic_name": new_clinic_name.strip() or "KNS",
                        "subtitle": new_subtitle.strip() or "KINESIOLOGÍA",
                        "logo_icon": new_icon
                    }
                    if uploaded_logo is not None:
                        updates["custom_logo_bytes"] = uploaded_logo.getvalue()
                    elif remove_custom_logo:
                        updates["custom_logo_bytes"] = None

                    ok_cfg, msg_cfg = update_app_config(updates)
                    if ok_cfg:
                        st.success("¡Identidad visual actualizada con éxito!")
                        st.rerun()

    # ==============================================================================
    # TAB 2: ABM DE USUARIOS (CREAR, EDITAR, ELIMINAR Y ROLES)
    # ==============================================================================
    with tab_usuarios:
        st.markdown("#### Gestión de Usuarios del Sistema (ABM)")
        st.caption("Administra los accesos para kinesiólogos y personal del consultorio.")

        # Botón para crear nuevo usuario
        with st.expander("➕ Registrar Nuevo Usuario", expanded=False):
            with st.form("form_nuevo_usuario"):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    new_u_username = st.text_input("Usuario (Login) *", placeholder="Ej: jaimito")
                    new_u_nombre = st.text_input("Nombre y Apellido *", placeholder="Ej: Dr. Jaimito Lopez")
                with col_u2:
                    new_u_password = st.text_input("Contraseña *", type="password", placeholder="••••••••")
                    new_u_rol = st.selectbox("Rol del Usuario", [("kinesio", "Kinesiólogo/a (Asistencial)"), ("admin", "Administrador (Acceso Total)")], format_func=lambda x: x[1])

                btn_crear_u = st.form_submit_button("Crear Usuario", type="primary")
                if btn_crear_u:
                    ok_u, msg_u = create_usuario(
                        username=new_u_username,
                        password=new_u_password,
                        nombre=new_u_nombre,
                        rol=new_u_rol[0]
                    )
                    if ok_u:
                        st.success(msg_u)
                        st.rerun()
                    else:
                        st.error(msg_u)

        # Listado de usuarios existentes
        usuarios_list = get_usuarios()
        st.markdown(f"##### Usuarios Registrados ({len(usuarios_list)})")

        for u in usuarios_list:
            u_id = str(u.get("id"))
            u_name = u.get("username", "")
            u_nom = u.get("nombre", "")
            u_rol = u.get("rol", "kinesio")
            u_act = u.get("activo", True)

            rol_badge = '<span style="background: rgba(2,132,199,0.2); color: #38bdf8; font-weight: bold; font-size: 0.78rem; padding: 2px 8px; border-radius: 9999px;">ADMINISTRADOR</span>' if u_rol == "admin" else '<span style="background: rgba(34,197,94,0.2); color: #4ade80; font-weight: bold; font-size: 0.78rem; padding: 2px 8px; border-radius: 9999px;">KINESIÓLOGO/A</span>'

            with st.container():
                st_html(
                    f"""
                    <div class="kns-card" style="padding: 12px 16px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                            <div>
                                <b style="color: #f8fafc; font-size: 1rem;">👤 {u_nom}</b> 
                                <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 6px;">(@{u_name})</span>
                            </div>
                            <div>
                                {rol_badge}
                            </div>
                        </div>
                    </div>
                    """
                )

                # Popover de edición de usuario
                col_u_act1, col_u_act2 = st.columns([4, 1])
                with col_u_act2:
                    with st.popover(f"⚙️ Modificar @{u_name}"):
                        st.markdown(f"###### Modificar Usuario **{u_name}**")
                        with st.form(f"form_edit_user_{u_id}"):
                            edit_nom = st.text_input("Nombre y Apellido", value=u_nom)
                            edit_pass = st.text_input("Nueva Contraseña (dejar vacío para no cambiar)", type="password")
                            
                            roles_op = ["kinesio", "admin"]
                            idx_r = roles_op.index(u_rol) if u_rol in roles_op else 0
                            edit_rol = st.selectbox("Rol", roles_op, index=idx_r, format_func=lambda x: "Administrador" if x == "admin" else "Kinesiólogo/a")
                            edit_act = st.checkbox("Usuario Activo", value=u_act)

                            btn_save_u = st.form_submit_button("Guardar Cambios", type="primary")
                            if btn_save_u:
                                upd = {
                                    "nombre": edit_nom.strip(),
                                    "rol": edit_rol,
                                    "activo": edit_act
                                }
                                if edit_pass.strip():
                                    upd["password"] = edit_pass.strip()
                                ok_up, msg_up = update_usuario(u_id, upd)
                                if ok_up:
                                    st.success("Usuario actualizado.")
                                    st.rerun()
                                else:
                                    st.error(msg_up)

                        st.markdown("---")
                        if st.button("🗑 Eliminar Usuario", key=f"del_u_btn_{u_id}", type="secondary"):
                            ok_del, msg_del = delete_usuario(u_id)
                            if ok_del:
                                st.warning("Usuario eliminado.")
                                st.rerun()
                            else:
                                st.error(msg_del)

    # ==============================================================================
    # TAB 3: ESTADO DEL SISTEMA Y CONEXIÓN
    # ==============================================================================
    with tab_diag:
        st.markdown("#### Estado de Conexión de la Base de Datos")
        url, key, bucket = get_supabase_credentials()

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.text_input("Servidor de Datos", value=url.split("//")[-1] if "//" in url else url, disabled=True)
            st.text_input("Repositorio de Archivos", value="Activo y Conectado", disabled=True)
        with col_c2:
            st.text_input("Llave de Acceso", value="Configurada y Protegida", disabled=True)
            st.caption("Credenciales protegidas en variables de entorno del servidor.")

        client = init_supabase_client()
        if client:
            st.success("✅ **Base de Datos y Almacenamiento sincronizados y respondiendo.**")
            try:
                test_res = client.table("pacientes").select("id", count="exact").limit(1).execute()
                st.info(f"📊 **Módulo de Pacientes activo:** {test_res.count if test_res.count is not None else 'OK'} registros sincronizados.")
            except Exception as e:
                st.warning(f"⚠️ Las tablas de base de datos aún no fueron creadas en el servidor. Ejecuta el script SQL en la pestaña contigua.")
        else:
            st.info("ℹ️ Sistema funcionando en almacenamiento local protegido.")

        st.markdown("---")
        st.markdown("##### Parámetros Operativos de Kinesiología")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            render_kpi_card("Horario de Atención", "08:00 a 15:00", "Jornada continua", color="#38bdf8")
        with col_p2:
            render_kpi_card("Capacidad Máxima", "2 Pacientes", "En simultáneo", color="#4ade80")
        with col_p3:
            render_kpi_card("Duraciones", "30 / 45 / 60 min", "Por sesión", color="#facc15")

    # ==============================================================================
    # TAB 4: SCRIPT DE BASE DE DATOS (SQL DDL)
    # ==============================================================================
    with tab_sql:
        st.markdown("#### Script de Estructura de Base de Datos")
        st.caption("Script DDL para inicializar o actualizar las tablas, usuarios, triggers y almacenamiento.")

        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "supabase_schema.sql")
        sql_content = ""
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
        
        st.code(sql_content, language="sql")

    # ==============================================================================
    # TAB 5: EXPLORADOR DE FRASES (EASTER EGG)
    # ==============================================================================
    with tab_quotes:
        st.markdown("#### 📼 100 Frases Icónicas y Bizarras de los 80s y 90s")
        st.caption("Colección de frases de culto (Francella, Darín, Los Simuladores, Olmedo, Schwarzenegger, Stallone, Willis y más).")

        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            filtro_frase = st.text_input("Buscar frase, actor o película", placeholder="Ej: Francella, Terminator, Simuladores...")
        with col_q2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🎲 Probar Frase Aleatoria"):
                rand_q = get_random_quote()
                st.session_state.sample_quote = rand_q

        if "sample_quote" in st.session_state:
            render_daily_quote_box(st.session_state.sample_quote)

        all_quotes = load_all_quotes()
        if filtro_frase:
            q_fil = filtro_frase.lower()
            all_quotes = [q for q in all_quotes if q_fil in q.get("frase","").lower() or q_fil in q.get("autor","").lower() or q_fil in q.get("obra","").lower()]

        st.markdown(f"**Total de frases disponibles:** {len(all_quotes)}")
        for q in all_quotes:
            st_html(
                f"""
                <div style="background: #1e293b; border-left: 3px solid #c084fc; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
                    <b style="color: #f3e8ff;">#{q.get('id')} "{q.get('frase')}"</b><br/>
                    <span style="font-size: 0.8rem; color: #cbd5e1;">— {q.get('autor')} ({q.get('obra')}, {q.get('año')})</span>
                    <span style="font-size: 0.75rem; background: rgba(192,132,252,0.2); color: #e9d5ff; padding: 2px 6px; border-radius: 4px; float: right;">{q.get('categoria')}</span>
                </div>
                """
            )
