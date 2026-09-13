"""
Vista de Historial Clínico y Evoluciones.
Permite visualizar y registrar la evolución de todos los pacientes,
analizar escalas de dolor (EVA) y exportar reportes de tratamiento.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date

from utils.supabase_client import (
    get_pacientes,
    get_evoluciones,
    create_evolucion,
    delete_evolucion
)
from utils.ui import (
    render_header,
    render_kpi_card
)

def render_historial_view():
    """Renderiza la vista consolidada de historias clínicas y evoluciones."""
    render_header("Historial Clínico y Evoluciones", "Registro detallado de tratamientos, notas de evolución y escala de dolor (EVA)", icon="🩺")

    pacientes_list = get_pacientes(activo_only=False)
    if not pacientes_list:
        st.info("No hay pacientes registrados aún para mostrar su historial.")
        return

    # ==============================================================================
    # FILTRO POR PACIENTE
    # ==============================================================================
    paciente_map = {f"{p['nombre_completo']} (DNI: {p.get('dni', 'S/D')})": p["id"] for p in pacientes_list}
    
    col_sel, col_stat = st.columns([3, 1])
    with col_sel:
        paciente_seleccionado_lbl = st.selectbox(
            "Seleccionar Paciente para ver su Historia Clínica",
            options=list(paciente_map.keys())
        )
        paciente_id = paciente_map[paciente_seleccionado_lbl]
        paciente_obj = next((p for p in pacientes_list if str(p["id"]) == str(paciente_id)), {})

    # Obtener evoluciones del paciente
    evoluciones = get_evoluciones(paciente_id)

    # Métricas del paciente
    with col_stat:
        render_kpi_card("Evoluciones", len(evoluciones), "Notas registradas", color="#38bdf8")

    st.markdown("---")

    # ==============================================================================
    # REGISTRAR NUEVA EVOLUCIÓN DIRECTAMENTE
    # ==============================================================================
    with st.expander(f"➕ Registrar Nueva Evolución para {paciente_obj.get('nombre_completo')}", expanded=False):
        with st.form("form_nueva_evolucion_global"):
            c1, c2 = st.columns([3, 1])
            with c1:
                ev_nota = st.text_area("Nota Clínica / Evaluación *", placeholder="Detalle la respuesta al tratamiento, estado muscular, movilidad, fuerza...")
                ev_trat = st.text_input("Tratamiento Aplicado", placeholder="Ej: Ondas de choque + Ejercicios de fortalecimiento excéntrico")
            with c2:
                ev_fecha = st.date_input("Fecha de Sesión", value=date.today())
                ev_eva = st.slider("Escala de Dolor (EVA)", min_value=0, max_value=10, value=3, help="0: Sin dolor, 10: Dolor máximo insoportable")

            btn_ev_save = st.form_submit_button("Guardar Evolución en Historial", type="primary", use_container_width=True)
            if btn_ev_save:
                if not ev_nota.strip():
                    st.error("Debes ingresar una nota clínica descriptiva.")
                else:
                    ok, msg = create_evolucion({
                        "paciente_id": paciente_id,
                        "fecha": ev_fecha.isoformat(),
                        "nota_clinica": ev_nota.strip(),
                        "tratamiento_aplicado": ev_trat.strip(),
                        "escala_dolor_eva": ev_eva
                    })
                    if ok:
                        st.success("Evolución guardada exitosamente.")
                        st.rerun()
                    else:
                        st.error(msg)

    # ==============================================================================
    # VISUALIZACIÓN DE EVOLUCIONES Y GRÁFICO DE DOLOR EVA
    # ==============================================================================
    if not evoluciones:
        st.info("Este paciente aún no cuenta con notas de evolución registradas.")
    else:
        tab_timeline, tab_grafico = st.tabs(["📜 Línea de Tiempo de Sesiones", "📈 Evolución del Dolor (EVA)"])

        with tab_timeline:
            st.markdown(f"#### Historial de Evolución ({len(evoluciones)} registros)")
            for ev in evoluciones:
                ev_id = str(ev.get("id"))
                f_ev = str(ev.get("fecha", ""))
                nota = ev.get("nota_clinica", "")
                trat = ev.get("tratamiento_aplicado", "")
                eva = ev.get("escala_dolor_eva")

                eva_badge = ""
                if eva is not None:
                    color_eva = "#ef4444" if eva >= 7 else "#f59e0b" if eva >= 4 else "#10b981"
                    eva_badge = f'<span style="background: {color_eva}; color: white; padding: 2px 8px; border-radius: 9999px; font-weight: bold; font-size: 0.8rem;">EVA {eva}/10</span>'

                st.markdown(
                    f"""
                    <div class="kns-card" style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 0.95rem; font-weight: 700; color: #38bdf8;">🗓 Sesión del {f_ev}</span>
                            <div>{eva_badge}</div>
                        </div>
                        <div style="font-size: 0.92rem; color: #f8fafc; line-height: 1.5;">
                            {nota}
                        </div>
                        {f'<div style="margin-top: 8px; font-size: 0.82rem; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px;"><b>Tratamiento:</b> {trat}</div>' if trat else ''}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Botón para borrar evolución puntual si fue error
                with st.expander("Opciones de registro", expanded=False):
                    if st.button("🗑 Eliminar esta nota clínica", key=f"del_ev_{ev_id}"):
                        delete_evolucion(ev_id)
                        st.warning("Evolución eliminada.")
                        st.rerun()

        with tab_grafico:
            st.markdown("#### Curva de Alivio y Evolución del Dolor")
            st.caption("Seguimiento del progreso del paciente a lo largo de las sesiones mediante la Escala Visual Analógica (EVA).")

            # Armar dataframe para el gráfico
            df_eva = []
            for ev in reversed(evoluciones):
                if ev.get("escala_dolor_eva") is not None:
                    df_eva.append({
                        "Fecha": ev.get("fecha"),
                        "Nivel de Dolor (EVA)": int(ev.get("escala_dolor_eva"))
                    })

            if df_eva:
                df = pd.DataFrame(df_eva)
                st.line_chart(df.set_index("Fecha"))
            else:
                st.info("No hay registros con valor de EVA para graficar.")
