"""
Vista de Agenda y Gestión de Turnos (Mobile-First, Grillas 7-Columnas Inquebrantables e Integración Google Calendar).
Permite navegar el calendario por Mes o Semana en formato grilla real que no colapsa en móviles,
inspeccionar turnos de cualquier día al tocarlo, ver la quincena contraída por día,
y sincronizar con Google Calendar e iCal (.ics).
"""
import streamlit as st
import calendar
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any

from utils.supabase_client import (
    get_turnos,
    get_pacientes,
    create_paciente,
    create_turno,
    update_turno,
    delete_turno,
    check_turnos_overlap,
    create_evolucion,
    get_app_config,
    create_pago
)
from utils.whatsapp import (
    generate_whatsapp_url,
    template_recordatorio_turno,
    template_confirmacion_turno,
    template_confirmacion_turno_con_link,
    template_alta_paciente_link,
    template_reprogramacion_turno
)
from utils.registration import (
    create_registration_token,
    generate_registration_link,
    generate_registration_whatsapp_url
)
from utils.google_calendar import (
    generate_google_calendar_url,
    generate_turno_google_url,
    generate_ics_content
)
from utils.ui import (
    st_html,
    render_header,
    render_kpi_card,
    render_status_badge,
    render_session_progress,
    render_google_calendar_button
)

WORK_START_HOUR = 8
WORK_END_HOUR = 15

MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_COMPLETOS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ==============================================================================
# GENERADORES DE HTML PARA GRILLAS DE CALENDARIO 7 COLUMNAS (NO COLAPSAN EN MÓVIL)
# ==============================================================================

def generate_month_calendar_html(year: int, month: int, selected_date: date, turnos_por_dia: Dict[int, List[Dict[str, Any]]], session_token: str = "") -> str:
    """Genera la tabla HTML de 7 columnas del mes completo sin sangría Markdown para evitar bloques de código."""
    month_matrix = calendar.monthcalendar(year, month)
    today = date.today()
    token_param = f"&session_token={session_token}" if session_token else ""

    html = []
    html.append('<div class="kns-cal-container">')
    html.append('<table class="kns-cal-table">')
    html.append('<thead><tr>')
    for d_name in DIAS_ES:
        html.append(f'<th>{d_name}</th>')
    html.append('</tr></thead>')
    html.append('<tbody>')
    
    for week in month_matrix:
        html.append('<tr>')
        for day_num in week:
            if day_num == 0:
                html.append('<td><div class="kns-cal-cell empty"></div></td>')
            else:
                d_date = date(year, month, day_num)
                is_today = (d_date == today)
                is_selected = (d_date == selected_date)
                
                turnos_d = turnos_por_dia.get(day_num, [])
                cant = len(turnos_d)
                
                if cant == 0:
                    badge_html = '<span class="kns-day-badge kns-badge-zero">0 t.</span>'
                elif cant < 4:
                    badge_html = f'<span class="kns-day-badge kns-badge-turnos">{cant} t.</span>'
                else:
                    badge_html = f'<span class="kns-day-badge kns-badge-full">{cant} t.</span>'
                    
                classes = ["kns-cal-cell"]
                if is_today:
                    classes.append("today")
                if is_selected:
                    classes.append("selected")
                    
                cls_str = " ".join(classes)
                d_iso = d_date.isoformat()
                star_txt = "★ " if is_today else ""
                
                cell_html = (
                    f'<td>'
                    f'<a href="?page=agenda&cal_date={d_iso}&cal_month={month}&cal_year={year}&view_mode=month{token_param}" target="_self" class="{cls_str}">'
                    f'<div class="kns-day-num">{star_txt}{day_num}</div>'
                    f'{badge_html}'
                    f'</a>'
                    f'</td>'
                )
                html.append(cell_html)
        html.append('</tr>')
        
    html.append('</tbody></table>')
    html.append('</div>')
    return "".join(html)

def generate_week_calendar_html(start_of_week: date, selected_date: date, turnos_semana_map: Dict[str, List[Dict[str, Any]]], session_token: str = "") -> str:
    """Genera la tabla HTML de 7 columnas de la semana actual."""
    today = date.today()
    token_param = f"&session_token={session_token}" if session_token else ""
    
    html = []
    html.append('<div class="kns-cal-container">')
    html.append('<table class="kns-cal-table">')
    html.append('<thead><tr>')
    for d_name in DIAS_ES:
        html.append(f'<th>{d_name}</th>')
    html.append('</tr></thead>')
    html.append('<tbody><tr>')
    
    for idx in range(7):
        d_curr = start_of_week + timedelta(days=idx)
        d_iso = d_curr.isoformat()
        is_today = (d_curr == today)
        is_selected = (d_curr == selected_date)
        
        turnos_d = turnos_semana_map.get(d_iso, [])
        cant = len(turnos_d)
        
        if cant == 0:
            badge_html = '<span class="kns-day-badge kns-badge-zero">0 t.</span>'
        elif cant < 4:
            badge_html = f'<span class="kns-day-badge kns-badge-turnos">{cant} t.</span>'
        else:
            badge_html = f'<span class="kns-day-badge kns-badge-full">{cant} t.</span>'
            
        classes = ["kns-cal-cell"]
        if is_today:
            classes.append("today")
        if is_selected:
            classes.append("selected")
            
        cls_str = " ".join(classes)
        star_txt = "★ " if is_today else ""
        
        cell_html = (
            f'<td>'
            f'<a href="?page=agenda&cal_date={d_iso}&view_mode=week{token_param}" target="_self" class="{cls_str}">'
            f'<div class="kns-day-num">{star_txt}{d_curr.day}</div>'
            f'{badge_html}'
            f'</a>'
            f'</td>'
        )
        html.append(cell_html)
        
    html.append('</tr></tbody></table>')
    html.append('</div>')
    return "".join(html)

# ==============================================================================
# DETALLE DEL DÍA INSPECCIONADO
# ==============================================================================

