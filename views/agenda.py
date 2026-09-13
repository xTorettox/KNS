"""
Vista de Agenda y Gestión de Turnos.
Horario laboral de 08:00 a 15:00 hs con capacidad máxima de 2 pacientes en simultáneo
y duraciones dinámicas de 30, 45 o 60 minutos.
"""
import streamlit as st
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any

from utils.supabase_client import (
    get_turnos,
    get_pacientes,
    create_turno,
    update_turno,
    delete_turno,
    check_turnos_overlap,
    create_evolucion
)
from utils.whatsapp import (
    generate_whatsapp_url,
    template_recordatorio_turno,
    template_confirmacion_turno,
    template_reprogramacion_turno
)
from utils.ui import (
    render_header,
    render_kpi_card,
    render_status_badge,
    render_session_progress
)

WORK_START_HOUR = 8
WORK_END_HOUR = 15

def render_agenda_view():
    """Renderiza la vista principal de la agenda kinesiológica."""
    render_header("Agenda de Turnos", "Gestión diaria de pacientes de 08:00 a 15:00 hs (Máximo 2 simultáneos)", icon="📅")

    # ==============================================================================
    # SELECTOR DE FECHA Y CONTROLES RÁPIDOS
    # ==============================================================================
    if "agenda_date" not in st.session_state:
        st.session_state.agenda_date = date.today()

    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1.2, 1.2, 2.5, 2.1])

    with col_nav1:
        if st.button("◀ Día Anterior", use_container_width=True):
            st.session_state.agenda_date -= timedelta(days=1)
            st.rerun()

    with col_nav2:
        if st.button("Día Siguiente ▶", use_container_width=True):
            st.session_state.agenda_date += timedelta(days=1)
            st.rerun()

    with col_nav3:
        selected_date = st.date_input(
            "Seleccionar Fecha",
            value=st.session_state.agenda_date,
            label_visibility="collapsed"
        )
        if selected_date != st.session_state.agenda_date:
            st.session_state.agenda_date = selected_date
            st.rerun()

    with col_nav4:
        if st.button("📅 Ir a Hoy", use_container_width=True, type="secondary"):
            st.session_state.agenda_date = date.today()
            st.rerun()

    current_date = st.session_state.agenda_date
    current_date_str = current_date.strftime("%d/%m/%Y")
    
    # Obtener turnos del día
    turnos_dia = get_turnos(target_date=current_date)
    pacientes_list = get_pacientes(activo_only=True)

    # ==============================================================================
    # RESUMEN METRICO DEL DÍA (KPIS)
    # ==============================================================================
    total_turnos = len(turnos_dia)
    asistidos = sum(1 for t in turnos_dia if t.get("estado") == "Asistió")
    pendientes = sum(1 for t in turnos_dia if t.get("estado") == "Pendiente")
    cancelados = sum(1 for t in turnos_dia if t.get("estado") == "Cancelado")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        render_kpi_card("Turnos Agendados", total_turnos, f"Jornada {current_date_str}", color="#38bdf8")
    with kpi2:
        render_kpi_card("Asistencias", asistidos, "Pacientes atendidos", color="#4ade80")
    with kpi3:
        render_kpi_card("Pendientes", pendientes, "Por atender hoy", color="#facc15")
    with kpi4:
        render_kpi_card("Cancelados / Aus.", cancelados, "Lugares liberados", color="#f87171")

    st.markdown("---")

    # ==============================================================================
    # SECCIONES: FORMULARIO AGENDAR NUEVO TURNO + LISTA DE TURNOS
    # ==============================================================================
    tab_turnos, tab_nuevo_turno, tab_matriz = st.tabs(["📋 Turnos del Día", "➕ Agendar Nuevo Turno", "📊 Ocupación Horaria (08:00 - 15:00)"])

    # ------------------------------------------------------------------------------
    # TAB 1: LISTADO DE TURNOS Y GESTIÓN EN TIEMPO REAL
    # ------------------------------------------------------------------------------
    with tab_turnos:
        if not turnos_dia:
            st.info(f"No hay turnos programados para el día **{current_date_str}**. ¡Utiliza la pestaña 'Agendar Nuevo Turno' para comenzar!")
        else:
            st.markdown(f"#### Turnos programados para el **{current_date_str}** ({len(turnos_dia)} pacientes)")
            
            for idx, turno in enumerate(turnos_dia):
                t_id = str(turno.get("id"))
                p_nombre = turno.get("paciente_nombre", "Paciente")
                p_tel = turno.get("paciente_telefono", "")
                p_os = turno.get("paciente_obra_social", "Particular")
                h_ini = str(turno.get("hora_inicio", ""))[:5]
                h_fin = str(turno.get("hora_fin", ""))[:5]
                dur = turno.get("duracion_minutos", 45)
                estado = turno.get("estado", "Pendiente")
                notas = turno.get("notas", "")
                motivo_ajuste = turno.get("motivo_ajuste", "")
                ses_real = turno.get("paciente_sesiones_realizadas", 0)
                ses_tot = turno.get("paciente_sesiones_totales", 10)
                p_id = str(turno.get("paciente_id", ""))

                with st.container():
                    st.markdown(
                        f"""
                        <div class="kns-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                                <div>
                                    <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">⏰ {h_ini} - {h_fin} hs</span>
                                    <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 8px;">({dur} min)</span>
                                    <h4 style="margin: 4px 0 2px 0; color: #38bdf8;">👤 {p_nombre}</h4>
                                    <span style="font-size: 0.85rem; color: #cbd5e1;">🏥 Obra Social: <b>{p_os or 'Particular'}</b></span>
                                </div>
                                <div>
                                    {render_status_badge(estado)}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Subcontroles para el turno
                    c_det1, c_det2, c_det3, c_det4 = st.columns([2.2, 1.8, 1.5, 1.5])
                    
                    # 1. Indicador de sesiones
                    with c_det1:
                        st.markdown(render_session_progress(ses_real, ses_tot), unsafe_allow_html=True)
                        if notas:
                            st.caption(f"📝 *Notas:* {notas}")
                        if motivo_ajuste:
                            st.caption(f"⏱ *Ajuste horario:* {motivo_ajuste}")

                    # 2. Botón WhatsApp Directo
                    with c_det2:
                        msg_wa = template_recordatorio_turno(p_nombre, current_date_str, h_ini)
                        wa_url = generate_whatsapp_url(p_tel, msg_wa)
                        st.markdown(
                            f'<a href="{wa_url}" target="_blank" class="btn-wa">📲 WhatsApp ({p_tel or "Sin tel"})</a>',
                            unsafe_allow_html=True
                        )

                    # 3. Cambio rápido de estado
                    with c_det3:
                        estados_opciones = ["Pendiente", "Asistió", "Cancelado", "Reprogramado", "Ausente"]
                        idx_estado = estados_opciones.index(estado) if estado in estados_opciones else 0
                        nuevo_estado = st.selectbox(
                            "Estado",
                            options=estados_opciones,
                            index=idx_estado,
                            key=f"estado_sel_{t_id}",
                            label_visibility="collapsed"
                        )
                        if nuevo_estado != estado:
                            ok, msg = update_turno(t_id, {"estado": nuevo_estado})
                            if ok:
                                st.toast(f"Estado actualizado a '{nuevo_estado}' (Sesiones sincronizadas)", icon="✅")
                                st.rerun()
                            else:
                                st.error(msg)

                    # 4. Acciones de Edición / Ajuste Horario
                    with c_det4:
                        with st.popover("⚙️ Editar / Ajustar"):
                            st.markdown("##### Ajustar Horario o Notas")
                            st.caption("Útil para registrar llegadas tarde o desfasajes de tiempo.")
                            
                            # Selector de hora inicio
                            curr_h_ini_obj = datetime.strptime(h_ini, "%H:%M").time()
                            nuevo_h_ini = st.time_input("Nueva Hora Inicio", value=curr_h_ini_obj, key=f"edit_hi_{t_id}")
                            
                            # Selector de duración
                            dur_opts = [30, 45, 60]
                            idx_dur = dur_opts.index(dur) if dur in dur_opts else 1
                            nueva_dur = st.selectbox("Duración (min)", dur_opts, index=idx_dur, key=f"edit_dur_{t_id}")
                            
                            # Calcular nueva hora fin
                            dummy_dt = datetime.combine(date.today(), nuevo_h_ini) + timedelta(minutes=nueva_dur)
                            nuevo_h_fin = dummy_dt.time()
                            st.info(f"Hora de finalización: **{nuevo_h_fin.strftime('%H:%M')} hs**")
                            
                            nuevo_motivo = st.text_input("Motivo del ajuste", value=motivo_ajuste, placeholder="Ej: Llegó 15 min tarde por tráfico", key=f"edit_mot_{t_id}")
                            nuevas_notas = st.text_area("Notas del turno", value=notas, key=f"edit_not_{t_id}")
                            
                            col_save, col_del = st.columns(2)
                            with col_save:
                                if st.button("Guardar Cambios", key=f"btn_save_{t_id}", type="primary", use_container_width=True):
                                    ok, msg = update_turno(t_id, {
                                        "hora_inicio": nuevo_h_ini,
                                        "hora_fin": nuevo_h_fin,
                                        "duracion_minutos": nueva_dur,
                                        "motivo_ajuste": nuevo_motivo,
                                        "notas": nuevas_notas
                                    })
                                    if ok:
                                        st.success("Turno actualizado correctamente.")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            with col_del:
                                if st.button("Eliminar Turno", key=f"btn_del_{t_id}", type="secondary", use_container_width=True):
                                    delete_turno(t_id)
                                    st.warning("Turno eliminado.")
                                    st.rerun()

                    # Opción para registrar evolución rápida si el paciente asistió
                    if estado == "Asistió":
                        with st.expander(f"🩺 Registrar Evolución de la Sesión para {p_nombre}"):
                            with st.form(key=f"quick_evol_form_{t_id}"):
                                col_ev1, col_ev2 = st.columns([3, 1])
                                with col_ev1:
                                    quick_nota = st.text_area("Nota Clínica / Evolución", placeholder="Ej: Paciente refiere mejoría en la marcha. Se realizó movilización pasiva...")
                                    quick_trat = st.text_input("Tratamiento Aplicado", placeholder="Ej: TENS + Crioterapia + Ejercicios de fortalecimiento")
                                with col_ev2:
                                    quick_eva = st.slider("Escala de Dolor (EVA 0-10)", 0, 10, 4)
                                
                                submit_evol = st.form_submit_button("Guardar en Historial Clínico", type="primary")
                                if submit_evol:
                                    if quick_nota:
                                        ok_ev, msg_ev = create_evolucion({
                                            "paciente_id": p_id,
                                            "turno_id": t_id,
                                            "fecha": current_date.isoformat(),
                                            "nota_clinica": quick_nota,
                                            "tratamiento_aplicado": quick_trat,
                                            "escala_dolor_eva": quick_eva
                                        })
                                        if ok_ev:
                                            st.success("¡Evolución guardada exitosamente en el historial del paciente!")
                                        else:
                                            st.error(msg_ev)
                                    else:
                                        st.warning("Ingresa la nota clínica para registrar la evolución.")

                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------------------
    # TAB 2: AGENDAR NUEVO TURNO (VALIDACIÓN SUPERPOSICIÓN MÁX 2)
    # ------------------------------------------------------------------------------
    with tab_nuevo_turno:
        st.markdown("#### Agendar Turno Kinesiológico")
        st.caption("El sistema valida automáticamente que no haya más de 2 pacientes en simultáneo y respeta el rango de 08:00 a 15:00 hs.")

        if not pacientes_list:
            st.warning("No hay pacientes activos registrados. Por favor, crea un paciente primero en la sección 'Pacientes'.")
        else:
            with st.form("form_nuevo_turno", clear_on_submit=False):
                col_ag1, col_ag2 = st.columns(2)
                
                with col_ag1:
                    paciente_options = {p["nombre_completo"]: p["id"] for p in pacientes_list}
                    nombre_sel = st.selectbox("Seleccionar Paciente", list(paciente_options.keys()))
                    paciente_id_sel = paciente_options[nombre_sel]

                    # Mostrar datos del paciente seleccionado
                    paciente_obj = next((p for p in pacientes_list if p["id"] == paciente_id_sel), {})
                    if paciente_obj:
                        ses_r = paciente_obj.get("sesiones_realizadas", 0)
                        ses_t = paciente_obj.get("sesiones_totales", 10)
                        restantes = max(0, ses_t - ses_r)
                        st.markdown(f"📋 **Obra Social:** {paciente_obj.get('obra_social', 'Particular')} | **Sesiones Restantes:** {restantes} de {ses_t}")
                        if restantes <= 0:
                            st.error("⚠️ Este paciente ha completado todas sus sesiones autorizadas. Solicitar nueva orden.")

                with col_ag2:
                    col_h1, col_h2 = st.columns(2)
                    with col_h1:
                        # Generar opciones de hora inicio de 08:00 a 14:30
                        hora_inicio_sel = st.time_input("Hora de Inicio", value=time(8, 30))
                    
                    with col_h2:
                        duracion_sel = st.selectbox("Duración de la Sesión", [30, 45, 60], index=1)
                
                # Calcular hora fin
                dt_temp = datetime.combine(current_date, hora_inicio_sel) + timedelta(minutes=duracion_sel)
                hora_fin_calc = dt_temp.time()

                # Validaciones visuales inmediatas
                st.markdown(
                    f"""
                    <div style="background-color: rgba(2, 132, 199, 0.1); border-left: 4px solid #0284c7; padding: 10px; border-radius: 6px; margin: 10px 0;">
                        <b>Resumen de Horario:</b> {hora_inicio_sel.strftime('%H:%M')} hs ➔ {hora_fin_calc.strftime('%H:%M')} hs ({duracion_sel} minutos)
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Notas y estado inicial
                col_n1, col_n2 = st.columns([2, 1])
                with col_n1:
                    turno_notas = st.text_input("Tratamiento previsto / Notas", placeholder="Ej: Fisioterapia + ejercicios propioceptivos")
                with col_n2:
                    turno_estado_ini = st.selectbox("Estado Inicial", ["Pendiente", "Asistió"])

                # Botón de submit
                btn_agendar = st.form_submit_button("📅 Confirmar y Agendar Turno", type="primary", use_container_width=True)

                if btn_agendar:
                    # Validar rango horario de 08:00 a 15:00
                    h_ini_val = hora_inicio_sel.hour * 60 + hora_inicio_sel.minute
                    h_fin_val = hora_fin_calc.hour * 60 + hora_fin_calc.minute

                    if h_ini_val < WORK_START_HOUR * 60 or h_fin_val > WORK_END_HOUR * 60:
                        st.error(f"El turno debe estar comprendido dentro del horario de atención ({WORK_START_HOUR}:00 a {WORK_END_HOUR}:00 hs).")
                    else:
                        # Validar superposición (máx 2 pacientes)
                        is_valid, count_overlap, overlap_msg = check_turnos_overlap(
                            target_date=current_date,
                            hora_inicio=hora_inicio_sel,
                            hora_fin=hora_fin_calc
                        )

                        if not is_valid:
                            st.error(f"❌ {overlap_msg}")
                        else:
                            ok, msg, new_turno = create_turno({
                                "paciente_id": paciente_id_sel,
                                "fecha": current_date.isoformat(),
                                "hora_inicio": hora_inicio_sel,
                                "hora_fin": hora_fin_calc,
                                "duracion_minutos": duracion_sel,
                                "estado": turno_estado_ini,
                                "notas": turno_notas
                            })

                            if ok:
                                st.success(f"✅ ¡Turno agendado exitosamente para **{nombre_sel}**!")
                                
                                # Generar link de WhatsApp para confirmación
                                tel_p = paciente_obj.get("telefono", "")
                                if tel_p:
                                    wa_conf = template_confirmacion_turno(
                                        nombre_paciente=nombre_sel,
                                        fecha_str=current_date_str,
                                        hora_str=hora_inicio_sel.strftime('%H:%M'),
                                        duracion_minutos=duracion_sel
                                    )
                                    url_conf = generate_whatsapp_url(tel_p, wa_conf)
                                    st.markdown(
                                        f'<a href="{url_conf}" target="_blank" class="btn-wa">📲 Enviar Confirmación por WhatsApp a {nombre_sel}</a>',
                                        unsafe_allow_html=True
                                    )
                                st.rerun()
                            else:
                                st.error(f"Error al agendar turno: {msg}")

    # ------------------------------------------------------------------------------
    # TAB 3: MATRIZ DE OCUPACIÓN HORARIA (08:00 A 15:00)
    # ------------------------------------------------------------------------------
    with tab_matriz:
        st.markdown(f"#### Ocupación de Camillas / Consultorio ({current_date_str})")
        st.caption("Capacidad máxima por franja horaria: **2 pacientes en simultáneo**.")

        # Generar bloques de 30 minutos desde las 08:00 hasta las 15:00
        time_slots = []
        curr_time = datetime.combine(current_date, time(8, 0))
        end_time = datetime.combine(current_date, time(15, 0))

        while curr_time < end_time:
            slot_start = curr_time.time()
            slot_end = (curr_time + timedelta(minutes=30)).time()
            time_slots.append((slot_start, slot_end))
            curr_time += timedelta(minutes=30)

        # Evaluar qué pacientes están en cada bloque
        for s_start, s_end in time_slots:
            s_start_min = s_start.hour * 60 + s_start.minute
            s_end_min = s_end.hour * 60 + s_end.minute

            pacientes_en_slot = []
            for t in turnos_dia:
                if t.get("estado") == "Cancelado":
                    continue
                t_hi = str(t.get("hora_inicio"))
                t_hf = str(t.get("hora_fin"))
                
                parts_i = t_hi.split(":")
                parts_f = t_hf.split(":")
                t_i_min = int(parts_i[0]) * 60 + int(parts_i[1])
                t_f_min = int(parts_f[0]) * 60 + int(parts_f[1])

                # Hay superposición si el turno coincide con este bloque de 30 min
                if t_i_min < s_end_min and t_f_min > s_start_min:
                    pacientes_en_slot.append(t)

            ocupacion = len(pacientes_en_slot)
            
            if ocupacion == 0:
                badge_slot = '<span style="color: #64748b; font-size: 0.8rem;">● Libre (0/2)</span>'
                border_color = "#334155"
            elif ocupacion == 1:
                badge_slot = '<span style="color: #38bdf8; font-size: 0.8rem; font-weight: 700;">● 1 Paciente (1/2 Disponible)</span>'
                border_color = "#0284c7"
            else:
                badge_slot = '<span style="color: #f87171; font-size: 0.8rem; font-weight: 700;">● COMPLETO (2/2)</span>'
                border_color = "#ef4444"

            # Renderizar fila de la matriz
            nombres_txt = ", ".join([f"<b>{t.get('paciente_nombre')}</b> ({str(t.get('hora_inicio'))[:5]}-{str(t.get('hora_fin'))[:5]})" for t in pacientes_en_slot]) if pacientes_en_slot else "<i style='color: #64748b;'>Sin turnos asignados</i>"

            st.markdown(
                f"""
                <div style="background: #1e293b; border-left: 5px solid {border_color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <b style="color: #f8fafc; font-size: 0.95rem;">{s_start.strftime('%H:%M')} - {s_end.strftime('%H:%M')} hs</b>
                        <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 2px;">{nombres_txt}</div>
                    </div>
                    <div>
                        {badge_slot}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
