import os
import streamlit as st
from datetime import date

# 1. Configuración de página de Streamlit
logo_path = "assets/kion_logo.png" if os.path.exists("assets/kion_logo.png") else "logo.png"
st.set_page_config(
    page_title="KION - Centro Terapéutico Integral",
    page_icon=logo_path if os.path.exists(logo_path) else "🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Importaciones de utilidades, autenticación y vistas
from utils.ui import inject_custom_css, render_daily_quote_box, st_html
from utils.quotes import get_daily_quote
from utils.auth import (
    is_authenticated,
    get_current_user,
    is_admin,
    logout,
    render_login_view
)
from utils.supabase_client import get_app_config
from views.agenda import render_agenda_view
from views.pacientes import render_pacientes_view
from views.historial import render_historial_view
from views.configuracion import render_configuracion_view
from views.registro_paciente import render_registro_paciente_view
from utils.registration import (
    get_unread_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read
)

def main():
    # Inyectar estilos visuales CSS
    inject_custom_css()

    # ==============================================================================
    # VERIFICACIÓN DE ENLACE PÚBLICO DE ALTA DE PACIENTE / REGISTRO
    # ==============================================================================
    public_token = st.query_params.get("token") or st.query_params.get("registro")
    if public_token:
        render_registro_paciente_view(public_token)
        return

    # ==============================================================================
    # VERIFICACIÓN DE AUTENTICACIÓN
    # ==============================================================================
    if not is_authenticated():
        render_login_view()
        return

    current_user = get_current_user() or {}
    user_name = current_user.get("nombre", "Usuario")
    user_role = current_user.get("rol", "kinesio")
    app_config = get_app_config()

    # ==============================================================================
    # SIDEBAR: LOGO DINÁMICO, PERFIL, NAVEGACIÓN Y EASTER EGG
    # ==============================================================================
    with st.sidebar:
        # LOGO Y MARCA DINÁMICOS
        custom_logo_bytes = app_config.get("custom_logo_bytes")
        logo_icon = app_config.get("logo_icon", "🩺")
        clinic_name = app_config.get("clinic_name", "KION")
        subtitle = app_config.get("subtitle", "Centro Terapéutico Integral")

        if custom_logo_bytes:
            st.image(custom_logo_bytes, use_container_width=True)
            icon_html = ""
        elif os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
            icon_html = ""
        else:
            icon_html = f"<div style='font-size: 2.2rem; margin-bottom: -5px;'>{logo_icon}</div>"

        st_html(
            f"""
            <div style='text-align: center; padding: 0.2rem 0;'>
                {icon_html}
                <h2 style="margin: 0; color: #38bdf8; font-weight: 800; letter-spacing: -0.5px; font-size: 1.3rem;">{clinic_name}</h2>
                <p style="margin: 0; font-size: 0.75rem; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">{subtitle}</p>
            </div>
            <hr style="margin: 0.8rem 0; border-color: rgba(255,255,255,0.08);"/>
            """
        )

        # INFORMACIÓN DEL USUARIO LOGUEADO
        rol_label = "Administrador" if is_admin() else "Kinesiólogo/a"
        rol_color = "#38bdf8" if is_admin() else "#4ade80"
        
        st_html(
            f"""
            <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #f8fafc;">👤 {user_name}</div>
                    <div style="font-size: 0.72rem; color: {rol_color}; font-weight: 600;">{rol_label}</div>
                </div>
            </div>
            """
        )

        # NOTIFICACIONES / AVISOS DE FICHAS Y PEDIDOS MÉDICOS COMPLETADOS
        unread_notifs = get_unread_notifications()
        if unread_notifs:
            count_n = len(unread_notifs)
            st_html(
                f"""
                <div style="background: linear-gradient(135deg, rgba(234, 88, 12, 0.15), rgba(249, 115, 22, 0.25)); border: 1px solid #f97316; border-radius: 8px; padding: 8px 10px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.82rem; font-weight: 800; color: #fdba74;">🔔 {count_n} {'Aviso de Alta' if count_n == 1 else 'Avisos de Altas'}</span>
                        <span style="background: #ea580c; color: white; border-radius: 999px; padding: 1px 6px; font-size: 0.7rem; font-weight: bold;">+{count_n}</span>
                    </div>
                </div>
                """
            )
            with st.expander(f"📥 Ver avisos pendientes ({count_n})", expanded=True):
                for n in unread_notifs[:5]:
                    n_id = n.get("id")
                    p_nom = n.get("paciente_nombre", "Paciente")
                    has_doc = n.get("tiene_pedido_medico", False)
                    doc_tag = " 📄 (Pedido médico)" if has_doc else ""
                    st.markdown(f"<div style='font-size: 0.78rem; color: #f8fafc; margin-bottom: 4px;'>• <b>{p_nom}</b> completó ficha{doc_tag}</div>", unsafe_allow_html=True)
                    c_n1, c_n2 = st.columns([1.2, 1])
                    with c_n1:
                        if st.button("👥 Ver", key=f"btn_notif_goto_{n_id}", use_container_width=True):
                            st.session_state.paciente_seleccionado_id = n.get("paciente_id")
                            st.session_state.nav_selection = "👥 Gestión de Pacientes"
                            st.query_params["page"] = "pacientes"
                            mark_notification_as_read(n_id)
                            st.rerun()
                    with c_n2:
                        if st.button("✓ Visto", key=f"btn_notif_ok_{n_id}", use_container_width=True):
                            mark_notification_as_read(n_id)
                            st.rerun()
                if count_n > 1:
                    if st.button("Marcar todos leídos", key="btn_notif_all_read", use_container_width=True):
                        mark_all_notifications_as_read()
                        st.rerun()

        # MENÚ DE NAVEGACIÓN SEGÚN ROL
        st.markdown("<p style='font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.5px; margin-bottom: 6px;'>MENÚ PRINCIPAL</p>", unsafe_allow_html=True)
        
        menu_options = [
            "📅 Agenda de Turnos",
            "👥 Gestión de Pacientes",
            "🩺 Historial Clínico"
        ]

        # Solo el Administrador tiene acceso a Configuración y Sistema
        if is_admin():
            menu_options.append("⚙️ Configuración & Sistema")

        # MAPEO DE PÁGINAS A PARÁMETROS URL
        page_map = {
            "agenda": "📅 Agenda de Turnos",
            "pacientes": "👥 Gestión de Pacientes",
            "historial": "🩺 Historial Clínico",
            "configuracion": "⚙️ Configuración & Sistema"
        }
        rev_page_map = {v: k for k, v in page_map.items()}

        url_page = st.query_params.get("page", "agenda")
        default_nav = page_map.get(url_page, menu_options[0])
        if default_nav not in menu_options:
            default_nav = menu_options[0]

        if "nav_selection" not in st.session_state or st.session_state.nav_selection not in menu_options:
            st.session_state.nav_selection = default_nav

        selected_page = st.radio(
            "Navegación",
            options=menu_options,
            label_visibility="collapsed",
            index=menu_options.index(st.session_state.nav_selection) if st.session_state.nav_selection in menu_options else 0
        )
        if selected_page != st.session_state.nav_selection:
            st.session_state.nav_selection = selected_page
            st.query_params["page"] = rev_page_map.get(selected_page, "agenda")
        elif "page" not in st.query_params:
            st.query_params["page"] = rev_page_map.get(selected_page, "agenda")

        st.markdown("<hr style='margin: 1rem 0 0.8rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

        # Resumen de atención
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.6); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); font-size: 0.8rem; color: #94a3b8;">
                <div style="color: #cbd5e1; font-weight: 700; margin-bottom: 4px;">🕒 Horario de Atención</div>
                <div>Lunes a Viernes: <b>08:00 - 15:00 hs</b></div>
                <div style="margin-top: 2px;">Capacidad: <b>Máx. 2 simultáneos</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # EASTER EGG: Frase del día de culto
        daily_quote = get_daily_quote(date.today())
        render_daily_quote_box(daily_quote)

        # BOTÓN CERRAR SESIÓN
        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
            logout()

    # ==============================================================================
    # ENRUTAMIENTO DE VISTAS
    # ==============================================================================
    if selected_page == "📅 Agenda de Turnos":
        render_agenda_view()
    elif selected_page == "👥 Gestión de Pacientes":
        render_pacientes_view()
    elif selected_page == "🩺 Historial Clínico":
        render_historial_view()
    elif selected_page == "⚙️ Configuración & Sistema":
        render_configuracion_view()

if __name__ == "__main__":
    main()