def render_day_turnos_detail(target_date: date, clinic_name: str, show_title: bool = True):
    """Renderiza el detalle de turnos, acciones, WhatsApp, Google Calendar y matriz de un día específico."""
    target_date_str = target_date.strftime("%d/%m/%Y")
    d_idx = target_date.weekday()
    dia_nombre = DIAS_COMPLETOS_ES[d_idx]
    
    turnos_dia = get_turnos(target_date=target_date)
    
    if show_title:
        st_html(
            f"""
            <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)); border-left: 5px solid #38bdf8; border-radius: 10px; padding: 12px 16px; margin: 12px 0 16px 0;">
                <h4 style="margin: 0; color: #f8fafc;">📋 Turnos del {dia_nombre} {target_date_str}</h4>
                <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 2px;">Total: <b>{len(turnos_dia)} turnos programados</b></div>
            </div>
            """
        )

    if not turnos_dia:
        st.info(f"No hay turnos agendados para el **{dia_nombre} {target_date_str}**.")
    else:
        for idx, turno in enumerate(turnos_dia):
            t_id = str(turno.get("id"))
            p_nombre = turno.get("paciente_nombre", "Paciente")
            p_tel = turno.get("paciente_telefono", "")
            p_os = turno.get("paciente_obra_social", "Particular")
            is_part = (str(p_os).lower().strip() == "particular")
            h_ini = str(turno.get("hora_inicio", ""))[:5]
            h_fin = str(turno.get("hora_fin", ""))[:5]
            dur = turno.get("duracion_minutos", 45)
            estado = turno.get("estado", "Pendiente")
            monto_cos = float(turno.get("monto_coseguro", 0) or turno.get("paciente_monto_coseguro_default", 0) or 0)
            estado_pago = turno.get("estado_pago", "Pendiente")
            notas = turno.get("notas", "")
            motivo_ajuste = turno.get("motivo_ajuste", "")
            ses_real = turno.get("paciente_sesiones_realizadas", 0)
            ses_tot = turno.get("paciente_sesiones_totales", 10)
            p_id = str(turno.get("paciente_id", ""))

            gcal_url_t = generate_turno_google_url(turno, clinic_name=clinic_name)

            badge_pago_html = '<span style="background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;">✓ ABONADO</span>' if estado_pago == "Abonado" else '<span style="background: rgba(234,179,8,0.15); color: #facc15; border: 1px solid rgba(234,179,8,0.3); padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;">⏳ PAGO PENDIENTE</span>'

            is_ficha_completa = bool(turno.get("paciente_ficha_completada", False))
            badge_ficha_html = '<span style="background: rgba(56,189,248,0.15); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3); padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;">📋 FICHA COMPLETA</span>' if is_ficha_completa else '<span style="background: rgba(251,146,60,0.15); color: #fb923c; border: 1px solid rgba(251,146,60,0.3); padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;">📝 FICHA PENDIENTE</span>'

            with st.container():
                st_html(
                    f"""
                    <div class="kns-card" style="margin-bottom: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">⏰ {h_ini} - {h_fin} hs</span>
                                <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 8px;">({dur} min)</span>
                                <h4 style="margin: 4px 0 2px 0; color: #38bdf8;">👤 {p_nombre}</h4>
                                <div style="font-size: 0.85rem; color: #cbd5e1; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px;">
                                    <span>{'👤 Particular' if is_part else f'🏥 {p_os}'}</span>
                                    <span>•</span>
                                    <span>💵 {'Valor Sesión:' if is_part else 'Coseguro:'} <b style="color: #4ade80;">${monto_cos:,.2f}</b></span>
                                    <span>•</span>
                                    {badge_pago_html}
                                    <span>•</span>
                                    {badge_ficha_html}
                                </div>
                            </div>
                            <div>
                                {render_status_badge(estado)}
                            </div>
                        </div>
                    </div>
                    """
                )

                c_det1, c_det2, c_det3, c_det4, c_det5 = st.columns([1.7, 1.4, 1.2, 1.2, 1.5])
                
                with c_det1:
                    st_html(render_session_progress(ses_real, ses_tot))
                    if notas:
                        st.caption(f"📝 *Notas:* {notas}")
                    if motivo_ajuste:
                        st.caption(f"⏱ *Ajuste:* {motivo_ajuste}")

                with c_det2:
                    col_w1, col_w2 = st.columns(2)
                    with col_w1:
                        msg_wa = template_recordatorio_turno(p_nombre, target_date_str, h_ini, consultorio=clinic_name, gcal_url=gcal_url_t)
                        wa_url = generate_whatsapp_url(p_tel, msg_wa)
                        st_html(f'<a href="{wa_url}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;" title="Recordatorio por WhatsApp">📲 Turno</a>')
                    with col_w2:
                        with st.popover("🔗 Ficha", use_container_width=True):
                            st.markdown("###### Enlace de Ficha y Pedido Médico")
                            st.caption("Enviar al paciente para que complete sus datos y suba su orden:")
                            reg_tok = create_registration_token(p_id, t_id, p_nombre, p_tel)
                            wa_link_ficha = generate_registration_whatsapp_url(p_tel, p_nombre, reg_tok["token"], turno_fecha=target_date_str, turno_hora=h_ini, clinic_name=clinic_name)
                            st_html(f'<a href="{wa_link_ficha}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center; margin-bottom: 6px;">📲 Enviar WhatsApp</a>')
                            st.caption("Enlace directo:")
                            st.code(f"?registro={reg_tok['token']}", language="text")

                with c_det3:
                    st_html(f'<a href="{gcal_url_t}" target="_blank" class="btn-gcal" style="width: 100%; text-align: center; justify-content: center;">📅 Google Cal</a>')

                with c_det4:
                    estados_opciones = ["Pendiente", "Asistió", "Cancelado", "Reprogramado", "Ausente"]
                    idx_estado = estados_opciones.index(estado) if estado in estados_opciones else 0
                    nuevo_estado = st.selectbox(
                        "Estado",
                        options=estados_opciones,
                        index=idx_estado,
                        key=f"estado_sel_grid_{t_id}",
                        label_visibility="collapsed"
                    )
                    if nuevo_estado != estado:
                        ok, msg = update_turno(t_id, {"estado": nuevo_estado})
                        if ok:
                            st.toast(f"Estado actualizado a '{nuevo_estado}'", icon="✅")
                            st.rerun()
                        else:
                            st.error(msg)

                with c_det5:
                    col_pop1, col_pop2 = st.columns(2)
                    with col_pop1:
                        # POPUP / POPOVER COBRO RÁPIDO
                        lbl_btn_cobro = "✅ Cobrado" if estado_pago == "Abonado" else "💵 Cobrar"
                        with st.popover(lbl_btn_cobro, use_container_width=True):
                            st.markdown("###### Registrar Cobro de Sesión")
                            with st.form(f"quick_pay_form_{t_id}"):
                                q_monto = st.number_input(
                                    "Monto a Cobrar ($)",
                                    min_value=0.0,
                                    step=500.0,
                                    value=monto_cos if monto_cos > 0 else 4000.0
                                )
                                q_metodo = st.selectbox("Método", ["Efectivo", "Transferencia / MP", "Tarjeta Débito", "Tarjeta Crédito", "Otro"], key=f"q_met_{t_id}")
                                q_concepto = st.text_input("Concepto", value=f"{'Valor Consulta Particular' if is_part else 'Coseguro Sesión'} ({target_date_str})", key=f"q_con_{t_id}")
                                
                                btn_quick_pay = st.form_submit_button("Confirmar Cobro", type="primary", use_container_width=True)
                                if btn_quick_pay:
                                    ok_qp, msg_qp, _ = create_pago({
                                        "paciente_id": p_id,
                                        "turno_id": t_id,
                                        "fecha_pago": target_date.isoformat(),
                                        "monto": float(q_monto),
                                        "concepto": q_concepto.strip(),
                                        "modalidad": "Por sesión",
                                        "metodo_pago": q_metodo,
                                        "sesiones_cubiertas": 1,
                                        "notas": f"Cobro registrado desde agenda del día {target_date_str}"
                                    })
                                    if ok_qp:
                                        update_turno(t_id, {"estado_pago": "Abonado", "monto_coseguro": float(q_monto)})
                                        st.success("¡Cobro registrado exitosamente!")
                                        st.rerun()
                                    else:
                                        st.error(msg_qp)
                                        st.error(msg_qp)

                    with col_pop2:
                        with st.popover("⚙️ Ajustar", use_container_width=True):
                            st.markdown("##### Ajustar Horario, Coseguro o Notas")
                            curr_h_ini_obj = datetime.strptime(h_ini, "%H:%M").time()
                            nuevo_h_ini = st.time_input("Nueva Hora Inicio", value=curr_h_ini_obj, key=f"grid_edit_hi_{t_id}")
                            
                            dur_opts = [30, 45, 60]
                            idx_dur = dur_opts.index(dur) if dur in dur_opts else 1
                            nueva_dur = st.selectbox("Duración (min)", dur_opts, index=idx_dur, key=f"grid_edit_dur_{t_id}")
                            
                            dummy_dt = datetime.combine(date.today(), nuevo_h_ini) + timedelta(minutes=nueva_dur)
                            nuevo_h_fin = dummy_dt.time()
                            st.info(f"Hora de fin: **{nuevo_h_fin.strftime('%H:%M')} hs**")
                            
                            edit_monto_cos = st.number_input("Monto Coseguro / Sesión ($)", min_value=0.0, step=500.0, value=monto_cos, key=f"grid_edit_cos_{t_id}")
                            edit_estado_pago = st.selectbox("Estado del Pago", ["Pendiente", "Abonado", "Parcial", "Exento"], index=["Pendiente", "Abonado", "Parcial", "Exento"].index(estado_pago) if estado_pago in ["Pendiente", "Abonado", "Parcial", "Exento"] else 0, key=f"grid_edit_ep_{t_id}")
                            
                            nuevo_motivo = st.text_input("Motivo del ajuste", value=motivo_ajuste, placeholder="Ej: Llegó 15 min tarde", key=f"grid_edit_mot_{t_id}")
                            nuevas_notas = st.text_area("Notas del turno", value=notas, key=f"grid_edit_not_{t_id}")
                            
                            col_save, col_del = st.columns(2)
                            with col_save:
                                if st.button("Guardar", key=f"grid_btn_save_{t_id}", type="primary", use_container_width=True):
                                    ok, msg = update_turno(t_id, {
                                        "hora_inicio": nuevo_h_ini,
                                        "hora_fin": nuevo_h_fin,
                                        "duracion_minutos": nueva_dur,
                                        "monto_coseguro": float(edit_monto_cos),
                                        "estado_pago": edit_estado_pago,
                                        "motivo_ajuste": nuevo_motivo,
                                        "notas": nuevas_notas
                                    })
                                    if ok:
                                        st.success("Turno actualizado.")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            with col_del:
                                if st.button("Eliminar", key=f"grid_btn_del_{t_id}", type="secondary", use_container_width=True):
                                    delete_turno(t_id)
                                    st.warning("Turno eliminado.")
                                    st.rerun()

                if estado == "Asistió":
                    with st.expander(f"🩺 Registrar Evolución de la Sesión para {p_nombre}"):
                        with st.form(key=f"grid_quick_evol_{t_id}"):
                            col_ev1, col_ev2 = st.columns([3, 1])
                            with col_ev1:
                                quick_nota = st.text_area("Nota Clínica / Evolución", placeholder="Ej: Movilización pasiva, fortalecimiento...")
                                quick_trat = st.text_input("Tratamiento Aplicado", placeholder="Ej: Fisioterapia + Magneto")
                            with col_ev2:
                                quick_eva = st.slider("Dolor (EVA 0-10)", 0, 10, 4)
                            
                            submit_evol = st.form_submit_button("Guardar Evolución", type="primary", use_container_width=True)
                            if submit_evol:
                                if quick_nota:
                                    ok_ev, msg_ev = create_evolucion({
                                        "paciente_id": p_id,
                                        "turno_id": t_id,
                                        "fecha": target_date.isoformat(),
                                        "nota_clinica": quick_nota,
                                        "tratamiento_aplicado": quick_trat,
                                        "escala_dolor_eva": quick_eva
                                    })
                                    if ok_ev:
                                        st.success("¡Evolución guardada exitosamente!")
                                    else:
                                        st.error(msg_ev)
                                else:
                                    st.warning("Ingresa la nota clínica para guardar la evolución.")

                st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    with st.expander(f"📊 Ver Ocupación Horaria de Camillas ({target_date_str})", expanded=False):
        time_slots = []
        curr_time = datetime.combine(target_date, time(8, 0))
        end_time = datetime.combine(target_date, time(15, 0))

        while curr_time < end_time:
            slot_start = curr_time.time()
            slot_end = (curr_time + timedelta(minutes=30)).time()
            time_slots.append((slot_start, slot_end))
            curr_time += timedelta(minutes=30)

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

                if t_i_min < s_end_min and t_f_min > s_start_min:
                    pacientes_en_slot.append(t)

            ocupacion = len(pacientes_en_slot)
            if ocupacion == 0:
                badge_slot = '<span style="color: #64748b; font-size: 0.8rem;">● Libre (0/2)</span>'
                border_color = "#334155"
            elif ocupacion == 1:
                badge_slot = '<span style="color: #38bdf8; font-size: 0.8rem; font-weight: 700;">● 1 Paciente (1/2 Disp.)</span>'
                border_color = "#0284c7"
            else:
                badge_slot = '<span style="color: #f87171; font-size: 0.8rem; font-weight: 700;">● COMPLETO (2/2)</span>'
                border_color = "#ef4444"

            nombres_txt = ", ".join([f"<b>{t.get('paciente_nombre')}</b> ({str(t.get('hora_inicio'))[:5]}-{str(t.get('hora_fin'))[:5]})" for t in pacientes_en_slot]) if pacientes_en_slot else "<i style='color: #64748b;'>Sin turnos</i>"

            st_html(
                f"""
                <div style="background: #1e293b; border-left: 5px solid {border_color}; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                    <div>
                        <b style="color: #f8fafc; font-size: 0.9rem;">{s_start.strftime('%H:%M')} - {s_end.strftime('%H:%M')} hs</b>
                        <span style="font-size: 0.82rem; color: #cbd5e1; margin-left: 8px;">{nombres_txt}</span>
                    </div>
                    <div>{badge_slot}</div>
                </div>
                """
            )

