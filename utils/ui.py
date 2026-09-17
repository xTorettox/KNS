"""
Módulo de componentes visuales, estilos CSS modernos e interfaz de usuario en Streamlit.
Provee una estética cuidada, profesional y agradable con badges, cards, grillas e indicadores.
"""
import streamlit as st
import textwrap
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
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Cards personalizadas con glassmorphism sutil */
    .kns-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 0.8rem;
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

    /* Barra de progreso de sesiones */
    .session-bar-container {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        height: 10px;
        width: 100%;
        overflow: hidden;
        margin-top: 6px;
    }

    .session-bar-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.3s ease;
    }

    /* ========================================================================= */
    /* CALENDARIO 7 COLUMNAS (TABLA PURA INQUEBRANTABLE EN MÓVILES) */
    /* ========================================================================= */
    .kns-cal-container {
        width: 100%;
        margin-bottom: 0.8rem;
    }

    .kns-month-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 8px;
    }

    .kns-month-title {
        font-size: 1.05rem;
        font-weight: 800;
        color: #38bdf8;
        text-align: center;
    }

    .kns-cal-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 4px;
        table-layout: fixed;
        margin-bottom: 8px;
    }

    .kns-cal-table th {
        text-align: center;
        font-weight: 800;
        font-size: 0.75rem;
        color: #94a3b8;
        padding: 3px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .kns-cal-table td {
        text-align: center;
        vertical-align: middle;
        padding: 0;
        width: 14.285%;
    }

    .kns-cal-cell {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 50px;
        border-radius: 8px;
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-decoration: none !important;
        color: #f8fafc !important;
        padding: 4px 1px;
        box-sizing: border-box;
        transition: transform 0.12s ease, border-color 0.12s ease, background 0.12s ease;
    }

    .kns-cal-cell:hover {
        border-color: #38bdf8;
        transform: scale(1.04);
        background: #24344d;
    }

    .kns-cal-cell.today {
        border: 2px solid #38bdf8 !important;
        background: rgba(56, 189, 248, 0.12) !important;
    }

    .kns-cal-cell.selected {
        background: #0284c7 !important;
        border: 2px solid #38bdf8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
    }

    .kns-cal-cell.empty {
        background: rgba(15, 23, 42, 0.2);
        border: 1px dashed rgba(255, 255, 255, 0.03);
        pointer-events: none;
        min-height: 50px;
    }

    .kns-day-num {
        font-weight: 800;
        font-size: 0.92rem;
        line-height: 1.1;
        color: #f8fafc;
    }

    .kns-day-badge {
        font-size: 0.65rem;
        font-weight: 700;
        padding: 1px 4px;
        border-radius: 4px;
        margin-top: 3px;
        display: inline-block;
        white-space: nowrap;
    }

    .kns-badge-zero {
        color: #64748b;
        background: transparent;
    }

    .kns-badge-turnos {
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.18);
    }

    .kns-badge-full {
        color: #facc15;
        background: rgba(250, 204, 21, 0.18);
    }

    /* Mobile specific tweaks */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            padding-bottom: 2rem !important;
        }
        .kpi-card {
            padding: 0.85rem !important;
            margin-bottom: 0.4rem !important;
        }
        .kpi-value {
            font-size: 1.45rem !important;
        }
        .kns-cal-table {
            border-spacing: 2px !important;
        }
        .kns-cal-cell {
            min-height: 44px !important;
            padding: 2px 0 !important;
            border-radius: 6px !important;
        }
        .kns-day-num {
            font-size: 0.82rem !important;
        }
        .kns-day-badge {
            font-size: 0.58rem !important;
            padding: 0 2px !important;
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
    st_html(custom_css)

def st_html(html_str: str):
    """Renderiza HTML en Streamlit asegurando que ninguna línea tenga indentación que active bloques de código de Markdown."""
    if not html_str:
        return
    clean_html = textwrap.dedent(html_str).strip()
    st.markdown(clean_html, unsafe_allow_html=True)

def render_header(title: str, subtitle: Optional[str] = None, icon: str = "🩺"):
    """Renderiza un encabezado limpio y moderno para cada vista."""
    sub_html = f"<p style='color: #94a3b8; margin: 0; font-size: 0.92rem;'>{subtitle}</p>" if subtitle else ""
    st_html(
        f"""
        <div style="margin-bottom: 1.2rem;">
            <h2 style="margin: 0; color: #f8fafc; font-weight: 800; display: flex; align-items: center; gap: 0.5rem; font-size: 1.6rem;">
                <span>{icon}</span> <span>{title}</span>
            </h2>
            {sub_html}
        </div>
        """
    )

def render_kpi_card(title: str, value: Any, subtitle: Optional[str] = None, color: str = "#38bdf8"):
    """Renderiza una tarjeta de indicador clave (KPI)."""
    st_html(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value" style="color: {color};">{value}</div>
            {f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
        """
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
        bar_color = "#ef4444"
        status_txt = "¡Sesiones Completadas! Solicitar nueva orden."
    elif porcentaje >= 80:
        bar_color = "#f59e0b"
        status_txt = f"{restantes} restante(s) - Próximo a finalizar"
    else:
        bar_color = "#10b981"
        status_txt = f"{restantes} restante(s) disponibles"

    return textwrap.dedent(f"""
    <div style="margin: 0.4rem 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 600; color: #cbd5e1;">
            <span>Sesiones: {realizadas} / {totales} ({porcentaje}%)</span>
            <span style="color: {bar_color};">{status_txt}</span>
        </div>
        <div class="session-bar-container">
            <div class="session-bar-fill" style="width: {porcentaje}%; background-color: {bar_color};"></div>
        </div>
    </div>
    """).strip()

def render_daily_quote_box(quote_data: Dict[str, Any]):
    """Renderiza el Easter Egg diario con las citas de los 80s/90s en el Sidebar."""
    frase = quote_data.get("frase", "")
    autor = quote_data.get("autor", "Anónimo")
    obra = quote_data.get("obra", "")
    año = quote_data.get("año", "")
    categoria = quote_data.get("categoria", "Cultura Pop")
    
    extra = f" ({obra}, {año})" if obra and año else f" ({obra})" if obra else ""
    
    st_html(
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
        """
    )

def render_google_calendar_button(gcal_url: str, label: str = "📅 Google Calendar") -> str:
    """Devuelve el fragmento HTML estilizado para el botón de Google Calendar."""
    return f'<a href="{gcal_url}" target="_blank" class="btn-gcal" title="Agregar a Google Calendar">{label}</a>'

