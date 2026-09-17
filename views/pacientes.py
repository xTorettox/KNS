"""
Vista de Gestión Integral de Pacientes (Diseño Mobile-First).
Incluye CRUD de pacientes con modal emergente @st.dialog, navegación Master-Detail limpia
sin scrolls confusos, buscador en tiempo real, control de sesiones, historial clínico,
archivos adjuntos y módulo completo de Pagos, Coseguros y Saldos.
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
    delete_paciente_archivo,
    get_pagos,
    create_pago,
    delete_pago,
    get_resumen_financiero_paciente
)
from utils.whatsapp import (
    generate_whatsapp_url,
    template_aviso_sesiones_completadas,
    template_recordatorio_turno
)
from utils.ui import (
    st_html,
    render_header,
    render_kpi_card,
    render_status_badge,
    render_session_progress
)

OBRAS_SOCIALES_COMUNES = [
    "Particular",
    "OSDE",
    "Swiss Medical",
    "Galeno",
    "PAMI",
    "Medifé",
    "Omint",
    "IOMA",
    "Osecac",
    "Unión Personal",
    "Sancor Salud",
    "Prevención Salud",
    "Accord Salud",
    "Otra (especificar)"
]

def calcular_edad(fecha_nac: Optional[date]) -> Optional[int]:
    """Calcula la edad exacta en base a la fecha de nacimiento."""
    if not fecha_nac:
        return None
    today = date.today()
    return today.year - fecha_nac.year - ((today.month, today.day) < (fecha_nac.month, fecha_nac.day))

# ==============================================================================
# MODAL EMERGENTE: ALTA DE PACIENTE (@st.dialog)
# ==============================================================================
@st.dialog("➕ Alta de Nuevo Paciente")
def modal_nuevo_paciente():
    """Formulario modal emergente para registrar un nuevo paciente con todos sus datos y coseguro."""
    with st.form("form_alta_paciente"):
        st.markdown("##### 👤 Datos Personales y Cobertura")
        
        c1, c2 = st.columns([2.5, 1.5])
        with c1:
            nombre_nuevo = st.text_input("Nombre y Apellido *", placeholder="Ej: Matías Rodriguez")
        with c2:
            dni_nuevo = st.text_input("DNI / Documento", placeholder="Ej: 32456789")

        c_fn, c_ed, c_tel = st.columns([1.5, 1, 1.5])
        with c_fn:
            fecha_nac_val = st.date_input(
                "Fecha de Nacimiento",
                value=date(1990, 1, 1),
                min_value=date(1910, 1, 1),
                max_value=date.today(),
                help="Seleccione la fecha de nacimiento para el cálculo automático de edad."
            )
        with c_ed:
            edad_calc = calcular_edad(fecha_nac_val) or 34
            edad_nueva = st.number_input("Edad", min_value=0, max_value=120, value=max(0, edad_calc))
        with c_tel:
            tel_nuevo = st.text_input("Teléfono / WhatsApp", placeholder="Ej: 11 4444-5555")

        st.markdown("##### 🏥 Obra Social / Prepaga y Coseguro")
        c_os1, c_os2 = st.columns([1.5, 1.5])
        with c_os1:
            os_sel = st.selectbox(
                "Obra Social / Cobertura",
                options=OBRAS_SOCIALES_COMUNES,
                index=0, # Particular por defecto
                help="Seleccione 'Particular' si el paciente no cuenta con cobertura médica."
            )
            if os_sel == "Otra (especificar)":
                os_custom = st.text_input("Especifique la Obra Social", placeholder="Ej: OSDEPYM, OSPACP...")
                os_final = os_custom.strip() or "Particular"
            else:
                os_final = os_sel

        with c_os2:
            afiliado_nuevo = st.text_input(
                "Número de Afiliado / Socio",
                placeholder="Ej: 0210-482910-01 (Dejar vacío si es Particular)",
                help="Credencial o número de afiliado de la obra social."
            )

        c_cos1, c_ses = st.columns(2)
        with c_cos1:
            is_particular = (os_final == "Particular")
            lbl_monto = "Valor Consulta / Sesión ($)" if is_particular else "Monto Coseguro Habitual ($)"
            hlp_monto = "Monto de la sesión particular." if is_particular else "Monto del coseguro por sesión acordado con el paciente."
            monto_cos_nuevo = st.number_input(
                lbl_monto,
                min_value=0.0,
                step=500.0,
                value=0.0,
                help=f"{hlp_monto} Campo de ingreso manual personalizable."
            )
        with c_ses:
            sesiones_tot_nuevas = st.number_input("Sesiones Autorizadas / Pactadas", min_value=1, max_value=60, value=10)

        st.markdown("##### 🩺 Información Clínica")
        patologia_nueva = st.text_area(
            "Patología / Diagnóstico / Motivo de Consulta *",
            placeholder="Ej: Tendinitis rotuliana rodilla izquierda. Dolor agudo al bajar escaleras. Derivado por Dr. Gomez."
        )
        notas_adicionales = st.text_input("Observaciones o Antecedentes", placeholder="Ej: Alérgico al látex, operado de LCA en 2021...")

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
                    "fecha_nacimiento": fecha_nac_val.isoformat() if fecha_nac_val else None,
                    "edad": int(edad_nueva),
                    "telefono": tel_nuevo.strip(),
                    "obra_social": os_final,
                    "numero_afiliado": afiliado_nuevo.strip(),
                    "monto_coseguro_default": float(monto_cos_nuevo),
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
        st.session_state.paciente_view_mode = "list"
    
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
        fn_raw = paciente_actual.get("fecha_nacimiento")
        fn_obj = None
        if fn_raw:
            try:
                fn_obj = date.fromisoformat(str(fn_raw))
            except Exception:
                pass
        
        edad_act = calcular_edad(fn_obj) if fn_obj else paciente_actual.get("edad", "-")
        tel_act = paciente_actual.get("telefono", "")
        os_act = paciente_actual.get("obra_social", "Particular")
        is_particular = (os_act.lower().strip() == "particular")
        afiliado_act = paciente_actual.get("numero_afiliado", "")
        cos_act = float(paciente_actual.get("monto_coseguro_default", 0) or 0)
        pat_act = paciente_actual.get("patologia", "Sin diagnóstico especificado")
        ses_tot_act = paciente_actual.get("sesiones_totales", 10)
        ses_real_act = paciente_actual.get("sesiones_realizadas", 0)
        ses_rest_act = max(0, ses_tot_act - ses_real_act)
        notas_act = paciente_actual.get("notas_generales", "")
        activo_act = paciente_actual.get("activo", True)

        fn_display = fn_obj.strftime("%d/%m/%Y") if fn_obj else "No informada"
        afiliado_display = afiliado_act if (afiliado_act and not is_particular) else ("Particular (Sin credencial)" if is_particular else "No registrado")

        # Encabezado de la Ficha
        st_html(
            f"""
            <div class="kns-card">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <h3 style="margin: 0; color: #38bdf8;">📋 Ficha de {nom_act}</h3>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <span style="font-size: 0.8rem; padding: 4px 10px; border-radius: 9999px; background: {'rgba(34,197,94,0.2)' if is_particular else 'rgba(56,189,248,0.2)'}; color: {'#4ade80' if is_particular else '#38bdf8'}; font-weight: bold;">
                            {'👤 PARTICULAR' if is_particular else f'🏥 {os_act}'}
                        </span>
                        <span style="font-size: 0.8rem; padding: 4px 10px; border-radius: 9999px; background: {'rgba(34,197,94,0.2)' if activo_act else 'rgba(239,68,68,0.2)'}; color: {'#4ade80' if activo_act else '#f87171'}; font-weight: bold;">
                            {'ACTIVO' if activo_act else 'INACTIVO'}
                        </span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 14px; font-size: 0.9rem; color: #cbd5e1;">
                    <div style="display: flex; align-items: center; gap: 6px;"><span style="background: #0284c7; color: white; font-size: 0.72rem; font-weight: 800; padding: 2px 6px; border-radius: 4px;">DNI</span> <b>{dni_act}</b></div>
                    <div>🎂 <b>F. Nacimiento:</b> {fn_display} ({edad_act} años)</div>
                    <div>🪪 <b>N° Afiliado:</b> {afiliado_display}</div>
                    <div>📞 <b>Teléfono:</b> {tel_act or 'No registrado'}</div>
                    <div>💵 <b>{'Valor Consulta:' if is_particular else 'Coseguro:'}</b> <span style="color: #4ade80; font-weight: 700;">${cos_act:,.2f}</span></div>
                </div>
                <div style="margin-top: 12px; font-size: 0.9rem; background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 8px;">
                    <b style="color: #94a3b8;">🩺 Diagnóstico / Patología:</b><br/>
                    <span style="color: #f1f5f9;">{pat_act}</span>
                    {f'<div style="font-size: 0.82rem; color: #94a3b8; margin-top: 6px;"><b>Observaciones:</b> {notas_act}</div>' if notas_act else ''}
                </div>
            </div>
            """
        )

        # Barra de progreso y control de sesiones
        st_html(render_session_progress(ses_real_act, ses_tot_act))
        
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
            st_html(f'<a href="{wa_link_p}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center; margin-bottom: 8px;">{btn_wa_txt}</a>')

        with col_ed_p:
            with st.popover("⚙️ Modificar Ficha", use_container_width=True):
                st.markdown("##### Editar Datos del Paciente")
                with st.form(f"edit_paciente_form_{sel_id}"):
                    e_nom = st.text_input("Nombre Completo", value=nom_act)
                    e_dni = st.text_input("DNI", value=dni_act if dni_act != "No informado" else "")
                    
                    e_fn_val = st.date_input(
                        "Fecha de Nacimiento",
                        value=fn_obj if fn_obj else date(1990, 1, 1),
                        min_value=date(1910, 1, 1),
                        max_value=date.today()
                    )
                    e_edad_calc = calcular_edad(e_fn_val) or (int(edad_act) if str(edad_act).isdigit() else 30)
                    e_edad = st.number_input("Edad", min_value=0, max_value=120, value=max(0, e_edad_calc))
                    
                    e_tel = st.text_input("Teléfono", value=tel_act)
                    e_os = st.text_input("Obra Social (escriba 'Particular' si no tiene cobertura)", value=os_act)
                    e_af = st.text_input("Número de Afiliado / Socio", value=afiliado_act)
                    e_cos = st.number_input("Monto Coseguro / Valor Consulta ($)", min_value=0.0, step=500.0, value=cos_act)
                    e_pat = st.text_area("Patología", value=pat_act)
                    e_tot = st.number_input("Sesiones Autorizadas / Pactadas", min_value=1, max_value=60, value=ses_tot_act)
                    e_real = st.number_input("Sesiones Realizadas (Ajuste manual)", min_value=0, max_value=60, value=ses_real_act)
                    e_act = st.checkbox("Paciente Activo", value=activo_act)
                    
                    sub_e = st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True)
                    if sub_e:
                        ok_u, msg_u = update_paciente(sel_id, {
                            "nombre_completo": e_nom,
                            "dni": e_dni,
                            "fecha_nacimiento": e_fn_val.isoformat() if e_fn_val else None,
                            "edad": int(e_edad),
                            "telefono": e_tel,
                            "obra_social": e_os.strip() or "Particular",
                            "numero_afiliado": e_af.strip(),
                            "monto_coseguro_default": float(e_cos),
                            "patologia": e_pat,
                            "sesiones_totales": int(e_tot),
                            "sesiones_realizadas": int(e_real),
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
        # PESTAÑAS DE LA FICHA: PAGOS & COSEGUROS / HISTORIAL CLÍNICO / ARCHIVOS / TURNOS
        # ==============================================================================
        tab_pagos, tab_evols, tab_archivos, tab_turnos_pac = st.tabs([
            "💳 Pagos y Coseguros",
            "🩺 Evolución Clínica",
            "📁 Imágenes y Estudios",
            "📅 Historial de Turnos"
        ])

        # ==============================================================================
        # PESTAÑA 1: GESTIÓN DE PAGOS Y COSEGUROS
        # ==============================================================================
        with tab_pagos:
            st.markdown("##### 💳 Control de Cobros, Coseguros y Pagos Parciales")
            
            # Obtener resumen financiero del paciente
            resumen_fin = get_resumen_financiero_paciente(sel_id)
            total_cobrado = resumen_fin["total_abonado"]
            cant_pagos = resumen_fin["cantidad_pagos"]
            ses_cubiertas = resumen_fin["sesiones_cubiertas"]
            saldo_pendiente = resumen_fin["saldo_pendiente"]
            pagos_paciente = resumen_fin["pagos"]

            # KPIs Financieros
            k_f1, k_f2, k_f3, k_f4 = st.columns(4)
            with k_f1:
                render_kpi_card("Total Cobrado", f"${total_cobrado:,.2f}", f"{cant_pagos} pago(s) registrados", color="#4ade80")
            with k_f2:
                render_kpi_card("Sesiones Pagadas", f"{ses_cubiertas} / {ses_tot_act}", f"{ses_real_act} asistidas", color="#38bdf8")
            with k_f3:
                color_saldo = "#f87171" if saldo_pendiente > 0 else "#4ade80"
                lbl_saldo = "Al día" if saldo_pendiente == 0 else "Saldo adeudado"
                render_kpi_card("Saldo Pendiente", f"${saldo_pendiente:,.2f}", lbl_saldo, color=color_saldo)
            with k_f4:
                lbl_unidad = "Valor Sesión (Particular)" if is_particular else "Coseguro Habitual"
                render_kpi_card(lbl_unidad, f"${cos_act:,.2f}", "Por sesión", color="#facc15")

            if saldo_pendiente > 0:
                st_html(
                    f"""
                    <div style="background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444; border-radius: 8px; padding: 10px 14px; margin: 10px 0;">
                        <b style="color: #f87171;">⚠️ Saldo Pendiente:</b> El paciente adeuda <b style="color: #fca5a5;">${saldo_pendiente:,.2f}</b> por el tratamiento o sesiones asistidas.
                    </div>
                    """
                )

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

            # FORMULARIO / EXPANDER: REGISTRAR NUEVO COBRO / PAGO
            with st.expander("➕ Registrar Nuevo Pago / Cobro", expanded=(len(pagos_paciente) == 0)):
                with st.form(f"form_nuevo_pago_{sel_id}"):
                    st.markdown("###### Detalles del Cobro")
                    
                    c_m1, c_m2 = st.columns([1.5, 1.5])
                    with c_m1:
                        modalidad_sel = st.selectbox(
                            "Modalidad / Frecuencia de Cobro",
                            options=["Por sesión", "Tratamiento completo", "Pago parcial / Seña"],
                            index=0,
                            help="Selecciona si se cobra una sesión puntual, el tratamiento total por adelantado/final, o una seña/entrega parcial."
                        )
                    with c_m2:
                        # Sugerir monto según modalidad y coseguro default
                        sugerido = cos_act if cos_act > 0 else 5000.0
                        if modalidad_sel == "Tratamiento completo":
                            sugerido = (cos_act * ses_tot_act) if cos_act > 0 else 35000.0
                        elif modalidad_sel == "Pago parcial / Seña" and saldo_pendiente > 0:
                            sugerido = saldo_pendiente
                        
                        monto_ingresado = st.number_input(
                            "Monto Abonado ($) *",
                            min_value=0.0,
                            step=500.0,
                            value=float(sugerido),
                            help="Monto exacto cobrado al paciente (campo manual editable)."
                        )

                    c_esp1, c_esp2 = st.columns([1.5, 1.5])
                    if modalidad_sel == "Pago parcial / Seña":
                        with c_esp1:
                            monto_total_pactado_input = st.number_input(
                                "Monto Total Acordado del Tratamiento ($) *",
                                min_value=0.0,
                                step=1000.0,
                                value=float((cos_act * ses_tot_act) if cos_act > 0 else (monto_ingresado * 2)),
                                help="Monto total del paquete o tratamiento para calcular saldos restantes."
                            )
                        with c_esp2:
                            ses_cubiertas_input = st.number_input("Sesiones cubiertas por esta seña", min_value=0, max_value=60, value=1)
                        concepto_default = f"Seña / Entrega inicial para tratamiento ({ses_tot_act} sesiones)"
                    elif modalidad_sel == "Tratamiento completo":
                        with c_esp1:
                            monto_total_pactado_input = st.number_input(
                                "Monto Total del Tratamiento ($)",
                                min_value=0.0,
                                step=1000.0,
                                value=float(monto_ingresado),
                                help="Monto total cobrado por el paquete de sesiones completo."
                            )
                        with c_esp2:
                            ses_cubiertas_input = st.number_input("Sesiones que cubre el pago", min_value=1, max_value=60, value=ses_tot_act)
                        concepto_default = f"Tratamiento Completo ({ses_cubiertas_input} sesiones)"
                    else:
                        monto_total_pactado_input = None
                        with c_esp1:
                            ses_cubiertas_input = st.number_input("Sesiones que cubre", min_value=1, max_value=60, value=1)
                        with c_esp2:
                            st.caption("Cobro individual por sesión asistida.")
                        concepto_default = f"Valor Consulta Sesión #{ses_real_act + 1}" if is_particular else f"Coseguro Sesión #{ses_real_act + 1}"

                    concepto_input = st.text_input("Concepto / Detalle del Cobro *", value=concepto_default, placeholder="Ej: Coseguro Sesión 2 o Pago total de 10 sesiones")

                    c_fp1, c_fp2 = st.columns([1.5, 1.5])
                    with c_fp1:
                        fecha_pago_input = st.date_input("Fecha de Cobro", value=date.today())
                    with c_fp2:
                        metodo_pago_input = st.selectbox(
                            "Método de Pago",
                            options=["Efectivo", "Transferencia / MP", "Tarjeta Débito", "Tarjeta Crédito", "Otro"],
                            index=0
                        )

                    notas_pago_input = st.text_input("Observaciones / N° Transacción", placeholder="Ej: Transferencia Banco Galicia o pagó en efectivo en recepción")

                    btn_guardar_pago = st.form_submit_button("💾 Confirmar y Registrar Pago", type="primary", use_container_width=True)
                    if btn_guardar_pago:
                        if monto_ingresado <= 0:
                            st.warning("Ingrese un monto mayor a 0.")
                        elif not concepto_input.strip():
                            st.warning("Ingrese un concepto para el cobro.")
                        else:
                            ok_p, msg_p, _ = create_pago({
                                "paciente_id": sel_id,
                                "fecha_pago": fecha_pago_input.isoformat(),
                                "monto": float(monto_ingresado),
                                "monto_total_esperado": float(monto_total_pactado_input) if monto_total_pactado_input is not None else None,
                                "concepto": concepto_input.strip(),
                                "modalidad": modalidad_sel,
                                "metodo_pago": metodo_pago_input,
                                "sesiones_cubiertas": int(ses_cubiertas_input),
                                "notas": notas_pago_input.strip()
                            })
                            if ok_p:
                                st.success("¡Pago registrado exitosamente!")
                                st.rerun()
                            else:
                                st.error(msg_p)

            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            st.markdown(f"###### Historial de Cobros y Recibos ({len(pagos_paciente)})")

            if not pagos_paciente:
                st.info("Aún no se han registrado cobros o pagos para este paciente.")
            else:
                for p in pagos_paciente:
                    p_id = str(p.get("id"))
                    p_fecha = str(p.get("fecha_pago", ""))
                    p_monto = float(p.get("monto", 0))
                    p_conc = p.get("concepto", "Pago")
                    p_mod = p.get("modalidad", "Por sesión")
                    p_met = p.get("metodo_pago", "Efectivo")
                    p_ses = p.get("sesiones_cubiertas", 1)
                    p_tot_esp = p.get("monto_total_esperado")
                    p_not = p.get("notas", "")

                    badge_mod_color = "#38bdf8" if p_mod == "Por sesión" else "#a855f7" if p_mod == "Tratamiento completo" else "#f59e0b"

                    st_html(
                        f"""
                        <div style="background: #1e293b; border-left: 4px solid {badge_mod_color}; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                                <div>
                                    <span style="font-size: 1.15rem; font-weight: 800; color: #4ade80;">+${p_monto:,.2f}</span>
                                    <span style="font-size: 0.85rem; color: #94a3b8; margin-left: 8px;">({p_met})</span>
                                    <div style="font-weight: 700; color: #f8fafc; margin-top: 2px; font-size: 0.95rem;">{p_conc}</div>
                                    <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 2px;">
                                        📅 <b>Fecha:</b> {p_fecha} | 🎟️ <b>Cubre:</b> {p_ses} sesión(es)
                                        {f' | 🎯 <b>Total Pactado:</b> ${float(p_tot_esp):,.2f}' if p_tot_esp else ''}
                                    </div>
                                    {f'<div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">📝 <i>{p_not}</i></div>' if p_not else ''}
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
                                    <span style="font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.08); color: {badge_mod_color};">
                                        {p_mod.upper()}
                                    </span>
                                </div>
                            </div>
                        </div>
                        """
                    )
                    
                    c_del_p, _ = st.columns([1, 4])
                    with c_del_p:
                        if st.button("🗑 Eliminar Cobro", key=f"del_pago_{p_id}", type="secondary", use_container_width=True):
                            delete_pago(p_id)
                            st.warning("Registro de cobro eliminado.")
                            st.rerun()

                # Botón para enviar resumen de pagos por WhatsApp
                if tel_act:
                    msg_resumen_wa = f"Hola {nom_act}, te compartimos el resumen de cobros de tu tratamiento en KNS Kinesiología:\n- Total Abonado: ${total_cobrado:,.2f}\n- Sesiones Cubiertas: {ses_cubiertas}/{ses_tot_act}\n- Saldo Pendiente: ${saldo_pendiente:,.2f}\n¡Muchas gracias!"
                    wa_res_url = generate_whatsapp_url(tel_act, msg_resumen_wa)
                    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                    st_html(f'<a href="{wa_res_url}" target="_blank" class="btn-wa" style="width: 100%; text-align: center; justify-content: center;">📲 Enviar Resumen de Pagos por WhatsApp</a>')

        # ==============================================================================
        # PESTAÑA 2: EVOLUCIÓN CLÍNICA
        # ==============================================================================
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

                    st_html(
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
                        """
                    )

        # ==============================================================================
        # PESTAÑA 3: ARCHIVOS Y ESTUDIOS MÉDICOS
        # ==============================================================================
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

        # ==============================================================================
        # PESTAÑA 4: HISTORIAL DE TURNOS
        # ==============================================================================
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
                    cos_tp = float(tp.get("monto_coseguro", 0) or cos_act)
                    pago_est = tp.get("estado_pago", "Pendiente")
                    
                    st_html(
                        f"""
                        <div style="background: #0f172a; padding: 10px 14px; border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <b>{f_tp}</b> — {hi_tp} a {hf_tp} hs ({dur_tp} min)
                                <div style="font-size: 0.85rem; color: #38bdf8; margin-top: 2px;">
                                    💵 Coseguro / Sesión: <b>${cos_tp:,.2f}</b> | Pago: <b>{pago_est}</b>
                                </div>
                                {f'<div style="font-size: 0.8rem; color: #94a3b8;">{not_tp}</div>' if not_tp else ''}
                            </div>
                            <div>
                                {render_status_badge(est_tp)}
                            </div>
                        </div>
                        """
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
            
        return

    # ==============================================================================
    # MODO LISTA: BUSCADOR, KPIS Y LISTADO DE PACIENTES (MOBILE FIRST)
    # ==============================================================================
    render_header("Gestión de Pacientes", "Fichas clínicas, control de sesiones por orden médica, pagos y coseguros", icon="👥")

    col_search, col_filter, col_btn = st.columns([3, 1.5, 1.5])
    
    with col_search:
        search_query = st.text_input("🔍 Buscar por Nombre, DNI, Afiliado u Obra Social", placeholder="Ej: Florencia, OSDE, 34123890...", key="search_pac_input")
    
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
    pac_particulares = sum(1 for p in pacientes_list if str(p.get("obra_social", "")).lower().strip() == "particular")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Total Pacientes", total_pac, "Registrados", color="#38bdf8")
    with k2:
        render_kpi_card("En Tratamiento", sum(1 for p in pacientes_list if p.get("activo", True)), "Activos", color="#4ade80")
    with k3:
        render_kpi_card("Particulares", pac_particulares, "Sin obra social", color="#a855f7")
    with k4:
        render_kpi_card("Órdenes por Vencer", pac_alerta_sesiones, "Restan ≤ 1 sesión", color="#f87171")

    st.markdown("---")

    if not pacientes_list:
        st.info("No se encontraron pacientes registrados con los criterios de búsqueda.")
        return

    st.markdown("#### Listado de Pacientes")
    st.caption("Toca **'Ver Ficha'** en cualquiera de los pacientes para ver su historial, pagos y coseguros, radiografías y evolución completa.")

    # Renderizar tarjetas de pacientes
    for p in pacientes_list:
        p_id = str(p.get("id"))
        p_nom = p.get("nombre_completo", "")
        p_os = p.get("obra_social", "Particular")
        is_part = (p_os.lower().strip() == "particular")
        p_af = p.get("numero_afiliado", "")
        p_tel = p.get("telefono", "")
        p_cos = float(p.get("monto_coseguro_default", 0) or 0)
        p_real = p.get("sesiones_realizadas", 0)
        p_tot = p.get("sesiones_totales", 10)
        p_rest = max(0, p_tot - p_real)
        
        color_ses = "#10b981" if p_rest > 2 else "#f59e0b" if p_rest > 0 else "#ef4444"
        badge_os_style = "background: rgba(34,197,94,0.15); color: #4ade80;" if is_part else "background: rgba(56,189,248,0.15); color: #38bdf8;"

        with st.container():
            st_html(
                f"""
                <div style="border: 1px solid rgba(255,255,255,0.08); background: #1e293b; border-radius: 12px; padding: 14px; margin-bottom: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                <b style="color: #f8fafc; font-size: 1.05rem;">{p_nom}</b>
                                <span style="font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; {badge_os_style}">
                                    {'👤 PARTICULAR' if is_part else f'🏥 {p_os}'}
                                </span>
                            </div>
                            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">
                                📞 {p_tel or 'S/Tel'} | 💵 {'Valor Sesión:' if is_part else 'Coseguro:'} <b style="color: #4ade80;">${p_cos:,.2f}</b>
                                {f' | 🪪 Afiliado: {p_af}' if p_af and not is_part else ''}
                            </div>
                        </div>
                        <span style="font-size: 0.8rem; font-weight: 700; color: {color_ses}; background: rgba(0,0,0,0.35); padding: 4px 10px; border-radius: 8px;">
                            {p_real}/{p_tot} Sesiones
                        </span>
                    </div>
                </div>
                """
            )
            if st.button(f"👤 Ver Ficha de {p_nom}", key=f"btn_sel_{p_id}", type="primary", use_container_width=True):
                st.session_state.selected_paciente_id = p_id
                st.session_state.paciente_view_mode = "detail"
                st.query_params["patient_id"] = p_id
                st.rerun()
            
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