# ==============================================================================
# VISTA PRINCIPAL DE LA AGENDA
# ==============================================================================

def render_agenda_view():
    """Renderiza la vista principal de la agenda kinesiológica con Grilla Mensual, Grilla Semanal y Próximos 15 Días."""
    app_config = get_app_config()
    clinic_name = app_config.get("clinic_name", "KNS Kinesiología")

    # Sincronizar parámetros de URL
    if "cal_date" in st.query_params:
        try:
            st.session_state.agenda_date = datetime.strptime(st.query_params["cal_date"], "%Y-%m-%d").date()
            st.session_state.cal_month = st.session_state.agenda_date.month
            st.session_state.cal_year = st.session_state.agenda_date.year
        except Exception:
            pass

    if "cal_month" in st.query_params:
        try:
            st.session_state.cal_month = int(st.query_params["cal_month"])
        except Exception:
            pass

    if "cal_year" in st.query_params:
        try:
            st.session_state.cal_year = int(st.query_params["cal_year"])
        except Exception:
            pass

    if "view_mode" in st.query_params:
        v_param = st.query_params["view_mode"]
        if v_param == "month":
            st.session_state.agenda_view_mode = "🗓️ Grilla Mensual"
        elif v_param == "week":
            st.session_state.agenda_view_mode = "📅 Grilla Semanal"
        elif v_param == "15d":
            st.session_state.agenda_view_mode = "📋 Próximos 15 Días (Contraído)"

    if "agenda_view_mode" not in st.session_state:
        st.session_state.agenda_view_mode = "🗓️ Grilla Mensual"
        
    if "agenda_date" not in st.session_state:
        st.session_state.agenda_date = date.today()

    if "cal_month" not in st.session_state:
        st.session_state.cal_month = st.session_state.agenda_date.month
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = st.session_state.agenda_date.year

    render_header("Agenda de Turnos", "Gestión de turnos de 08:00 a 15:00 hs con grillas interactivas y Google Calendar", icon="📅")

    # Selector de Modo de Vista
    col_mode, col_export = st.columns([3.2, 1.2])
    with col_mode:
        view_modes = ["🗓️ Grilla Mensual", "📅 Grilla Semanal", "📋 Próximos 15 Días (Contraído)", "➕ Agendar Turno"]
        selected_mode = st.radio(
            "Modo de Vista",
            options=view_modes,
            index=view_modes.index(st.session_state.agenda_view_mode) if st.session_state.agenda_view_mode in view_modes else 0,
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state.agenda_view_mode = selected_mode

    with col_export:
        all_future_turnos = get_turnos(start_date=date.today())
        ics_data = generate_ics_content(all_future_turnos, clinic_name=clinic_name)
        st.download_button(
            label="📥 Exportar (.ics)",
            data=ics_data,
            file_name=f"turnos_kns_{date.today().strftime('%Y%m%d')}.ics",
            mime="text/calendar",
            help="Descargar calendario para importar a Google Calendar, Apple Calendar o Outlook",
            use_container_width=True
        )

    st.markdown("---")

    session_token = st.query_params.get("session_token", "")

    # ==============================================================================
    # MODO 1: 🗓️ GRILLA MENSUAL (TABLA 7 COLUMNAS INQUEBRANTABLE + INSPECTOR)
    # ==============================================================================
    if selected_mode == "🗓️ Grilla Mensual":
        cal_y = st.session_state.cal_year
        cal_m = st.session_state.cal_month

        # Navegación del Mes con Botones Nativos de Streamlit (Sin recarga de navegador ni pérdida de sesión)
        col_m_prev, col_m_title, col_m_next = st.columns([1, 2.2, 1])
        
        with col_m_prev:
            if st.button("◀ Anterior", use_container_width=True, key="btn_native_m_prev"):
                if cal_m == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()

        with col_m_title:
            st_html(f"<h3 style='text-align: center; margin: 4px 0; color: #38bdf8; font-size: 1.25rem; font-weight: 800;'>🗓️ {MESES_ES[cal_m]} {cal_y}</h3>")

        with col_m_next:
            if st.button("Siguiente ▶", use_container_width=True, key="btn_native_m_next"):
                if cal_m == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()

        num_days_in_month = calendar.monthrange(cal_y, cal_m)[1]
        start_month_date = date(cal_y, cal_m, 1)
        end_month_date = date(cal_y, cal_m, num_days_in_month)
        
        turnos_mes = get_turnos(start_date=start_month_date, end_date=end_month_date)
        
        turnos_por_dia: Dict[int, List[Dict[str, Any]]] = {}
        for t in turnos_mes:
            f_str = str(t.get("fecha", ""))
            try:
                t_dt = datetime.strptime(f_str, "%Y-%m-%d").date()
                if t_dt.month == cal_m and t_dt.year == cal_y:
                    turnos_por_dia.setdefault(t_dt.day, []).append(t)
            except Exception:
                pass

        # Renderizar Grilla HTML 7 columnas sin espacios indentados
        grid_html = generate_month_calendar_html(cal_y, cal_m, st.session_state.agenda_date, turnos_por_dia, session_token=session_token)
        st.html(grid_html)

        # Controles rápidos de fecha
        col_ctrl1, col_ctrl2 = st.columns([1.5, 2])
        with col_ctrl1:
            if st.button("⭐ Ir a Hoy", use_container_width=True, type="secondary"):
                st.session_state.agenda_date = date.today()
                st.session_state.cal_month = date.today().month
                st.session_state.cal_year = date.today().year
                st.rerun()
        with col_ctrl2:
            sel_d_input = st.date_input("Elegir fecha directamente", value=st.session_state.agenda_date, label_visibility="collapsed")
            if sel_d_input != st.session_state.agenda_date:
                st.session_state.agenda_date = sel_d_input
                st.session_state.cal_month = sel_d_input.month
                st.session_state.cal_year = sel_d_input.year
                st.rerun()

        # Detalle del día seleccionado
        st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
        render_day_turnos_detail(st.session_state.agenda_date, clinic_name=clinic_name, show_title=True)
        return

    # ==============================================================================
    # MODO 2: 📅 GRILLA SEMANAL (7 DÍAS HORIZONTALES + INSPECTOR)
    # ==============================================================================
    elif selected_mode == "📅 Grilla Semanal":
        current_date = st.session_state.agenda_date
        start_of_week = current_date - timedelta(days=current_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        col_w_prev, col_w_title, col_w_next = st.columns([1, 2.2, 1])
        
        with col_w_prev:
            if st.button("◀ Semana Ant.", use_container_width=True, key="btn_native_w_prev"):
                st.session_state.agenda_date -= timedelta(days=7)
                st.session_state.cal_month = st.session_state.agenda_date.month
                st.session_state.cal_year = st.session_state.agenda_date.year
                st.rerun()

        with col_w_title:
            st_html(f"<h4 style='text-align: center; margin: 4px 0; color: #38bdf8; font-size: 1.1rem;'>Semana: {start_of_week.strftime('%d/%m')} al {end_of_week.strftime('%d/%m')}</h4>")

        with col_w_next:
            if st.button("Semana Sig. ▶", use_container_width=True, key="btn_native_w_next"):
                st.session_state.agenda_date += timedelta(days=7)
                st.session_state.cal_month = st.session_state.agenda_date.month
                st.session_state.cal_year = st.session_state.agenda_date.year
                st.rerun()

        turnos_semana = get_turnos(start_date=start_of_week, end_date=end_of_week)
        turnos_semana_map: Dict[str, List[Dict[str, Any]]] = {}
        for t in turnos_semana:
            turnos_semana_map.setdefault(str(t.get("fecha", "")), []).append(t)

        # Renderizar Grilla Semanal HTML 7 columnas
        week_html = generate_week_calendar_html(start_of_week, current_date, turnos_semana_map, session_token=session_token)
        st.html(week_html)

        col_ctrl_w1, col_ctrl_w2 = st.columns([1.5, 2])
        with col_ctrl_w1:
            if st.button("⭐ Esta Semana", use_container_width=True, type="secondary"):
                st.session_state.agenda_date = date.today()
                st.session_state.cal_month = date.today().month
                st.session_state.cal_year = date.today().year
                st.rerun()
        with col_ctrl_w2:
            sel_w_input = st.date_input("Elegir fecha semanal", value=st.session_state.agenda_date, label_visibility="collapsed", key="picker_sem")
            if sel_w_input != st.session_state.agenda_date:
                st.session_state.agenda_date = sel_w_input
                st.session_state.cal_month = sel_w_input.month
                st.session_state.cal_year = sel_w_input.year
                st.rerun()

        # Detalle del día seleccionado
        st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
        render_day_turnos_detail(st.session_state.agenda_date, clinic_name=clinic_name, show_title=True)
        return

    # ==============================================================================
    # MODO 3: 📋 PRÓXIMOS 15 DÍAS (CONTRAÍDOS POR DEFECTO)
    # ==============================================================================
    elif selected_mode == "📋 Próximos 15 Días (Contraído)":
        hoy = date.today()
        hasta_15 = hoy + timedelta(days=15)
        
        turnos_15 = get_turnos(start_date=hoy, end_date=hasta_15)
        
        col_f_search, col_f_info = st.columns([3, 1.5])
        with col_f_search:
            filtro_nom = st.text_input("🔍 Filtrar por Paciente u Obra Social", placeholder="Ej: Menéndez o OSDE...", key="filtro_15d")
        with col_f_info:
            st_html(f"<div style='margin-top: 28px; font-weight: 700; color: #38bdf8;'>Total: {len(turnos_15)} turnos en 15 días</div>")

        if filtro_nom:
            turnos_15 = [t for t in turnos_15 if filtro_nom.lower() in t.get("paciente_nombre", "").lower() or filtro_nom.lower() in t.get("paciente_obra_social", "").lower()]

        if not turnos_15:
            st.info("No hay turnos agendados en los próximos 15 días.")
        else:
            turnos_agrupados: Dict[str, List[Dict[str, Any]]] = {}
            for t in turnos_15:
                turnos_agrupados.setdefault(t.get("fecha", ""), []).append(t)

            st.caption("Haz clic en cualquier día para desplegar sus turnos:")

            for f_str, lista_t in sorted(turnos_agrupados.items()):
                try:
                    f_dt = datetime.strptime(f_str, "%Y-%m-%d").date()
                    d_idx = f_dt.weekday()
                    dia_nombre = DIAS_COMPLETOS_ES[d_idx]
                    f_formateada = f_dt.strftime("%d/%m/%Y")
                    dias_dif = (f_dt - hoy).days
                    dias_txt = "Hoy" if dias_dif == 0 else "Mañana" if dias_dif == 1 else f"En {dias_dif} días"
                except Exception:
                    dia_nombre = ""
                    f_formateada = f_str
                    dias_txt = ""

                is_today = (dias_dif == 0)
                expander_title = f"🗓️ {dia_nombre} {f_formateada} — {len(lista_t)} turno(s) ({dias_txt})"

                with st.expander(expander_title, expanded=is_today):
                    for t in lista_t:
                        t_id = str(t.get("id"))
                        p_nom = t.get("paciente_nombre", "Paciente")
                        p_tel = t.get("paciente_telefono", "")
                        p_os = t.get("paciente_obra_social", "Particular")
                        h_ini = str(t.get("hora_inicio", ""))[:5]
                        h_fin = str(t.get("hora_fin", ""))[:5]
                        dur = t.get("duracion_minutos", 45)
                        estado = t.get("estado", "Pendiente")
                        
                        gcal_url = generate_turno_google_url(t, clinic_name=clinic_name)
                        wa_msg = template_recordatorio_turno(p_nom, f_formateada, h_ini, consultorio=clinic_name, gcal_url=gcal_url)
                        wa_url = generate_whatsapp_url(p_tel, wa_msg)

                        st_html(
                            f"""
                            <div class="kns-card" style="margin-bottom: 6px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                    <div>
                                        <b style="font-size: 1.05rem; color: #f8fafc;">⏰ {h_ini} a {h_fin} hs</b> <span style="font-size: 0.82rem; color: #94a3b8;">({dur} min)</span>
                                        <h4 style="margin: 2px 0; color: #38bdf8;">👤 {p_nom}</h4>
                                        <span style="font-size: 0.85rem; color: #cbd5e1;">🏥 {p_os} | 📞 {p_tel or 'S/Tel'}</span>
                                    </div>
                                    <div>
                                        {render_status_badge(estado)}
                                    </div>
                                </div>
                            </div>
                            """
                        )
                        c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 1.5])
                        with c_act1:
                            st_html(f'<a href="{wa_url}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;">📲 WhatsApp</a>')
                        with c_act2:
                            st_html(f'<a href="{gcal_url}" target="_blank" class="btn-gcal" style="width: 100%; text-align: center; justify-content: center;">📅 Google Calendar</a>')
                        with c_act3:
                            if st.button("👉 Abrir Jornada", key=f"btn_goto_15_{t_id}", use_container_width=True):
                                try:
                                    st.session_state.agenda_date = datetime.strptime(f_str, "%Y-%m-%d").date()
                                    st.session_state.agenda_view_mode = "🗓️ Grilla Mensual"
                                    st.rerun()
                                except Exception:
                                    pass
                        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
        return

    # ==============================================================================
    # MODO 4: ➕ AGENDAR NUEVO TURNO (CARGA RÁPIDA + LINK DE FICHA O PACIENTE EXISTENTE)
    # ==============================================================================
    elif selected_mode == "➕ Agendar Turno":
        st.markdown("#### Agendar Turno Kinesiológico")
        st.caption("Podés hacer una carga rápida con Nombre y WhatsApp para enviarle el link de alta al paciente, o agendar para un paciente ya existente:")

        # Si recién se agendó un turno, mostrar tarjeta de acciones rápidas WhatsApp
        if "reciente_turno_agendado" in st.session_state and st.session_state.reciente_turno_agendado:
            rec = st.session_state.reciente_turno_agendado
            st_html(
                f"""
                <div style="background: linear-gradient(135deg, rgba(2, 132, 199, 0.15), rgba(14, 165, 233, 0.25)); border: 2px solid #0284c7; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h4 style="margin: 0; color: #38bdf8;">✅ ¡Turno agendado para {rec.get('nombre')}!</h4>
                            <div style="font-size: 0.9rem; color: #e2e8f0; margin-top: 4px;">
                                🗓️ <b>{rec.get('fecha_str')}</b> a las <b>{rec.get('hora_str')} hs</b> | 📞 {rec.get('telefono') or 'Sin teléfono'}
                            </div>
                        </div>
                    </div>
                </div>
                """
            )
            col_rec1, col_rec2, col_rec3 = st.columns([2, 2, 1.2])
            with col_rec1:
                st_html(f'<a href="{rec.get("wa_url")}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;">📲 Enviar Link y Confirmación por WhatsApp</a>')
            with col_rec2:
                st_html(f'<a href="{rec.get("gcal_url")}" target="_blank" class="btn-gcal" style="width: 100%; text-align: center; justify-content: center;">📅 Añadir a Google Calendar</a>')
            with col_rec3:
                if st.button("✓ Listo / Cerrar", key="btn_close_reciente", use_container_width=True):
                    del st.session_state["reciente_turno_agendado"]
                    st.rerun()

            if rec.get("reg_link"):
                st.markdown(f"**Enlace de alta directa para el paciente:**")
                st.code(rec["reg_link"], language="text")
            st.markdown("---")

        tab_rapida, tab_existente = st.tabs([
            "⚡ Carga Rápida + Enviar Link de Ficha por WhatsApp",
            "👤 Seleccionar Paciente ya Registrado"
        ])

        # TAB 1: CARGA RÁPIDA (NOMBRE + TELÉFONO + FECHA/HORA + LINK WHATSAPP)
        with tab_rapida:
            st.markdown("##### ⚡ Agendar solo con Nombre y WhatsApp")
            st.caption("Cargás los datos esenciales del turno y el paciente completará el resto (DNI, Obra Social, Domicilio y foto de su Pedido Médico) mediante el enlace que le envíes por WhatsApp.")
            
            with st.form("form_nuevo_turno_rapido", clear_on_submit=False):
                col_r_nom, col_r_tel = st.columns([2, 1.5])
                with col_r_nom:
                    rapido_nombre = st.text_input("Nombre y Apellido del Paciente *", placeholder="Ej: Perez, Juan")
                with col_r_tel:
                    rapido_tel = st.text_input("Celular / WhatsApp *", placeholder="Ej: +54 9 11 1234-5678")

                col_r_f, col_r_h, col_r_dur = st.columns([1.5, 1.2, 1.2])
                with col_r_f:
                    rapido_fecha = st.date_input("Fecha del Turno *", value=st.session_state.agenda_date, key="rapido_f_in")
                with col_r_h:
                    rapido_hora = st.time_input("Hora de Inicio *", value=time(8, 30), key="rapido_h_in")
                with col_r_dur:
                    rapido_dur = st.selectbox("Duración (min)", [30, 45, 60], index=1, key="rapido_dur_in")

                rapido_dt_fin = datetime.combine(rapido_fecha, rapido_hora) + timedelta(minutes=rapido_dur)
                rapido_h_fin = rapido_dt_fin.time()

                col_r_os, col_r_cos = st.columns([2, 1.5])
                with col_r_os:
                    rapido_os = st.text_input("Obra Social / Cobertura (Opcional)", value="Particular", placeholder="Ej: OSDE, Swiss Medical, Particular...")
                with col_r_cos:
                    rapido_cos = st.number_input("Monto Coseguro / Sesión ($)", min_value=0.0, step=500.0, value=4000.0)

                rapido_notas = st.text_input("Motivo de Consulta / Notas", placeholder="Ej: Dolor rodilla derecha post-partido")

                btn_agendar_rapido = st.form_submit_button("📅 Agendar Turno y Generar Link para WhatsApp", type="primary", use_container_width=True)

                if btn_agendar_rapido:
                    if not rapido_nombre.strip():
                        st.error("El nombre y apellido son obligatorios.")
                    elif not rapido_tel.strip():
                        st.error("El teléfono / WhatsApp es obligatorio para enviar el formulario.")
                    else:
                        h_ini_m = rapido_hora.hour * 60 + rapido_hora.minute
                        h_fin_m = rapido_h_fin.hour * 60 + rapido_h_fin.minute

                        if h_ini_m < WORK_START_HOUR * 60 or h_fin_m > WORK_END_HOUR * 60:
                            st.error(f"El turno debe estar dentro del horario de atención ({WORK_START_HOUR}:00 a {WORK_END_HOUR}:00 hs).")
                        else:
                            is_valid, _, overlap_msg = check_turnos_overlap(
                                target_date=rapido_fecha,
                                hora_inicio=rapido_hora,
                                hora_fin=rapido_h_fin
                            )
                            if not is_valid:
                                st.error(f"❌ {overlap_msg}")
                            else:
                                # 1. Crear o buscar paciente rápido
                                ok_p, msg_p, created_p = create_paciente({
                                    "nombre_completo": rapido_nombre.strip(),
                                    "telefono": rapido_tel.strip(),
                                    "obra_social": rapido_os.strip() or "Particular",
                                    "monto_coseguro_default": float(rapido_cos),
                                    "patologia": rapido_notas.strip(),
                                    "ficha_completada": False,
                                    "activo": True
                                })
                                if not ok_p or not created_p:
                                    st.error(f"Error al registrar paciente: {msg_p}")
                                else:
                                    paciente_id_created = created_p["id"]
                                    # 2. Crear turno
                                    ok_t, msg_t, created_t = create_turno({
                                        "paciente_id": paciente_id_created,
                                        "fecha": rapido_fecha.isoformat(),
                                        "hora_inicio": rapido_hora,
                                        "hora_fin": rapido_h_fin,
                                        "duracion_minutos": rapido_dur,
                                        "estado": "Pendiente",
                                        "monto_coseguro": float(rapido_cos),
                                        "estado_pago": "Pendiente",
                                        "notas": rapido_notas
                                    })
                                    if not ok_t or not created_t:
                                        st.error(f"Error al crear turno: {msg_t}")
                                    else:
                                        # 3. Generar token de registro y URLs
                                        reg_token_obj = create_registration_token(
                                            paciente_id=paciente_id_created,
                                            turno_id=created_t.get("id"),
                                            nombre_inicial=rapido_nombre.strip(),
                                            telefono_inicial=rapido_tel.strip()
                                        )
                                        f_formateada = rapido_fecha.strftime('%d/%m/%Y')
                                        h_formateada = rapido_hora.strftime('%H:%M')
                                        
                                        reg_link_str = generate_registration_link(reg_token_obj["token"])
                                        wa_url_rapido = generate_registration_whatsapp_url(
                                            phone=rapido_tel.strip(),
                                            paciente_nombre=rapido_nombre.strip(),
                                            token=reg_token_obj["token"],
                                            turno_fecha=f_formateada,
                                            turno_hora=h_formateada,
                                            clinic_name=clinic_name
                                        )
                                        
                                        turno_gcal_data = {
                                            "fecha": rapido_fecha.isoformat(),
                                            "hora_inicio": rapido_hora,
                                            "hora_fin": rapido_h_fin,
                                            "paciente_nombre": rapido_nombre.strip(),
                                            "paciente_obra_social": rapido_os.strip() or "Particular",
                                            "notas": rapido_notas
                                        }
                                        gcal_url_rapido = generate_turno_google_url(turno_gcal_data, clinic_name=clinic_name)

                                        st.session_state.reciente_turno_agendado = {
                                            "nombre": rapido_nombre.strip(),
                                            "telefono": rapido_tel.strip(),
                                            "fecha_str": f_formateada,
                                            "hora_str": h_formateada,
                                            "wa_url": wa_url_rapido,
                                            "gcal_url": gcal_url_rapido,
                                            "reg_link": reg_link_str
                                        }
                                        st.session_state.agenda_date = rapido_fecha
                                        st.rerun()

        # TAB 2: PACIENTE REGISTRADO EXISTENTE
        with tab_existente:
            pacientes_list = get_pacientes(activo_only=True)
            if not pacientes_list:
                st.info("No hay pacientes registrados aún. Podés usar la pestaña 'Carga Rápida' arriba para agendar tu primer turno.")
            else:
                with st.form("form_nuevo_turno_direct", clear_on_submit=False):
                    col_f_ag1, col_f_ag2 = st.columns([1.5, 2])
                    with col_f_ag1:
                        fecha_turno_sel = st.date_input("Fecha del Turno *", value=st.session_state.agenda_date, key="dir_f_in")
                    with col_f_ag2:
                        paciente_options = {p["nombre_completo"]: p["id"] for p in pacientes_list}
                        nombre_sel = st.selectbox("Seleccionar Paciente *", list(paciente_options.keys()))
                        paciente_id_sel = paciente_options[nombre_sel]

                    paciente_obj = next((p for p in pacientes_list if p["id"] == paciente_id_sel), {})
                    p_os_actual = paciente_obj.get('obra_social', 'Particular') if paciente_obj else 'Particular'
                    p_cos_default = float(paciente_obj.get('monto_coseguro_default', 0) or 0) if paciente_obj else 0.0
                    is_part_ag = (str(p_os_actual).lower().strip() == 'particular')

                    if paciente_obj:
                        ses_r = paciente_obj.get("sesiones_realizadas", 0)
                        ses_t = paciente_obj.get("sesiones_totales", 10)
                        restantes = max(0, ses_t - ses_r)
                        st.markdown(
                            f"📋 **Cobertura:** {'👤 Particular' if is_part_ag else f'🏥 {p_os_actual}'} | "
                            f"💵 **{'Valor Sesión:' if is_part_ag else 'Coseguro:'}** ${p_cos_default:,.2f} | "
                            f"🎟️ **Sesiones Restantes:** {restantes} de {ses_t}"
                        )

                    col_h1, col_h2, col_cos = st.columns([1.2, 1.2, 1.6])
                    with col_h1:
                        hora_inicio_sel = st.time_input("Hora de Inicio", value=time(8, 30), key="dir_h_in")
                    with col_h2:
                        duracion_sel = st.selectbox("Duración de la Sesión", [30, 45, 60], index=1, key="dir_dur_in")
                    with col_cos:
                        lbl_monto_ag = "Valor Sesión ($)" if is_part_ag else "Monto Coseguro ($)"
                        monto_coseguro_turno = st.number_input(
                            lbl_monto_ag,
                            min_value=0.0,
                            step=500.0,
                            value=p_cos_default,
                            help="Monto de cobro manual para esta sesión."
                        )
                    
                    dt_temp = datetime.combine(fecha_turno_sel, hora_inicio_sel) + timedelta(minutes=duracion_sel)
                    hora_fin_calc = dt_temp.time()

                    col_n1, col_n2 = st.columns([2, 1])
                    with col_n1:
                        turno_notas = st.text_input("Tratamiento previsto / Notas", placeholder="Ej: Fisioterapia + ejercicios McKenzie")
                    with col_n2:
                        turno_estado_ini = st.selectbox("Estado Inicial", ["Pendiente", "Asistió"])

                    btn_agendar = st.form_submit_button("📅 Confirmar y Agendar Turno", type="primary", use_container_width=True)

                    if btn_agendar:
                        h_ini_val = hora_inicio_sel.hour * 60 + hora_inicio_sel.minute
                        h_fin_val = hora_fin_calc.hour * 60 + hora_fin_calc.minute

                        if h_ini_val < WORK_START_HOUR * 60 or h_fin_val > WORK_END_HOUR * 60:
                            st.error(f"El turno debe estar dentro del horario de atención ({WORK_START_HOUR}:00 a {WORK_END_HOUR}:00 hs).")
                        else:
                            is_valid, count_overlap, overlap_msg = check_turnos_overlap(
                                target_date=fecha_turno_sel,
                                hora_inicio=hora_inicio_sel,
                                hora_fin=hora_fin_calc
                            )

                            if not is_valid:
                                st.error(f"❌ {overlap_msg}")
                            else:
                                ok, msg, new_turno = create_turno({
                                    "paciente_id": paciente_id_sel,
                                    "fecha": fecha_turno_sel.isoformat(),
                                    "hora_inicio": hora_inicio_sel,
                                    "hora_fin": hora_fin_calc,
                                    "duracion_minutos": duracion_sel,
                                    "estado": turno_estado_ini,
                                    "monto_coseguro": float(monto_coseguro_turno),
                                    "estado_pago": "Pendiente",
                                    "notas": turno_notas
                                })

                                if ok:
                                    f_formateada = fecha_turno_sel.strftime('%d/%m/%Y')
                                    h_formateada = hora_inicio_sel.strftime('%H:%M')
                                    tel_p = paciente_obj.get("telefono", "")
                                    
                                    turno_data_for_gcal = {
                                        "fecha": fecha_turno_sel.isoformat(),
                                        "hora_inicio": hora_inicio_sel,
                                        "hora_fin": hora_fin_calc,
                                        "paciente_nombre": nombre_sel,
                                        "paciente_obra_social": paciente_obj.get("obra_social", "Particular"),
                                        "notas": turno_notas
                                    }
                                    gcal_url_new = generate_turno_google_url(turno_data_for_gcal, clinic_name=clinic_name)
                                    
                                    reg_tok_ex = create_registration_token(paciente_id_sel, new_turno.get("id"), nombre_sel, tel_p)
                                    reg_link_ex = generate_registration_link(reg_tok_ex["token"])
                                    
                                    wa_conf = template_confirmacion_turno_con_link(
                                        nombre_paciente=nombre_sel,
                                        fecha_str=f_formateada,
                                        hora_str=h_formateada,
                                        duracion_minutos=duracion_sel,
                                        registro_link=reg_link_ex if not paciente_obj.get("ficha_completada") else None,
                                        consultorio=clinic_name,
                                        gcal_url=gcal_url_new
                                    )
                                    url_conf = generate_whatsapp_url(tel_p, wa_conf)
                                    
                                    st.session_state.reciente_turno_agendado = {
                                        "nombre": nombre_sel,
                                        "telefono": tel_p,
                                        "fecha_str": f_formateada,
                                        "hora_str": h_formateada,
                                        "wa_url": url_conf,
                                        "gcal_url": gcal_url_new,
                                        "reg_link": reg_link_ex if not paciente_obj.get("ficha_completada") else None
                                    }
                                    st.session_state.agenda_date = fecha_turno_sel
                                    st.rerun()
                                else:
                                    st.error(f"Error al agendar turno: {msg}")
