"""
KNS - Sistema de Gestión en Kinesiología
Punto de entrada principal de la aplicación Streamlit con autenticación, roles y personalización de marca.
"""
import streamlit as st
from datetime import date

# 1. Configuración de página de Streamlit
st.set_page_config(
    page_title="KNS - Kinesiología",
    page_icon="🩺",
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

def main():
    # Inyectar estilos visuales CSS
    inject_custom_css()

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
        clinic_name = app_config.get("clinic_name", "KNS")
        subtitle = app_config.get("subtitle", "KINESIOLOGÍA")

        if custom_logo_bytes:
            st.image(custom_logo_bytes, width=100)
            icon_html = ""
        else:
            icon_html = f"<div style='font-size: 2.2rem; margin-bottom: -5px;'>{logo_icon}</div>"

        st_html(
            f"""
            <div style='text-align: center; padding: 0.5rem 0;'>
                {icon_html}
                <h2 style="margin: 0; color: #38bdf8; font-weight: 800; letter-spacing: -0.5px;">{clinic_name}</h2>
                <p style="margin: 0; font-size: 0.8rem; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">{subtitle}</p>
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
