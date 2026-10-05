"""
KNS - Formulario Público de Alta / Registro de Paciente y Carga de Pedido Médico.
Permite al paciente completar su ficha personal y adjuntar su orden médica desde su celular o PC.
"""
import io
import streamlit as st
from datetime import date, datetime
from typing import Optional

from utils.supabase_client import get_app_config, get_paciente_by_id
from utils.registration import get_registration_token, submit_patient_registration
from utils.ui import st_html

OBRAS_SOCIALES_POPULARES = [
    "Particular",
    "O.S.D.E.",
    "SWISS MEDICAL",
    "GALENO",
    "PAMI",
    "MEDIFE",
    "SANCOR SALUD",
    "FEDERADA SALUD",
    "I.S.S.N.",
    "SOSUNC",
    "OSPSA",
    "OMINT",
    "PREVENCION SALUD",
    "UNION PERSONAL / ACCORD",
    "OSDEPYM",
    "OSPAC",
    "Otra (especificar)"
]

TIPOS_DOCUMENTO = [
    "DNI",
    "Cédula de Identidad (CI)",
    "Libreta Cívica (LC)",
    "Libreta de Enrolamiento (LE)",
    "Pasaporte (PAS)",
    "Otro"
]

def render_registro_paciente_view(token: str):
    """Renderiza la vista pública de registro para el paciente identificado por el token."""
    
    app_config = get_app_config()
    clinic_name = app_config.get("clinic_name", "KNS")
    subtitle = app_config.get("subtitle", "KINESIOLOGÍA")
    logo_icon = app_config.get("logo_icon", "🩺")
    custom_logo_bytes = app_config.get("custom_logo_bytes")

    # Inyectar estilos CSS específicos para la vista de registro móvil y desktop
    st.markdown(
        """
        <style>
        /* Ocultar barra lateral y decoraciones innecesarias para el paciente */
        [data-testid="stSidebar"] { display: none; }
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container {
            max-width: 860px !important;
            padding-top: 1rem !important;
            padding-bottom: 2.5rem !important;
        }
        .reg-header {
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            padding: 12px 18px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }
        .reg-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .reg-title {
            color: #0f172a;
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .reg-subtitle {
            color: #64748b;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. Header con logo de la clínica
    if custom_logo_bytes:
        logo_html = f"<img src='data:image/png;base64,{custom_logo_bytes}' style='height: 38px; width: auto;' />"
    else:
        logo_html = f"<div style='font-size: 1.8rem;'>{logo_icon}</div>"

    st_html(
        f"""
        <div class="reg-header">
            {logo_html}
            <div>
                <div style="font-size: 1.1rem; font-weight: 800; color: #0284c7; line-height: 1.1;">{clinic_name}</div>
                <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{subtitle} • Registro de Paciente</div>
            </div>
        </div>
        """
    )

    # 2. Validar token
    reg_info = get_registration_token(token)
    if not reg_info:
        st.error("⚠️ El enlace de registro no es válido, ya ha caducado o no existe.")
        st.info("Por favor comunicate con el consultorio para que te envíen un nuevo link.")
        return

    paciente_id = reg_info.get("paciente_id")
    paciente = get_paciente_by_id(paciente_id) or {}
    
    # 3. Si ya fue completado, mostrar pantalla de confirmación exitosa
    if reg_info.get("completado") and not st.session_state.get(f"force_edit_{token}"):
        nombre_guardado = paciente.get("nombre_completo") or reg_info.get("nombre_inicial", "Paciente")
        st_html(
            f"""
            <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border: 2px solid #34d399; border-radius: 16px; padding: 2rem 1.5rem; text-align: center; margin: 1.5rem 0;">
                <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">✅</div>
                <h2 style="color: #065f46; font-weight: 800; margin: 0 0 0.5rem 0;">¡Ficha Médica Enviada con Éxito!</h2>
                <p style="color: #047857; font-size: 1rem; max-width: 500px; margin: 0 auto 1.5rem auto; line-height: 1.4;">
                    Muchas gracias <b>{nombre_guardado}</b>. Tus datos personales y pedido médico ya fueron cargados en el sistema de <b>{clinic_name}</b>.
                </p>
                <div style="background: #ffffff; border: 1px solid #a7f3d0; border-radius: 10px; padding: 12px 18px; display: inline-block; text-align: left; font-size: 0.88rem; color: #064e3b;">
                    <div>👤 <b>Paciente:</b> {nombre_guardado}</div>
                    <div>🏥 <b>Obra Social:</b> {paciente.get('obra_social', 'Particular')}</div>
                    <div>📞 <b>Teléfono:</b> {paciente.get('telefono', '-')}</div>
                </div>
            </div>
            """
        )
        if st.button("✏️ Modificar o reenviar mis datos", key=f"btn_reedit_{token}"):
            st.session_state[f"force_edit_{token}"] = True
            st.rerun()
        return

    # 4. Formulario de registro activo
    st.markdown("### 📋 Registrate como paciente")
    st.caption("Completá tus datos para que podamos preparar tu historia clínica antes de tu turno.")

    nombre_def = paciente.get("nombre_completo") or reg_info.get("nombre_inicial", "")
    tel_def = paciente.get("telefono") or reg_info.get("telefono_inicial", "")
    dni_def = paciente.get("dni", "")
    email_def = paciente.get("email", "")
    os_def = paciente.get("obra_social", "Particular")
    plan_def = paciente.get("plan_obra_social", "")
    afiliado_def = paciente.get("numero_afiliado", "")
    dir_def = paciente.get("direccion", "")
    loc_def = paciente.get("localidad", "")
    prov_def = paciente.get("provincia", "Buenos Aires")
    pat_def = paciente.get("patologia", "")

    # Manejar fecha de nacimiento inicial
    fn_def = None
    if paciente.get("fecha_nacimiento"):
        try:
            fn_def = datetime.strptime(str(paciente["fecha_nacimiento"]), "%Y-%m-%d").date()
        except Exception:
            fn_def = date(1995, 1, 1)
    else:
        fn_def = date(1995, 1, 1)

    # FORMULARIO
    with st.form("form_alta_paciente_publica", clear_on_submit=False):
        
        # SECCIÓN 1: DATOS DEL PACIENTE
        st.markdown("##### 👤 1. Datos Personales")
        c_dp1, c_dp2 = st.columns([2, 1])
        with c_dp1:
            input_nombre = st.text_input("Apellido y Nombre *", value=nombre_def, placeholder="Ej: Perez, Juan")
        with c_dp2:
            idx_sex = 0
            if paciente.get("sexo") == "Femenino":
                idx_sex = 1
            elif paciente.get("sexo") == "Masculino":
                idx_sex = 0
            input_sexo = st.selectbox("Sexo", ["Masculino", "Femenino", "Otro / No especifica"], index=idx_sex)

        c_doc1, c_doc2, c_fn = st.columns([1.2, 1.5, 1.3])
        with c_doc1:
            input_tipo_doc = st.selectbox("Tipo de Documento *", TIPOS_DOCUMENTO, index=0)
        with c_doc2:
            input_dni = st.text_input("Número de Documento *", value=dni_def, placeholder="Ej: 38123456")
        with c_fn:
            input_fn = st.date_input(
                "Fecha de Nacimiento *",
                value=fn_def,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
                help="Seleccioná tu fecha de nacimiento."
            )

        st.markdown("<hr style='margin: 0.8rem 0; border-color: #e2e8f0;'/>", unsafe_allow_html=True)

        # SECCIÓN 2: CONTACTO
        st.markdown("##### 📞 2. Datos de Contacto")
        c_ct1, c_ct2 = st.columns(2)
        with c_ct1:
            input_cel = st.text_input("Celular / WhatsApp *", value=tel_def, placeholder="Ej: +54 9 11 1234-5678")
        with c_ct2:
            input_email = st.text_input("Correo Electrónico", value=email_def, placeholder="nombre@email.com")

        st.markdown("<hr style='margin: 0.8rem 0; border-color: #e2e8f0;'/>", unsafe_allow_html=True)

        # SECCIÓN 3: OBRA SOCIAL O COBERTURA
        st.markdown("##### 🏥 3. Obra Social o Prepaga")
        c_os1, c_os2, c_os3 = st.columns([1.5, 1.2, 1.3])
        with c_os1:
            idx_os = 0
            if os_def in OBRAS_SOCIALES_POPULARES:
                idx_os = OBRAS_SOCIALES_POPULARES.index(os_def)
            elif os_def:
                idx_os = len(OBRAS_SOCIALES_POPULARES) - 1
            input_os_sel = st.selectbox("Obra Social / Cobertura *", OBRAS_SOCIALES_POPULARES, index=idx_os)
            if input_os_sel == "Otra (especificar)":
                input_os_custom = st.text_input("Nombre de la Obra Social", value=os_def if os_def not in OBRAS_SOCIALES_POPULARES else "")
                input_os_final = input_os_custom.strip() or "Particular"
            else:
                input_os_final = input_os_sel
        with c_os2:
            input_plan = st.text_input("Plan", value=plan_def, placeholder="Ej: 210 / Plan Único")
        with c_os3:
            input_afiliado = st.text_input("Nº de Afiliado / Credencial", value=afiliado_def, placeholder="Ej: 0012345678")

        st.markdown("<hr style='margin: 0.8rem 0; border-color: #e2e8f0;'/>", unsafe_allow_html=True)

        # SECCIÓN 4: DOMICILIO
        st.markdown("##### 📍 4. Domicilio")
        c_dom1, c_dom2, c_dom3 = st.columns([2, 1.2, 1.2])
        with c_dom1:
            input_dir = st.text_input("Dirección (Calle y N°)", value=dir_def, placeholder="Ej: Av. Corrientes 1234")
        with c_dom2:
            input_loc = st.text_input("Localidad", value=loc_def, placeholder="Ej: Belgrano / Ramos Mejía")
        with c_dom3:
            input_prov = st.text_input("Provincia", value=prov_def, placeholder="Ej: CABA / Buenos Aires")

        st.markdown("<hr style='margin: 0.8rem 0; border-color: #e2e8f0;'/>", unsafe_allow_html=True)

        # SECCIÓN 5: CARGA DEL PEDIDO MÉDICO (CÁMARA O ARCHIVO)
        st.markdown("##### 📄 5. Foto del Pedido Médico / Orden Médica")
        st.caption("Podés sacarle una foto directa con la cámara de tu celular o adjuntar un archivo (foto o PDF):")

        tab_cam, tab_file = st.tabs(["📷 Sacar Foto con la Cámara", "📁 Subir Archivo / Foto"])
        
        with tab_cam:
            camera_pic = st.camera_input("Tomar foto del pedido médico")
        with tab_file:
            uploaded_file = st.file_uploader(
                "Seleccionar foto o documento (JPG, PNG, PDF)",
                type=["jpg", "jpeg", "png", "webp", "pdf"],
                help="Sube una foto clara y legible de la orden emitida por tu médico/traumatólogo."
            )

        st.markdown("<hr style='margin: 0.8rem 0; border-color: #e2e8f0;'/>", unsafe_allow_html=True)

        # SECCIÓN 6: MOTIVO DE CONSULTA
        st.markdown("##### 🩺 6. Motivo de Consulta o Diagnóstico")
        input_patologia = st.text_area(
            "¿Cuál es tu lesión, dolor o motivo de consulta? (Opcional)",
            value=pat_def,
            placeholder="Ej: Dolor lumbar al agacharme, tendinitis en hombro derecho, rehabilitación post-quirúrgica...",
            help="Nos ayuda a que el kinesiólogo prepare el equipamiento y plan de tratamiento antes de que llegues."
        )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        btn_enviar = st.form_submit_button("📤 Confirmar y Enviar mis Datos", type="primary", use_container_width=True)

        if btn_enviar:
            if not input_nombre.strip():
                st.error("Por favor completá tu Apellido y Nombre.")
            elif not input_dni.strip():
                st.error("Por favor ingresá tu Número de Documento.")
            elif not input_cel.strip():
                st.error("Por favor ingresá tu número de Celular / WhatsApp.")
            else:
                # Procesar archivo del pedido médico (cámara o uploader)
                file_bytes_to_send = None
                filename_to_send = None

                if camera_pic is not None:
                    file_bytes_to_send = camera_pic.getvalue()
                    filename_to_send = f"pedido_camara_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                elif uploaded_file is not None:
                    file_bytes_to_send = uploaded_file.getvalue()
                    filename_to_send = uploaded_file.name

                form_payload = {
                    "full_name": input_nombre.strip(),
                    "document_type": input_tipo_doc,
                    "document_number": input_dni.strip(),
                    "birth_date": input_fn,
                    "gender": input_sexo,
                    "mobile_phone": input_cel.strip(),
                    "email": input_email.strip(),
                    "medical_insurance": input_os_final,
                    "plan": input_plan.strip(),
                    "affiliate_number": input_afiliado.strip(),
                    "address": input_dir.strip(),
                    "city": input_loc.strip(),
                    "state": input_prov.strip(),
                    "reason": input_patologia.strip()
                }

                with st.spinner("Guardando tu información y subiendo pedido médico..."):
                    ok_sub, msg_sub = submit_patient_registration(
                        token=token,
                        form_data=form_payload,
                        file_bytes=file_bytes_to_send,
                        filename=filename_to_send
                    )

                if ok_sub:
                    st.success("¡Tus datos han sido registrados exitosamente!")
                    if f"force_edit_{token}" in st.session_state:
                        del st.session_state[f"force_edit_{token}"]
                    st.rerun()
                else:
                    st.error(f"Ocurrió un error: {msg_sub}")

    st_html(
        f"""
        <div style="text-align: center; margin-top: 2rem; color: #94a3b8; font-size: 0.8rem;">
            🔒 Tus datos son tratados de forma estrictamente confidencial por <b>{clinic_name}</b>.
        </div>
        """
    )
