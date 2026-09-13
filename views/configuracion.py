"""
Vista de Configuración, Diagnóstico del Sistema y Base de Datos Supabase.
Permite verificar la conexión con Supabase, revisar el script SQL y explorar el Easter Egg de frases.
"""
import streamlit as st
import os
import json

from utils.supabase_client import (
    get_supabase_credentials,
    init_supabase_client
)
from utils.quotes import load_all_quotes, get_random_quote
from utils.ui import render_header, render_kpi_card, render_daily_quote_box

def render_configuracion_view():
    """Renderiza la vista de configuración y diagnósticos."""
    render_header("Configuración y Sistema", "Parámetros del consultorio, estado de Supabase y Easter Egg", icon="⚙️")

    tab_diag, tab_sql, tab_quotes = st.tabs(["🔌 Estado de Supabase", "📜 Esquema SQL (DDL)", "📼 Explorador de Frases (80s/90s)"])

    # ==============================================================================
    # TAB 1: DIAGNÓSTICO DE SUPABASE
    # ==============================================================================
    with tab_diag:
        st.markdown("#### Estado de Conexión con Supabase")
        url, key, bucket = get_supabase_credentials()

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.text_input("Supabase Project URL", value=url, disabled=True)
            st.text_input("Storage Bucket", value=bucket, disabled=True)
        with col_c2:
            st.text_input("Supabase Key (Anon / Service Role)", value=key[:10] + "..." + key[-6:] if key else "No configurada", disabled=True)
            st.caption("Configurable desde `.streamlit/secrets.toml` o en Streamlit Community Cloud.")

        # Probar conexión activa
        client = init_supabase_client()
        if client:
            st.success("✅ **Cliente de Supabase inicializado correctamente.**")
            
            # Test de consulta
            try:
                test_res = client.table("pacientes").select("id", count="exact").limit(1).execute()
                st.info(f"📊 **Tabla 'pacientes' activa y respondiendo.** Registros encontrados: {test_res.count if test_res.count is not None else 'OK'}")
            except Exception as e:
                st.warning(f"⚠️ Las tablas de Supabase aún no fueron creadas o requieren permisos. Ejecuta el script de la pestaña 'Esquema SQL' en tu panel de Supabase. (Detalle: {e})")
        else:
            st.warning("⚠️ Modo sin conexión a Supabase activa. La aplicación está funcionando con almacenamiento local de demostración.")

        st.markdown("---")
        st.markdown("##### Parámetros Operativos del Consultorio")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            render_kpi_card("Horario de Atención", "08:00 a 15:00", "Jornada continua", color="#38bdf8")
        with col_p2:
            render_kpi_card("Capacidad Máxima", "2 Pacientes", "En simultáneo", color="#4ade80")
        with col_p3:
            render_kpi_card("Duraciones", "30 / 45 / 60 min", "Por sesión", color="#facc15")

    # ==============================================================================
    # TAB 2: ESQUEMA SQL
    # ==============================================================================
    with tab_sql:
        st.markdown("#### Script de Inicialización para Supabase SQL Editor")
        st.caption("Copia este script completo y pégalo en el **SQL Editor** de tu proyecto Supabase para crear automáticamente todas las tablas, índices, triggers y el bucket de Storage.")

        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "supabase_schema.sql")
        sql_content = ""
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
        
        st.code(sql_content, language="sql")

    # ==============================================================================
    # TAB 3: EXPLORADOR DE FRASES (EASTER EGG)
    # ==============================================================================
    with tab_quotes:
        st.markdown("#### 📼 100 Frases Icónicas y Bizarras de los 80s y 90s")
        st.caption("Colección de frases de Francella, Darín, Los Simuladores, Olmedo, Schwarzenegger, Stallone, Willis y más.")

        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            filtro_frase = st.text_input("Buscar frase, actor o película", placeholder="Ej: Francella, Terminator, Simuladores...")
        with col_q2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🎲 Frase Aleatoria"):
                rand_q = get_random_quote()
                st.session_state.sample_quote = rand_q

        if "sample_quote" in st.session_state:
            render_daily_quote_box(st.session_state.sample_quote)

        all_quotes = load_all_quotes()
        if filtro_frase:
            q_fil = filtro_frase.lower()
            all_quotes = [q for q in all_quotes if q_fil in q.get("frase","").lower() or q_fil in q.get("autor","").lower() or q_fil in q.get("obra","").lower()]

        st.markdown(f"**Total de frases listadas:** {len(all_quotes)}")
        for q in all_quotes:
            st.markdown(
                f"""
                <div style="background: #1e293b; border-left: 3px solid #c084fc; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
                    <b style="color: #f3e8ff;">#{q.get('id')} "{q.get('frase')}"</b><br/>
                    <span style="font-size: 0.8rem; color: #cbd5e1;">— {q.get('autor')} ({q.get('obra')}, {q.get('año')})</span>
                    <span style="font-size: 0.75rem; background: rgba(192,132,252,0.2); color: #e9d5ff; padding: 2px 6px; border-radius: 4px; float: right;">{q.get('categoria')}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
