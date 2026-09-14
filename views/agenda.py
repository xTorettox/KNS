"""
Vista de Agenda y Gestión de Turnos (Mobile-First y Vista Mensual).
Permite gestionar turnos diarios de 08:00 a 15:00 hs (máx 2 simultáneos),
explorar el calendario mensual completo para agendar a futuro (15+ días),
y sincronizar con Google Calendar e iCal (.ics).
"""
import streamlit as st
import calendar
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any

from utils.supabase_client import (
    get_turnos,
    get_pacientes,
    create_turno,
    update_turno,
    delete_turno,
    check_turnos_overlap,
    create_evolucion,
    get_app_config
)
from utils.whatsapp import (
    generate_whatsapp_url,
    template_recordatorio_turno,
    template_confirmacion_turno,
    template_reprogramacion_turno
)
from utils.google_calendar import (
    generate_google_calendar_url,
    generate_turno_google_url,
    generate_ics_content
)
from utils.ui import (
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

def render_agenda_view():
    """Renderiza la vista principal de la agenda kinesiológica con modos Diario, Mensual y Próximos."""
    app_config = get_app_config()
    clinic_name = app_config.get("clinic_name", "KNS Kinesiología")

    # ==============================================================================
    # SELECTOR DE MODO DE VISTA (DIARIA / MENSUAL / PRÓXIMOS TURNOS)
    # ==============================================================================
    if "agenda_view_mode" not in st.session_state:
        st.session_state.agenda_view_mode = "📅 Vista Diaria"
        
    if "agenda_date" not in st.session_state:
        st.session_state.agenda_date = date.today()

    if "cal_month" not in st.session_state:
        st.session_state.cal_month = st.session_state.agenda_date.month
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = st.session_state.agenda_date.year

    render_header("Agenda de Turnos", "Gestión de turnos de 08:00 a 15:00 hs (Máximo 2 simultáneos) y sincronización con Google Calendar", icon="📅")

    # Selector de Modo de Vista
    col_mode, col_export = st.columns([3, 1.2])
    with col_mode:
        view_modes = ["📅 Vista Diaria", "🗓️ Vista Mensual (Calendario)", "📋 Próximos Turnos (30 días)"]
        selected_mode = st.radio(
            "Modo de Vista",
            options=view_modes,
            index=view_modes.index(st.session_state.agenda_view_mode) if st.session_state.agenda_view_mode in view_modes else 0,
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state.agenda_view_mode = selected_mode

    with col_export:
        # Botón de exportación .ics
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

    # ==============================================================================
    # MODO 1: 🗓️ VISTA MENSUAL (CALENDARIO COMPLETO)
    # ==============================================================================
    if selected_mode == "🗓️ Vista Mensual (Calendario)":
        cal_y = st.session_state.cal_year
        cal_m = st.session_state.cal_month

        # Barra de navegación del mes
        col_m_prev, col_m_title, col_m_next, col_m_today = st.columns([1, 2.5, 1, 1.2])
        
        with col_m_prev:
            if st.button("◀ Mes Anterior", use_container_width=True):
                if cal_m == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()

        with col_m_title:
            st.markdown(
                f"<h3 style='text-align: center; margin: 0; color: #38bdf8;'>🗓️ {MESES_ES[cal_m]} {cal_y}</h3>",
                unsafe_allow_html=True
            )

        with col_m_next:
            if st.button("Mes Siguiente ▶", use_container_width=True):
                if cal_m == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()

        with col_m_today:
            if st.button("📅 Mes Actual", use_container_width=True, type="secondary"):
                st.session_state.cal_month = date.today().month
                st.session_state.cal_year = date.today().year
                st.rerun()

        # Obtener todos los turnos del mes
        num_days_in_month = calendar.monthrange(cal_y, cal_m)[1]
        start_month_date = date(cal_y, cal_m, 1)
        end_month_date = date(cal_y, cal_m, num_days_in_month)
        
        turnos_mes = get_turnos(start_date=start_month_date, end_date=end_month_date)
        
        # Agrupar turnos por día
        turnos_por_dia: Dict[int, List[Dict[str, Any]]] = {}
        for t in turnos_mes:
            f_str = str(t.get("fecha", ""))
            try:
                t_dt = datetime.strptime(f_str, "%Y-%m-%d").date()
                if t_dt.month == cal_m and t_dt.year == cal_y:
                    turnos_por_dia.setdefault(t_dt.day, []).append(t)
            except Exception:
                pass

        st.caption("Toca cualquier día para saltar a su agenda o agendar un turno:")

        # Encabezados de días de la semana
        cols_headers = st.columns(7)
        for i, nom_dia in enumerate(DIAS_ES):
            with cols_headers[i]:
                st.markdown(f"<div style='text-align: center; font-weight: 800; color: #94a3b8; font-size: 0.85rem; padding: 4px;'>{nom_dia}</div>", unsafe_allow_html=True)

        # Matriz de semanas
        month_matrix = calendar.monthcalendar(cal_y, cal_m)
        today = date.today()

        for week in month_matrix:
            cols_week = st.columns(7)
            for day_idx, day_num in enumerate(week):
                with cols_week[day_idx]:
                    if day_num == 0:
                        st.markdown("<div style='min-height: 60px; background: rgba(15,23,42,0.3); border-radius: 8px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)
                    else:
                        d_date = date(cal_y, cal_m, day_num)
                        is_today = (d_date == today)
                        is_selected = (d_date == st.session_state.agenda_date)
                        turnos_d = turnos_por_dia.get(day_num, [])
                        cant_turnos = len(turnos_d)
                        
                        # Estilo del indicador
                        if cant_turnos == 0:
                            badge_html = "<span style='color: #64748b; font-size: 0.72rem;'>0 turnos</span>"
                        elif cant_turnos < 4:
                            badge_html = f"<span style='color: #38bdf8; font-weight: 700; font-size: 0.75rem; background: rgba(56,189,248,0.15); padding: 1px 5px; border-radius: 4px;'>{cant_turnos} turnos</span>"
                        else:
                            badge_html = f"<span style='color: #facc15; font-weight: 700; font-size: 0.75rem; background: rgba(250,204,21,0.15); padding: 1px 5px; border-radius: 4px;'>{cant_turnos} turnos</span>"

                        border_style = "2px solid #38bdf8" if is_today else "2px solid #4ade80" if is_selected else "1px solid rgba(255,255,255,0.08)"
                        bg_style = "rgba(56,189,248,0.1)" if is_today else "#1e293b"

                        st.markdown(
                            f"""
                            <div style="background: {bg_style}; border: {border_style}; border-radius: 8px; padding: 6px 2px; text-align: center; margin-bottom: 4px;">
                                <div style="font-weight: 800; font-size: 0.95rem; color: {'#38bdf8' if is_today else '#f8fafc'};">{day_num}</div>
                                <div>{badge_html}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        btn_label = "📍 Ir" if not is_today else "⭐ Hoy"
                        if st.button(btn_label, key=f"btn_cal_day_{cal_y}_{cal_m}_{day_num}", use_container_width=True):
                            st.session_state.agenda_date = d_date
                            st.session_state.agenda_view_mode = "📅 Vista Diaria"
                            st.rerun()

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        return

    # ==============================================================================
    # MODO 2: 📋 PRÓXIMOS TURNOS (30 DÍAS)
    # ==============================================================================
    elif selected_mode == "📋 Próximos Turnos (30 días)":
        hoy = date.today()
        hasta_30 = hoy + timedelta(days=30)
        
        turnos_futuros = get_turnos(start_date=hoy, end_date=hasta_30)
        
        col_f_search, col_f_info = st.columns([3, 1.5])
        with col_f_search:
            filtro_nom = st.text_input("🔍 Buscar en próximos turnos por paciente u obra social", placeholder="Ej: Florencia...")
        with col_f_info:
            st.markdown(f"<div style='margin-top: 28px; font-weight: 700; color: #38bdf8;'>Total: {len(turnos_futuros)} turnos agendados</div>", unsafe_allow_html=True)

        if filtro_nom:
            turnos_futuros = [t for t in turnos_futuros if filtro_nom.lower() in t.get("paciente_nombre", "").lower() or filtro_nom.lower() in t.get("paciente_obra_social", "").lower()]

        if not turnos_futuros:
            st.info("No hay turnos agendados en los próximos 30 días.")
        else:
            # Agrupar por fecha
            turnos_agrupados: Dict[str, List[Dict[str, Any]]] = {}
            for t in turnos_futuros:
                turnos_agrupados.setdefault(t.get("fecha", ""), []).append(t)

            for f_str, lista_t in sorted(turnos_agrupados.items()):
                try:
                    f_dt = datetime.strptime(f_str, "%Y-%m-%d").date()
                    f_formateada = f_dt.strftime("%d/%m/%Y")
                    dias_dif = (f_dt - hoy).days
                    dias_txt = "Hoy" if dias_dif == 0 else "Mañana" if dias_dif == 1 else f"En {dias_dif} días"
                except Exception:
                    f_formateada = f_str
                    dias_txt = ""

                st.markdown(f"##### 🗓️ {f_formateada} — <span style='color: #38bdf8;'>{dias_txt}</span> ({len(lista_t)} turnos)", unsafe_allow_html=True)

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

                    with st.container():
                        st.markdown(
                            f"""
                            <div class="kns-card" style="margin-bottom: 8px;">
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
                            """,
                            unsafe_allow_html=True
                        )
                        c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 1.5])
                        with c_act1:
                            st.markdown(f'<a href="{wa_url}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;">📲 WhatsApp</a>', unsafe_allow_html=True)
                        with c_act2:
                            st.markdown(f'<a href="{gcal_url}" target="_blank" class="btn-gcal" style="width: 100%; text-align: center; justify-content: center;">📅 Google Calendar</a>', unsafe_allow_html=True)
                        with c_act3:
                            if st.button("👉 Ir a esta Jornada", key=f"btn_goto_{t_id}", use_container_width=True):
                                try:
                                    st.session_state.agenda_date = datetime.strptime(f_str, "%Y-%m-%d").date()
                                    st.session_state.agenda_view_mode = "📅 Vista Diaria"
                                    st.rerun()
                                except Exception:
                                    pass
                        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
        return

    # ==============================================================================
    # MODO 3: 📅 VISTA DIARIA (GESTIÓN HORARIA Y ASISTENCIA)
    # ==============================================================================
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1.2, 1.2, 2.5, 1.8])

    with col_nav1:
        if st.button("◀ Día Anterior", use_container_width=True):
            st.session_state.agenda_date -= timedelta(days=1)
            st.session_state.cal_month = st.session_state.agenda_date.month
            st.session_state.cal_year = st.session_state.agenda_date.year
            st.rerun()

    with col_nav2:
        if st.button("Día Siguiente ▶", use_container_width=True):
            st.session_state.agenda_date += timedelta(days=1)
            st.session_state.cal_month = st.session_state.agenda_date.month
            st.session_state.cal_year = st.session_state.agenda_date.year
            st.rerun()

    with col_nav3:
        selected_date = st.date_input(
            "Seleccionar Fecha",
            value=st.session_state.agenda_date,
            label_visibility="collapsed"
        )
        if selected_date != st.session_state.agenda_date:
            st.session_state.agenda_date = selected_date
            st.session_state.cal_month = selected_date.month
            st.session_state.cal_year = selected_date.year
            st.rerun()

    with col_nav4:
        if st.button("📅 Ir a Hoy", use_container_width=True, type="secondary"):
            st.session_state.agenda_date = date.today()
            st.session_state.cal_month = date.today().month
            st.session_state.cal_year = date.today().year
            st.rerun()

    current_date = st.session_state.agenda_date
    current_date_str = current_date.strftime("%d/%m/%Y")
    
    # Obtener turnos del día
    turnos_dia = get_turnos(target_date=current_date)
    pacientes_list = get_pacientes(activo_only=True)

    # Resumen métrico
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
    # PESTAÑAS: TURNOS DEL DÍA / AGENDAR NUEVO TURNO / MATRIZ DE OCUPACIÓN
    # ==============================================================================
    tab_turnos, tab_nuevo_turno, tab_matriz = st.tabs(["📋 Turnos del Día", "➕ Agendar Nuevo Turno", "📊 Ocupación Horaria (08:00 - 15:00)"])

    # ------------------------------------------------------------------------------
    # TAB 1: LISTADO DE TURNOS DEL DÍA CON GOOGLE CALENDAR Y WHATSAPP
    # ------------------------------------------------------------------------------
    with tab_turnos:
        if not turnos_dia:
            st.info(f"No hay turnos programados para el día **{current_date_str}**. ¡Utiliza la pestaña 'Agendar Nuevo Turno' para agendar a cualquier paciente!")
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

                # Enlace de Google Calendar
                gcal_url_t = generate_turno_google_url(turno, clinic_name=clinic_name)

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

                    c_det1, c_det2, c_det3, c_det4, c_det5 = st.columns([2, 1.4, 1.4, 1.3, 1.3])
                    
                    # 1. Indicador de sesiones y notas
                    with c_det1:
                        st.markdown(render_session_progress(ses_real, ses_tot), unsafe_allow_html=True)
                        if notas:
                            st.caption(f"📝 *Notas:* {notas}")
                        if motivo_ajuste:
                            st.caption(f"⏱ *Ajuste:* {motivo_ajuste}")

                    # 2. Botón WhatsApp Directo (con link de Google Calendar)
                    with c_det2:
                        msg_wa = template_recordatorio_turno(p_nombre, current_date_str, h_ini, consultorio=clinic_name, gcal_url=gcal_url_t)
                        wa_url = generate_whatsapp_url(p_tel, msg_wa)
                        st.markdown(
                            f'<a href="{wa_url}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;">📲 WhatsApp</a>',
                            unsafe_allow_html=True
                        )

                    # 3. Botón 1-Clic Google Calendar
                    with c_det3:
                        st.markdown(
                            f'<a href="{gcal_url_t}" target="_blank" class="btn-gcal" style="width: 100%; text-align: center; justify-content: center;">📅 Google Cal</a>',
                            unsafe_allow_html=True
                        )

                    # 4. Cambio rápido de estado
                    with c_det4:
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
                                st.toast(f"Estado actualizado a '{nuevo_estado}'", icon="✅")
                                st.rerun()
                            else:
                                st.error(msg)

                    # 5. Edición / Ajuste
                    with c_det5:
                        with st.popover("⚙️ Ajustar", use_container_width=True):
                            st.markdown("##### Ajustar Horario o Notas")
                            
                            curr_h_ini_obj = datetime.strptime(h_ini, "%H:%M").time()
                            nuevo_h_ini = st.time_input("Nueva Hora Inicio", value=curr_h_ini_obj, key=f"edit_hi_{t_id}")
                            
                            dur_opts = [30, 45, 60]
                            idx_dur = dur_opts.index(dur) if dur in dur_opts else 1
                            nueva_dur = st.selectbox("Duración (min)", dur_opts, index=idx_dur, key=f"edit_dur_{t_id}")
                            
                            dummy_dt = datetime.combine(date.today(), nuevo_h_ini) + timedelta(minutes=nueva_dur)
                            nuevo_h_fin = dummy_dt.time()
                            st.info(f"Hora de fin: **{nuevo_h_fin.strftime('%H:%M')} hs**")
                            
                            nuevo_motivo = st.text_input("Motivo del ajuste", value=motivo_ajuste, placeholder="Ej: Llegó 15 min tarde", key=f"edit_mot_{t_id}")
                            nuevas_notas = st.text_area("Notas del turno", value=notas, key=f"edit_not_{t_id}")
                            
                            col_save, col_del = st.columns(2)
                            with col_save:
                                if st.button("Guardar", key=f"btn_save_{t_id}", type="primary", use_container_width=True):
                                    ok, msg = update_turno(t_id, {
                                        "hora_inicio": nuevo_h_ini,
                                        "hora_fin": nuevo_h_fin,
                                        "duracion_minutos": nueva_dur,
                                        "motivo_ajuste": nuevo_motivo,
                                        "notas": nuevas_notas
                                    })
                                    if ok:
                                        st.success("Turno actualizado.")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            
                            with col_del:
                                if st.button("Eliminar", key=f"btn_del_{t_id}", type="secondary", use_container_width=True):
                                    delete_turno(t_id)
                                    st.warning("Turno eliminado.")
                                    st.rerun()

                    # Opción para registrar evolución si asistió
                    if estado == "Asistió":
                        with st.expander(f"🩺 Registrar Evolución de la Sesión para {p_nombre}"):
                            with st.form(key=f"quick_evol_form_{t_id}"):
                                col_ev1, col_ev2 = st.columns([3, 1])
                                with col_ev1:
                                    quick_nota = st.text_area("Nota Clínica / Evolución", placeholder="Ej: Paciente refiere mejoría en la marcha. Se realizó movilización pasiva...")
                                    quick_trat = st.text_input("Tratamiento Aplicado", placeholder="Ej: TENS + Crioterapia + Ejercicios de fortalecimiento")
                                Coin_ev2 = col_ev2
                                with Coin_ev2:
                                    quick_eva = st.slider("Escala de Dolor (EVA 0-10)", 0, 10, 4)
                                
                                submit_evol = st.form_submit_button("Guardar en Historial Clínico", type="primary", use_container_width=True)
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
                                            st.success("¡Evolución guardada exitosamente!")
                                        else:
                                            st.error(msg_ev)
                                    else:
                                        st.warning("Ingresa la nota clínica para registrar la evolución.")

                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------------------
    # TAB 2: AGENDAR NUEVO TURNO (CON SELECTOR DE FECHA DIRECTO)
    # ------------------------------------------------------------------------------
    with tab_nuevo_turno:
        st.markdown("#### Agendar Turno Kinesiológico")
        st.caption("Puedes agendar para hoy o seleccionar cualquier fecha futura (15, 30 días, etc.) directamente:")

        if not pacientes_list:
            st.warning("No hay pacientes activos registrados. Por favor, crea un paciente primero en la sección 'Pacientes'.")
        else:
            with st.form("form_nuevo_turno", clear_on_submit=False):
                # Selector explícito de fecha del turno
                col_f_ag1, col_f_ag2 = st.columns([1.5, 2])
                with col_f_ag1:
                    fecha_turno_sel = st.date_input("Fecha del Turno *", value=current_date)
                with col_f_ag2:
                    paciente_options = {p["nombre_completo"]: p["id"] for p in pacientes_list}
                    nombre_sel = st.selectbox("Seleccionar Paciente *", list(paciente_options.keys()))
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

                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hora_inicio_sel = st.time_input("Hora de Inicio", value=time(8, 30))
                with col_h2:
                    duracion_sel = st.selectbox("Duración de la Sesión", [30, 45, 60], index=1)
                
                # Calcular hora fin
                dt_temp = datetime.combine(fecha_turno_sel, hora_inicio_sel) + timedelta(minutes=duracion_sel)
                hora_fin_calc = dt_temp.time()

                st.markdown(
                    f"""
                    <div style="background-color: rgba(2, 132, 199, 0.1); border-left: 4px solid #0284c7; padding: 10px; border-radius: 6px; margin: 10px 0;">
                        <b>Resumen:</b> {fecha_turno_sel.strftime('%d/%m/%Y')} | {hora_inicio_sel.strftime('%H:%M')} hs ➔ {hora_fin_calc.strftime('%H:%M')} hs ({duracion_sel} min)
                    </div>
                    """,
                    unsafe_allow_html=True
                )

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
                                "notas": turno_notas
                            })

                            if ok:
                                st.success(f"✅ ¡Turno agendado exitosamente para **{nombre_sel}** el día **{fecha_turno_sel.strftime('%d/%m/%Y')}**!")
                                st.session_state.agenda_date = fecha_turno_sel
                                
                                # Enlaces de WhatsApp y Google Calendar
                                turno_data_for_gcal = {
                                    "fecha": fecha_turno_sel.isoformat(),
                                    "hora_inicio": hora_inicio_sel,
                                    "hora_fin": hora_fin_calc,
                                    "paciente_nombre": nombre_sel,
                                    "paciente_obra_social": paciente_obj.get("obra_social", "Particular"),
                                    "notas": turno_notas
                                }
                                gcal_url_new = generate_turno_google_url(turno_data_for_gcal, clinic_name=clinic_name)
                                
                                tel_p = paciente_obj.get("telefono", "")
                                if tel_p:
                                    wa_conf = template_confirmacion_turno(
                                        nombre_paciente=nombre_sel,
                                        fecha_str=fecha_turno_sel.strftime('%d/%m/%Y'),
                                        hora_str=hora_inicio_sel.strftime('%H:%M'),
                                        duracion_minutos=duracion_sel,
                                        consultorio=clinic_name,
                                        gcal_url=gcal_url_new
                                    )
                                    url_conf = generate_whatsapp_url(tel_p, wa_conf)
                                    st.markdown(
                                        f'<a href="{url_conf}" target="_blank" class="btn-wa" style="margin-right: 10px;">📲 Enviar WhatsApp a {nombre_sel}</a>'
                                        f'<a href="{gcal_url_new}" target="_blank" class="btn-gcal">📅 Añadir a Google Calendar</a>',
                                        unsafe_allow_html=True
                                    )
                                st.rerun()
                            else:
                                st.error(f"Error al agendar turno: {msg}")

    # ------------------------------------------------------------------------------
    # TAB 3: MATRIZ DE OCUPACIÓN HORARIA
    # ------------------------------------------------------------------------------
    with tab_matriz:
        st.markdown(f"#### Ocupación de Camillas / Consultorio ({current_date_str})")
        st.caption("Capacidad máxima por franja horaria: **2 pacientes en simultáneo**.")

        time_slots = []
        curr_time = datetime.combine(current_date, time(8, 0))
        end_time = datetime.combine(current_date, time(15, 0))

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

            nombres_txt = ", ".join([f"<b>{t.get('paciente_nombre')}</b> ({str(t.get('hora_inicio'))[:5]}-{str(t.get('hora_fin'))[:5]})" for t in pacientes_en_slot]) if pacientes_en_slot else "<i style='color: #64748b;'>Sin turnos asignados</i>"

            st.markdown(
                f"""
                <div style="background: #1e293b; border-left: 5px solid {border_color}; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
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
