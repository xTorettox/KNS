"""
Vista de Gestión Integral de Pacientes (Diseño Mobile-First).
Incluye CRUD de pacientes con modal emergente @st.dialog, navegación Master-Detail limpia
sin scrolls confusos, buscador en tiempo real, control de sesiones, historial clínico y archivos adjuntos.
"""
import streamlit as st
from datetime import datetime, date
import pandas as pd
from typing import Optional, Dict, Any, List

from utils.supabase_client import (
    get_pacientes,
    get_paciente_by_id,
    create_paciente,
    update_paciente,
    delete_paciente,
    get_turnos,
    get_evoluciones,
    create_evolucion,
    upload_paciente_archivo,
    get_paciente_archivos,
    delete_paciente_archivo
)
from utils.whatsapp import (
    generate_whatsapp_url,
    template_aviso_sesiones_completadas,
    template_recordatorio_turno
)
from utils.ui import (
    render_header,
    render_kpi_card,
    render_status_badge,
    render_session_progress
)

# ==============================================================================
# MODAL EMERGENTE: ALTA DE PACIENTE (@st.dialog)
# ==============================================================================
@st.dialog("➕ Alta de Nuevo Paciente")
def modal_nuevo_paciente():
    """Formulario modal emergente para registrar un nuevo paciente sin scroll."""
    with st.form("form_alta_paciente"):
        st.markdown("##### Datos Personales y de Contacto")
        c1, c2, c3 = st.columns([3, 1.5, 2])
        with c1:
            nombre_nuevo = st.text_input("Nombre y Apellido *", placeholder="Ej: Matías Rodriguez")
        with c2:
            dni_nuevo = st.text_input("DNI / Documento", placeholder="Ej: 32456789")
        with c3:
            edad_nueva = st.number_input("Edad", min_value=0, max_value=120, value=35)

        c4, c5 = st.columns(2)
        with c4:
            tel_nuevo = st.text_input("Teléfono / Celular (WhatsApp)", placeholder="Ej: 11 4444-5555 o +54 9 11...")
        with c5:
            os_nueva = st.text_input("Obra Social / Prepaga", placeholder="Ej: OSDE, Swiss Medical, Galeno, Particular...")

        st.markdown("##### Información Clínica y Autorización")
        patologia_nueva = st.text_area("Patología / Diagnóstico / Motivo de Consulta *", placeholder="Ej: Tendinitis rotuliana rodilla izquierda. Dolor agudo al bajar escaleras. Derivado por Dr. Gomez.")
        
        c6, c7 = st.columns(2)
        with c6:
            sesiones_tot_nuevas = st.number_input("Sesiones Autorizadas por Orden Médica", min_value=1, max_value=50, value=10)
        with c7:
            notas_adicionales = st.text_input("Observaciones o Antecedentes", placeholder="Ej: Alérgico al látex, opera de LCA en 2021...")

        col_sub1, col_sub2 = st.columns([2, 1])
        with col_sub1:
            btn_guardar_nuevo = st.form_submit_button("Guardar Paciente", type="primary", use_container_width=True)
        with col_sub2:
            btn_cancelar_nuevo = st.form_submit_button("Cancelar", use_container_width=True)

        if btn_guardar_nuevo:
            if not nombre_nuevo.strip():
                st.error("El nombre y apellido son obligatorios.")
            else:
                ok, msg, created = create_paciente({
                    "nombre_completo": nombre_nuevo.strip(),
                    "dni": dni_nuevo.strip(),
                    "edad": int(edad_nueva),
                    "telefono": tel_nuevo.strip(),
                    "obra_social": os_nueva.strip() or "Particular",
                    "patologia": patologia_nueva.strip(),
                    "sesiones_totales": int(sesiones_tot_nuevas),
                    "sesiones_realizadas": 0,
                    "activo": True,
                    "notas_generales": notas_adicionales.strip()
                })
                if ok:
                    st.success(f"¡Paciente **{nombre_nuevo}** creado con éxito!")
                    if created and "id" in created:
                        st.session_state.selected_paciente_id = str(created["id"])
                        st.session_state.paciente_view_mode = "detail"
                    st.rerun()
                else:
                    st.error(msg)
        
        if btn_cancelar_nuevo:
            st.rerun()

