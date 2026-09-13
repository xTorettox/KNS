"""
KNS - Sistema de Gestión de Consultorio Kinesiológico
Punto de entrada principal de la aplicación Streamlit.
"""
import streamlit as st
from datetime import date

# 1. Configuración de página de Streamlit (debe ser la primera llamada de Streamlit)
st.set_page_config(
    page_title="KNS - Consultorio Kinesiológico",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Importaciones de módulos y vistas
from utils.ui import inject_custom_css, render_daily_quote_box
from utils.quotes import get_daily_quote
from views.agenda import render_agenda_view
from views.pacientes import render_pacientes_view
from views.historial import render_historial_view
from views.configuracion import render_configuracion_view

def main():
    # Inyectar estilos CSS visuales personalizados
    inject_custom_css()

    # ==============================================================================
    # SIDEBAR: NAVEGACIÓN, INFORMACIÓN PROFESIONAL Y EASTER EGG DIARIO
    # ==============================================================================
    with st.sidebar:
        # Encabezado del Consultorio
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0 0.5rem 0;">
                <div style="font-size: 2.2rem; margin-bottom: -5px;">🩺</div>
                <h2 style="margin: 0; color: #38bdf8; font-weight: 800; letter-spacing: -0.5px;">KNS</h2>
                <p style="margin: 0; font-size: 0.8rem; color: #94a3b8; font-weight: 600;">CONSULTORIO KINESIOLÓGICO</p>
            </div>
            <hr style="margin: 0.8rem 0; border-color: rgba(255,255,255,0.08);"/>
            """,
            unsafe_allow_html=True
        )

        # Menú de Navegación
        st.markdown("<p style='font-size: 0.75rem; font-weight: 700; color: #64748b; letter-spacing: 0.5px; margin-bottom: 6px;'>MENÚ PRINCIPAL</p>", unsafe_allow_html=True)
        
        menu_options = [
            "📅 Agenda de Turnos",
            "👥 Gestión de Pacientes",
            "🩺 Historial Clínico",
            "⚙️ Configuración & Sistema"
        ]

        if "nav_selection" not in st.session_state:
            st.session_state.nav_selection = menu_options[0]

        selected_page = st.radio(
            "Navegación",
            options=menu_options,
            label_visibility="collapsed",
            index=menu_options.index(st.session_state.nav_selection) if st.session_state.nav_selection in menu_options else 0
        )
        st.session_state.nav_selection = selected_page

        st.markdown("<hr style='margin: 1.2rem 0 0.8rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

        # Resumen rápido de atención
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

        # EASTER EGG: Frase del día de actores/actrices de los 80s/90s
        daily_quote = get_daily_quote(date.today())
        render_daily_quote_box(daily_quote)

        # Footer sidebar
        st.markdown(
            """
            <div style="text-align: center; margin-top: 1.5rem; font-size: 0.7rem; color: #475569;">
                KNS Management System v1.0<br/>
                Desplegable en Streamlit Cloud
            </div>
            """,
            unsafe_allow_html=True
        )

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
