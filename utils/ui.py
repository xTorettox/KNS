"""
Módulo de componentes visuales, estilos CSS modernos e interfaz de usuario en Streamlit.
Provee una estética cuidada, profesional y agradable con badges, cards e indicadores.
"""
import streamlit as st
from typing import Optional, Dict, Any

def inject_custom_css():
    """Inyecta estilos CSS globales para mejorar la apariencia de Streamlit."""
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Ocultar barra superior por defecto si es necesario */
    #MainMenu {visibility: visible;}
    footer {visibility: hidden;}

    /* Contenedor principal con espaciado óptimo */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Cards personalizadas con glassmorphism sutil */
    .kns-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .kns-card:hover {
        border-color: rgba(2, 132, 199, 0.4);
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    .kpi-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }

    .kpi-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1.2;
    }

    .kpi-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    /* Badges de Estado */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }

    .badge-asistio {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .badge-pendiente {
        background-color: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .badge-cancelado {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .badge-reprogramado {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.3);
    }

    .badge-ausente {
        background-color: rgba(148, 163, 184, 0.15);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }

    /* Caja de Frase Diaria (Easter Egg) con estilo Retro / Ochentoso */
    .quote-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 50%, #1e293b 100%);
        border: 1px solid #c084fc;
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
        box-shadow: 0 0 15px rgba(192, 132, 252, 0.2);
        position: relative;
    }

    .quote-text {
        font-size: 0.92rem;
        font-style: italic;
        color: #f3e8ff;
        font-weight: 600;
        line-height: 1.4;
        margin-bottom: 0.5rem;
    }

    .quote-author {
        font-size: 0.78rem;
        color: #c084fc;
        font-weight: 700;
        text-align: right;
    }

    .quote-tag {
        display: inline-block;
        font-size: 0.65rem;
        background-color: rgba(216, 180, 254, 0.2);
        color: #e9d5ff;
        padding: 2px 6px;
        border-radius: 4px;
        margin-top: 4px;
    }

    /* Botón de WhatsApp estilizado */
    .btn-wa {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #25D366;
        color: #ffffff !important;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }

    .btn-wa:hover {
        background-color: #1eb857;
        transform: translateY(-1px);
        text-decoration: none;
    }

    /* Botón de Google Calendar estilizado */
    .btn-gcal {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #1a73e8;
        color: #ffffff !important;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        transition: background-color 0.2s ease, transform 0.1s ease;
        border: 1px solid rgba(255,255,255,0.15);
    }

    .btn-gcal:hover {
        background-color: #1557b0;
        transform: translateY(-1px);
        text-decoration: none;
    }

    /* Contenedor del calendario mensual */
    .cal-grid-header {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 6px;
        text-align: center;
        font-weight: 700;
        font-size: 0.82rem;
        color: #94a3b8;
        margin-bottom: 6px;
    }

    .cal-day-cell {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 8px 4px;
        text-align: center;
        min-height: 68px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        transition: all 0.2s ease;
    }

    .cal-day-cell.today {
        border: 2px solid #38bdf8;
        background: rgba(56, 189, 248, 0.08);
    }

    .cal-day-cell.selected {
        border: 2px solid #4ade80;
        background: rgba(74, 222, 128, 0.1);
    }

    .cal-day-num {
        font-size: 0.95rem;
        font-weight: 700;
        color: #f8fafc;
    }

    .cal-day-badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 5px;
        border-radius: 4px;
        margin-top: 2px;
        display: inline-block;
        white-space: nowrap;
    }

    /* Contenedor y tarjetas de la Grilla Semanal */
    .week-grid-container {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        margin-bottom: 12px;
    }

    .week-day-card {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }

    .week-day-card:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }

    .week-day-card.today {
        border: 2px solid #38bdf8;
        background: rgba(56, 189, 248, 0.1);
    }

    .week-day-card.selected {
        border: 2px solid #4ade80;
        background: rgba(74, 222, 128, 0.12);
    }

    /* Mobile specific tweaks */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
            padding-bottom: 2rem !important;
        }
        .kpi-card {
            padding: 0.85rem !important;
            margin-bottom: 0.4rem !important;
        }
        .kpi-value {
            font-size: 1.45rem !important;
        }
        .cal-day-cell {
            min-height: 52px !important;
            padding: 4px 1px !important;
        }
        .cal-day-num {
            font-size: 0.82rem !important;
        }
        .cal-day-badge {
            font-size: 0.62rem !important;
            padding: 1px 2px !important;
        }
        .week-grid-container {
            grid-template-columns: repeat(4, 1fr) !important;
        }
    }
    </style>

    <script>
    // Prevenir salida involuntaria de la app al presionar el botón "Atrás" en móviles
    (function() {
        if (window.history && window.history.pushState) {
            if (!window.__kns_nav_initialized) {
                window.__kns_nav_initialized = true;
                window.history.pushState({ kns_state: "active" }, document.title, window.location.href);
                window.addEventListener("popstate", function(e) {
                    window.history.pushState({ kns_state: "active" }, document.title, window.location.href);
                });
            }
        }
    })();
    </script>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def render_header(title: str, subtitle: Optional[str] = None, icon: str = "🩺"):
    """Renderiza un encabezado limpio y moderno para cada vista."""
    sub_html = f"<p style='color: #94a3b8; margin: 0; font-size: 0.95rem;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="margin: 0; color: #f8fafc; font-weight: 800; display: flex; align-items: center; gap: 0.5rem;">
                <span>{icon}</span> <span>{title}</span>
            </h2>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_kpi_card(title: str, value: Any, subtitle: Optional[str] = None, color: str = "#38bdf8"):
    """Renderiza una tarjeta de indicador clave (KPI)."""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value" style="color: {color};">{value}</div>
            {f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_status_badge(estado: str) -> str:
    """Devuelve el fragmento HTML del badge de estado correspondiente."""
    est = str(estado).lower().strip()
    if "asisti" in est:
        return '<span class="badge badge-asistio">✓ Asistió</span>'
    elif "cancel" in est:
        return '<span class="badge badge-cancelado">✕ Cancelado</span>'
    elif "reprog" in est:
        return '<span class="badge badge-reprogramado">⟳ Reprogramado</span>'
    elif "ausen" in est:
        return '<span class="badge badge-ausente">∅ Ausente</span>'
    else:
        return '<span class="badge badge-pendiente">⏳ Pendiente</span>'

def render_session_progress(sesiones_realizadas: int, sesiones_totales: int) -> str:
    """Devuelve un widget visual en HTML del progreso de sesiones autorizadas."""
    totales = max(1, sesiones_totales)
    realizadas = min(sesiones_realizadas, totales)
    porcentaje = min(100, int((realizadas / totales) * 100))
    restantes = max(0, totales - realizadas)
    
    # Color según avance
    if porcentaje >= 100:
        bar_color = "#ef4444" # Agotado / Alerta
        status_txt = "¡Sesiones Completadas! Solicitar nueva orden."
    elif porcentaje >= 80:
        bar_color = "#f59e0b" # Por finalizar
        status_txt = f"{restantes} restante(s) - Próximo a finalizar"
    else:
        bar_color = "#10b981" # Normal
        status_txt = f"{restantes} restante(s) disponibles"

    return f"""
    <div style="margin: 0.4rem 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600; color: #cbd5e1;">
            <span>Sesiones: {realizadas} / {totales} ({porcentaje}%)</span>
            <span style="color: {bar_color};">{status_txt}</span>
        </div>
        <div class="session-bar-container">
            <div class="session-bar-fill" style="width: {porcentaje}%; background-color: {bar_color};"></div>
        </div>
    </div>
    """

def render_daily_quote_box(quote_data: Dict[str, Any]):
    """Renderiza el Easter Egg diario con las citas de los 80s/90s en el Sidebar."""
    frase = quote_data.get("frase", "")
    autor = quote_data.get("autor", "Anónimo")
    obra = quote_data.get("obra", "")
    año = quote_data.get("año", "")
    categoria = quote_data.get("categoria", "Cultura Pop")
    
    extra = f" ({obra}, {año})" if obra and año else f" ({obra})" if obra else ""
    
    st.markdown(
        f"""
        <div class="quote-box">
            <div style="font-size: 0.75rem; font-weight: 800; color: #e9d5ff; letter-spacing: 0.5px; margin-bottom: 4px; display: flex; justify-content: space-between;">
                <span>📼 FRASE DEL DÍA (80s/90s)</span>
                <span>✨</span>
            </div>
            <div class="quote-text">"{frase}"</div>
            <div class="quote-author">— {autor}{extra}</div>
            <div class="quote-tag">{categoria}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_google_calendar_button(gcal_url: str, label: str = "📅 Google Calendar") -> str:
    """Devuelve el fragmento HTML estilizado para el botón de Google Calendar."""
    return f'<a href="{gcal_url}" target="_blank" class="btn-gcal" title="Agregar a Google Calendar">{label}</a>'