# ==============================================================================
# VISTA PRINCIPAL DE PACIENTES
# ==============================================================================
def render_pacientes_view():
    """Renderiza la vista de Pacientes con navegación Master-Detail optimizada para móviles."""
    
    # Recuperar estado de URL si existe
    if "patient_id" in st.query_params and st.query_params["patient_id"]:
        st.session_state.selected_paciente_id = st.query_params["patient_id"]
        st.session_state.paciente_view_mode = "detail"

    # Inicializar estado de navegación
    if "paciente_view_mode" not in st.session_state:
        st.session_state.paciente_view_mode = "list" # "list" o "detail"
    
    # ==============================================================================
    # MODO DETALLE: FICHA CLÍNICA COMPLETA DEL PACIENTE
    # ==============================================================================
    if st.session_state.paciente_view_mode == "detail" and st.session_state.get("selected_paciente_id"):
        sel_id = st.session_state.selected_paciente_id
        paciente_actual = get_paciente_by_id(sel_id)

        if not paciente_actual:
            st.session_state.paciente_view_mode = "list"
            if "patient_id" in st.query_params:
                del st.query_params["patient_id"]
            st.rerun()
            return

        # BOTÓN SUPERIOR DE RETORNO AL LISTADO (MOBILE FIRST)
        if st.button("⬅ Volver al Listado de Pacientes", key="btn_back_top", type="secondary", use_container_width=True):
            st.session_state.paciente_view_mode = "list"
            if "patient_id" in st.query_params:
                try:
                    del st.query_params["patient_id"]
                except Exception:
                    pass
            st.rerun()

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        nom_act = paciente_actual.get("nombre_completo", "")
        dni_act = paciente_actual.get("dni", "No informado")
        edad_act = paciente_actual.get("edad", "-")
        tel_act = paciente_actual.get("telefono", "")
        os_act = paciente_actual.get("obra_social", "Particular")
        pat_act = paciente_actual.get("patologia", "Sin diagnóstico especificado")
        ses_tot_act = paciente_actual.get("sesiones_totales", 10)
        ses_real_act = paciente_actual.get("sesiones_realizadas", 0)
        ses_rest_act = max(0, ses_tot_act - ses_real_act)
        notas_act = paciente_actual.get("notas_generales", "")
        activo_act = paciente_actual.get("activo", True)

        # Encabezado de la Ficha
        st.markdown(
            f"""
            <div class="kns-card">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <h3 style="margin: 0; color: #38bdf8;">📋 Ficha de {nom_act}</h3>
                    <span style="font-size: 0.8rem; padding: 4px 10px; border-radius: 9999px; background: {'rgba(34,197,94,0.2)' if activo_act else 'rgba(239,68,68,0.2)'}; color: {'#4ade80' if activo_act else '#f87171'}; font-weight: bold;">
                        {'ACTIVO' if activo_act else 'INACTIVO'}
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; font-size: 0.9rem; color: #cbd5e1;">
                    <div style="display: flex; align-items: center; gap: 6px;"><span style="background: #0284c7; color: white; font-size: 0.72rem; font-weight: 800; padding: 2px 6px; border-radius: 4px;">DNI</span> <b>{dni_act}</b></div>
                    <div>🎂 <b>Edad:</b> {edad_act} años</div>
                    <div>🏥 <b>Obra Social:</b> {os_act}</div>
                    <div>📞 <b>Teléfono:</b> {tel_act or 'No registrado'}</div>
                </div>
                <div style="margin-top: 12px; font-size: 0.9rem; background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 8px;">
                    <b style="color: #94a3b8;">🩺 Diagnóstico / Patología:</b><br/>
                    <span style="color: #f1f5f9;">{pat_act}</span>
                    {f'<div style="font-size: 0.82rem; color: #94a3b8; margin-top: 6px;"><b>Observaciones:</b> {notas_act}</div>' if notas_act else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Barra de progreso y control de sesiones
        st.markdown(render_session_progress(ses_real_act, ses_tot_act), unsafe_allow_html=True)
        
        # Botones de Acción Contextual
        col_wa_p, col_ed_p = st.columns([2, 1])
        with col_wa_p:
            if ses_rest_act <= 1:
                msg_p = template_aviso_sesiones_completadas(nom_act, ses_real_act, ses_tot_act, os_act)
                btn_wa_txt = "📲 Solicitar Nueva Orden por WhatsApp"
            else:
                msg_p = f"Hola {nom_act}, te escribimos de KNS Kinesiología para coordinar tus próximas sesiones."
                btn_wa_txt = "📲 Contactar por WhatsApp"
            
            wa_link_p = generate_whatsapp_url(tel_act, msg_p)
            st.markdown(f'<a href="{wa_link_p}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center; margin-bottom: 8px;">{btn_wa_txt}</a>', unsafe_allow_html=True)

        with col_ed_p:
            with st.popover("⚙️ Modificar Ficha", use_container_width=True):
                st.markdown("##### Editar Datos del Paciente")
                with st.form(f"edit_paciente_form_{sel_id}"):
                    e_nom = st.text_input("Nombre Completo", value=nom_act)
                    e_dni = st.text_input("DNI", value=dni_act if dni_act != "No informado" else "")
                    e_edad = st.number_input("Edad", min_value=0, max_value=120, value=int(edad_act) if str(edad_act).isdigit() else 30)
                    e_tel = st.text_input("Teléfono", value=tel_act)
                    e_os = st.text_input("Obra Social", value=os_act)
                    e_pat = st.text_area("Patología", value=pat_act)
                    e_tot = st.number_input("Sesiones Autorizadas", min_value=1, max_value=60, value=ses_tot_act)
                    e_real = st.number_input("Sesiones Realizadas (Ajuste manual)", min_value=0, max_value=60, value=ses_real_act)
                    e_act = st.checkbox("Paciente Activo", value=activo_act)
                    
                    sub_e = st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True)
                    if sub_e:
                        ok_u, msg_u = update_paciente(sel_id, {
                            "nombre_completo": e_nom,
                            "dni": e_dni,
                            "edad": e_edad,
                            "telefono": e_tel,
                            "obra_social": e_os,
                            "patologia": e_pat,
                            "sesiones_totales": e_tot,
                            "sesiones_realizadas": e_real,
                            "activo": e_act
                        })
                        if ok_u:
                            st.success("Ficha médica actualizada.")
                            st.rerun()
                        else:
                            st.error(msg_u)

                # Opción de eliminación
                st.markdown("---")
                if st.button("🗑 Eliminar Paciente", key=f"del_pac_{sel_id}", type="secondary", use_container_width=True):
                    delete_paciente(sel_id)
                    st.warning("Paciente eliminado.")
                    st.session_state.selected_paciente_id = None
                    st.session_state.paciente_view_mode = "list"
                    st.rerun()

        # ==============================================================================
        # PESTAÑAS DE LA FICHA: HISTORIAL CLÍNICO / EVOLUCIÓN / ARCHIVOS
        # ==============================================================================
        tab_evols, tab_archivos, tab_turnos_pac = st.tabs(["🩺 Evolución Clínica", "📁 Imágenes y Estudios", "📅 Historial de Turnos"])

        # PESTAÑA 1: EVOLUCIÓN CLÍNICA
        with tab_evols:
            st.markdown("##### Registro de Evolución y Notas de Sesión")
            
            with st.form(f"nueva_evol_form_{sel_id}"):
                c_ev1, c_ev2 = st.columns([3, 1])
                with c_ev1:
                    ev_nota = st.text_area("Nota Clínica / Evolución del Paciente", placeholder="Describir signos, respuesta al tratamiento, movilidad articular, ejercicios...")
                    ev_trat = st.text_input("Tratamiento Aplicado", placeholder="Ej: Magneto 30m + Masoterapia descontracturante + Ejercicios McKenzie")
                with c_ev2:
                    ev_fecha = st.date_input("Fecha", value=date.today())
                    ev_eva = st.slider("Dolor (EVA 0-10)", 0, 10, 3)
                
                btn_ev = st.form_submit_button("Registrar Evolución", type="primary", use_container_width=True)
                if btn_ev:
                    if ev_nota.strip():
                        ok_ev, msg_ev = create_evolucion({
                            "paciente_id": sel_id,
                            "fecha": ev_fecha.isoformat(),
                            "nota_clinica": ev_nota.strip(),
                            "tratamiento_aplicado": ev_trat.strip(),
                            "escala_dolor_eva": ev_eva
                        })
                        if ok_ev:
                            st.success("Evolución guardada exitosamente.")
                            st.rerun()
                        else:
                            st.error(msg_ev)
                    else:
                        st.warning("Escribe la nota clínica.")

            evoluciones_paciente = get_evoluciones(sel_id)
            if not evoluciones_paciente:
                st.caption("Aún no se han registrado notas de evolución para este paciente.")
            else:
                for ev in evoluciones_paciente:
                    f_str = str(ev.get("fecha", ""))
                    n_txt = ev.get("nota_clinica", "")
                    t_txt = ev.get("tratamiento_aplicado", "")
                    eva_val = ev.get("escala_dolor_eva")

                    st.markdown(
                        f"""
                        <div style="border-left: 3px solid #38bdf8; background: #0f172a; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #94a3b8; margin-bottom: 4px;">
                                <span>📅 <b>Fecha:</b> {f_str}</span>
                                <span style="color: {'#ef4444' if (eva_val or 0) > 6 else '#f59e0b' if (eva_val or 0) > 3 else '#10b981'}; font-weight: bold;">
                                    EVA: {eva_val}/10
                                </span>
                            </div>
                            <div style="font-size: 0.9rem; color: #f8fafc;">{n_txt}</div>
                            {f'<div style="font-size: 0.8rem; color: #38bdf8; margin-top: 4px;">🔬 <i>{t_txt}</i></div>' if t_txt else ''}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # PESTAÑA 2: ARCHIVOS Y ESTUDIOS MÉDICOS
        with tab_archivos:
            st.markdown("##### Archivos Clínicos y Estudios de Diagnóstico")
            st.caption("Sube órdenes médicas escaneadas, radiografías, ecografías o informes del paciente.")

            with st.form(f"upload_archivo_form_{sel_id}"):
                c_up1, c_up2 = st.columns([2, 1])
                with c_up1:
                    uploaded_file = st.file_uploader("Seleccionar imagen o documento (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "webp", "pdf"])
                with c_up2:
                    tipo_doc = st.selectbox("Tipo de Documento", ["Orden Médica", "Radiografía (Rx)", "Resonancia Magnética (RMN)", "Ecografía", "Informe Médico", "Otro"])
                
                btn_upload = st.form_submit_button("⬆️ Guardar Archivo / Estudio", type="primary", use_container_width=True)
                if btn_upload and uploaded_file is not None:
                    file_bytes = uploaded_file.getvalue()
                    ok_up, msg_up, arch_rec = upload_paciente_archivo(
                        paciente_id=sel_id,
                        file_bytes=file_bytes,
                        filename=uploaded_file.name,
                        tipo_documento=tipo_doc
                    )
                    if ok_up:
                        st.success(f"¡Archivo '{uploaded_file.name}' guardado correctamente!")
                        st.rerun()
                    else:
                        st.error(msg_up)

            archivos_paciente = get_paciente_archivos(sel_id)
            if not archivos_paciente:
                st.caption("No hay archivos subidos para este paciente todavía.")
            else:
                st.markdown(f"**Archivos guardados ({len(archivos_paciente)}):**")
                for arch in archivos_paciente:
                    a_id = str(arch.get("id"))
                    a_nom = arch.get("nombre_archivo", "Archivo")
                    a_tipo = arch.get("tipo_documento", "Documento")
                    a_path = arch.get("storage_path", "")
                    a_url = arch.get("public_url")
                    a_bytes = arch.get("file_bytes")

                    with st.container():
                        col_a1, col_a2, col_a3 = st.columns([2.5, 1.5, 1])
                        with col_a1:
                            st.markdown(f"📄 **{a_nom}** — *{a_tipo}*")
                        with col_a2:
                            if a_url:
                                st.markdown(f"[🔗 Ver / Descargar]({a_url})")
                            elif a_bytes:
                                st.download_button("⬇️ Descargar", data=a_bytes, file_name=a_nom, key=f"dl_{a_id}")
                        with col_a3:
                            if st.button("🗑", key=f"del_arch_{a_id}", help="Eliminar archivo"):
                                delete_paciente_archivo(a_id, a_path)
                                st.warning("Archivo eliminado.")
                                st.rerun()

                        if any(a_nom.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                            if a_bytes:
                                st.image(a_bytes, width=300, caption=f"{a_nom} ({a_tipo})")
                            elif a_url:
                                st.image(a_url, width=300, caption=f"{a_nom} ({a_tipo})")
                        st.markdown("<hr style='margin: 6px 0; opacity: 0.2;'/>", unsafe_allow_html=True)

        # PESTAÑA 3: HISTORIAL DE TURNOS
        with tab_turnos_pac:
            st.markdown("##### Historial de Turnos y Asistencias")
            turnos_paciente = get_turnos(paciente_id=sel_id)
            if not turnos_paciente:
                st.caption("No hay turnos registrados para este paciente.")
            else:
                for tp in turnos_paciente:
                    f_tp = tp.get("fecha", "")
                    hi_tp = str(tp.get("hora_inicio", ""))[:5]
                    hf_tp = str(tp.get("hora_fin", ""))[:5]
                    dur_tp = tp.get("duracion_minutos", 45)
                    est_tp = tp.get("estado", "Pendiente")
                    not_tp = tp.get("notas", "")
                    
                    st.markdown(
                        f"""
                        <div style="background: #0f172a; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <b>{f_tp}</b> — {hi_tp} a {hf_tp} hs ({dur_tp} min)
                                {f'<div style="font-size: 0.8rem; color: #94a3b8;">{not_tp}</div>' if not_tp else ''}
                            </div>
                            <div>
                                {render_status_badge(est_tp)}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        if st.button("⬅ Volver al Listado de Pacientes", key="btn_back_bottom", type="secondary", use_container_width=True):
            st.session_state.paciente_view_mode = "list"
            if "patient_id" in st.query_params:
                try:
                    del st.query_params["patient_id"]
                except Exception:
                    pass
            st.rerun()
            
        return # Termina renderizado de la ficha

    # ==============================================================================
    # MODO LISTA: BUSCADOR, KPIS Y LISTADO DE PACIENTES (MOBILE FIRST)
    # ==============================================================================
    render_header("Gestión de Pacientes", "Fichas clínicas, control de sesiones por orden médica y archivos adjuntos", icon="👥")

    col_search, col_filter, col_btn = st.columns([3, 1.5, 1.5])
    
    with col_search:
        search_query = st.text_input("🔍 Buscar por Nombre, DNI u Obra Social", placeholder="Ej: Florencia o 34123890...", key="search_pac_input")
    
    with col_filter:
        solo_activos = st.checkbox("Solo pacientes activos", value=True, key="cb_solo_activos")
        
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Nuevo Paciente", type="primary", use_container_width=True, key="btn_open_modal_nuevo"):
            modal_nuevo_paciente()

    # Cargar pacientes
    pacientes_list = get_pacientes(activo_only=solo_activos, query=search_query)

    # KPIs de Pacientes
    total_pac = len(pacientes_list)
    pac_alerta_sesiones = sum(1 for p in pacientes_list if (p.get("sesiones_totales", 10) - p.get("sesiones_realizadas", 0)) <= 1)
    
    k1, k2, k3 = st.columns(3)
    with k1:
        render_kpi_card("Total Pacientes", total_pac, "Registrados en el sistema", color="#38bdf8")
    with k2:
        render_kpi_card("Activos en Tratamiento", sum(1 for p in pacientes_list if p.get("activo", True)), "En curso", color="#4ade80")
    with k3:
        render_kpi_card("Órdenes por Vencer / Vencidas", pac_alerta_sesiones, "Restan ≤ 1 sesión", color="#f87171")

    st.markdown("---")

    if not pacientes_list:
        st.info("No se encontraron pacientes registrados con los criterios de búsqueda.")
        return

    st.markdown("#### Listado de Pacientes")
    st.caption("Toca **'Ver Ficha'** en cualquiera de los pacientes para ver su historial, radiografías y evolución completa.")

    # Renderizar tarjetas de pacientes
    for p in pacientes_list:
        p_id = str(p.get("id"))
        p_nom = p.get("nombre_completo", "")
        p_os = p.get("obra_social", "Particular")
        p_tel = p.get("telefono", "")
        p_real = p.get("sesiones_realizadas", 0)
        p_tot = p.get("sesiones_totales", 10)
        p_rest = max(0, p_tot - p_real)
        
        color_ses = "#10b981" if p_rest > 2 else "#f59e0b" if p_rest > 0 else "#ef4444"

        with st.container():
            st.markdown(
                f"""
                <div style="border: 1px solid rgba(255,255,255,0.08); background: #1e293b; border-radius: 12px; padding: 14px; margin-bottom: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <b style="color: #f8fafc; font-size: 1.05rem;">{p_nom}</b>
                            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 2px;">🏥 {p_os} | 📞 {p_tel or 'S/Tel'}</div>
                        </div>
                        <span style="font-size: 0.8rem; font-weight: 700; color: {color_ses}; background: rgba(0,0,0,0.35); padding: 4px 10px; border-radius: 8px;">
                            {p_real}/{p_tot} Sesiones
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button(f"👤 Ver Ficha de {p_nom}", key=f"btn_sel_{p_id}", type="primary", use_container_width=True):
                st.session_state.selected_paciente_id = p_id
                st.session_state.paciente_view_mode = "detail"
                st.query_params["patient_id"] = p_id
                st.rerun()
            
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
