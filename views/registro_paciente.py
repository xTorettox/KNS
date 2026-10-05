# -*- coding: utf-8 -*-
"""
KION - Centro Terapéutico Integral
Formulario Público de Alta / Registro de Paciente y Carga de Pedido Médico.
Permite al paciente completar su ficha personal y adjuntar su orden médica desde su celular o PC.
"""
import io
import os
import base64
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

def _get_kion_logo_b64() -> Optional[str]:
    """Obtiene el logo oficial de KION en formato base64 para renderizar en HTML."""
    candidates = ["assets/kion_logo.png", "assets/logo.png", "logo.png"]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return None

def render_registro_paciente_view(token: str):
    """Renderiza la vista pública de registro para el paciente identificado por el token."""
    
    app_config = get_app_config()
    clinic_name = app_config.get("clinic_name", "KION")
    subtitle = app_config.get("subtitle", "Centro Terapéutico Integral")
    
    logo_b64 = _get_kion_logo_b64()

    # Inyectar estilos CSS específicos para la vista de registro móvil y desktop
    st.markdown(
        """
        <style>
        /* Ocultar barra lateral y menús internos para el paciente */
        [data-testid="stSidebar"] { display: none !important; }
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        .block-container {
            max-width: 820px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 3rem !important;
        }
        
        .kion-header-card {
            background: linear-gradient(135deg, #042f2e 0%, #0f766e 100%);
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 1.2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 25px -5px rgba(15, 118, 110, 0.3);
            border: 1px solid rgba(45, 212, 191, 0.2);
        }
        
        .kion-logo-img {
            max-height: 65px;
            width: auto;
            object-fit: contain;
            background: #ffffff;
            padding: 4px 8px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        
        .kion-header-text h1 {
            margin: 0;
            color: #ffffff;
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        
        .kion-header-text p {
            margin: 0;
            color: #ccfbf1;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .section-card {
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 1rem;
        }
        
        .section-title {
            color: #38bdf8;
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .info-particular-box {
            background: rgba(45, 212, 191, 0.1);
            border: 1px solid #14b8a6;
            border-radius: 10px;
            padding: 10px 14px;
            color: #ccfbf1;
            font-size: 0.88rem;
            margin: 0.8rem 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. Header con logo de KION
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="kion-logo-img" alt="KION Logo" />'
    else:
        logo_html = '<div style="font-size: 2.2rem; background: #fff; border-radius: 10px; padding: 4px 10px;">🩺</div>'

    st_html(
        f"""
        <div class="kion-header-card">
            {logo_html}
            <div class="kion-header-text">
                <h1>{clinic_name}</h1>
                <p>{subtitle} • Ficha de Paciente</p>
            </div>
        </div>
        """
    )

    # 2. Validar token
    reg_info = get_registration_token(token)
    if not reg_info:
        st.error("⚠️ El enlace de registro no es válido, ya ha caducado o no existe.")
        st.info("Por favor comunicate con el consultorio para solicitar un nuevo link.")
        return

    paciente_id = reg_info.get("paciente_id")
    paciente = get_paciente_by_id(paciente_id) or {}
    
    # 3. Si ya fue completado, mostrar pantalla de confirmación exitosa
    if reg_info.get("completado") and not st.session_state.get(f"force_edit_{token}"):
        nombre_guardado = paciente.get("nombre_completo") or reg_info.get("nombre_inicial", "Paciente")
        os_guardada = paciente.get('obra_social', 'Particular')
        st_html(
            f"""
            <div style="background: linear-gradient(135deg, #042f2e 0%, #115e59 100%); border: 2px solid #2dd4bf; border-radius: 16px; padding: 2rem 1.5rem; text-align: center; margin: 1.5rem 0; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
                <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">✅</div>
                <h2 style="color: #ffffff; font-weight: 800; margin: 0 0 0.5rem 0;">¡Ficha Médica Registrada con Éxito!</h2>
                <p style="color: #ccfbf1; font-size: 1rem; max-width: 520px; margin: 0 auto 1.5rem auto; line-height: 1.4;">
                    Muchas gracias <b>{nombre_guardado}</b>. Tus datos ya se encuentran cargados en el sistema de <b>{clinic_name}</b>.
                </p>
                <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(45, 212, 191, 0.3); border-radius: 12px; padding: 14px 20px; display: inline-block; text-align: left; font-size: 0.9rem; color: #f8fafc;">
                    <div>👤 <b>Paciente:</b> {nombre_guardado}</div>
                    <div>🏥 <b>Cobertura / Obra Social:</b> {os_guardada}</div>
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
    st.markdown("### 📋 Completá tu Ficha de Atención")
    st.caption("Por favor completá los siguientes campos para que preparemos tu historia clínica antes de tu turno.")

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

    # SECCIÓN 1: DATOS PERSONALES
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

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    # SECCIÓN 2: CONTACTO
    st.markdown("##### 📞 2. Datos de Contacto")
    c_ct1, c_ct2 = st.columns(2)
    with c_ct1:
        input_cel = st.text_input("Celular / WhatsApp *", value=tel_def, placeholder="Ej: +54 9 11 1234-5678")
    with c_ct2:
        input_email = st.text_input("Correo Electrónico", value=email_def, placeholder="nombre@email.com")

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    # SECCIÓN 3: OBRA SOCIAL O COBERTURA
    st.markdown("##### 🏥 3. Obra Social o Cobertura Médica")
    c_os1, c_os2, c_os3 = st.columns([1.5, 1.2, 1.3])
    with c_os1:
        idx_os = 0
        if os_def in OBRAS_SOCIALES_POPULARES:
            idx_os = OBRAS_SOCIALES_POPULARES.index(os_def)
        elif os_def:
            idx_os = len(OBRAS_SOCIALES_POPULARES) - 1
        input_os_sel = st.selectbox("Obra Social / Cobertura *", OBRAS_SOCIALES_POPULARES, index=idx_os, key="reg_os_selector")
        
        if input_os_sel == "Otra (especificar)":
            input_os_custom = st.text_input("Especificar Nombre de Obra Social", value=os_def if os_def not in OBRAS_SOCIALES_POPULARES else "")
            input_os_final = input_os_custom.strip() or "Particular"
        else:
            input_os_final = input_os_sel

    is_particular = (input_os_sel == "Particular")

    if is_particular:
        input_plan = ""
        input_afiliado = ""
        st_html(
            """
            <div class="info-particular-box">
                <span>💡</span> <span><b>Atención Particular:</b> No es necesario ingresar plan ni número de afiliado, ni adjuntar orden médica.</span>
            </div>
            """
        )
    else:
        with c_os2:
            input_plan = st.text_input("Plan", value=plan_def, placeholder="Ej: 210 / Plan Único")
        with c_os3:
            input_afiliado = st.text_input("Nº de Afiliado / Credencial", value=afiliado_def, placeholder="Ej: 0012345678")

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    # SECCIÓN 4: DOMICILIO
    st.markdown("##### 📍 4. Domicilio")
    c_dom1, c_dom2, c_dom3 = st.columns([2, 1.2, 1.2])
    with c_dom1:
        input_dir = st.text_input("Dirección (Calle y N°)", value=dir_def, placeholder="Ej: Av. Corrientes 1234")
    with c_dom2:
        input_loc = st.text_input("Localidad", value=loc_def, placeholder="Ej: Belgrano / Ramos Mejía")
    with c_dom3:
        input_prov = st.text_input("Provincia", value=prov_def, placeholder="Ej: CABA / Buenos Aires")

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    # SECCIÓN 5: CARGA DEL PEDIDO MÉDICO (SÓLO SI NO ES PARTICULAR, Y ES OPCIONAL)
    camera_pic = None
    uploaded_file = None

    if not is_particular:
        st.markdown("##### 📄 5. Foto del Pedido Médico / Orden Médica (Opcional)")
        st.caption("Si contás con tu orden médica o derivación, podés fotografiarla o adjuntarla ahora (o presentarla el día de la sesión):")

        tab_cam, tab_file = st.tabs(["📷 Sacar Foto con la Cámara", "📁 Subir Archivo / Foto / PDF"])
        
        with tab_cam:
            camera_pic = st.camera_input("Tomar foto de la orden médica", key="reg_cam_pic")
        with tab_file:
            uploaded_file = st.file_uploader(
                "Seleccionar archivo (JPG, PNG, PDF)",
                type=["jpg", "jpeg", "png", "webp", "pdf"],
                key="reg_file_up",
                help="Sube una foto clara y legible de la orden médica."
            )

        st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    # SECCIÓN 6: MOTIVO DE CONSULTA
    st.markdown("##### 🩺 6. Motivo de Consulta o Diagnóstico")
    input_patologia = st.text_area(
        "¿Cuál es tu lesión, dolor o motivo de consulta? (Opcional)",
        value=pat_def,
        placeholder="Ej: Dolor lumbar al agacharme, rehabilitación post-quirúrgica, tendinitis en hombro...",
        help="Nos permite conocer tu caso para prepararnos antes de tu llegada."
    )

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # BOTÓN DE ENVÍO
    btn_enviar = st.button("📤 Confirmar y Enviar mis Datos", type="primary", use_container_width=True, key="btn_enviar_ficha_paciente")

    if btn_enviar:
        if not input_nombre.strip():
            st.error("Por favor completá tu Apellido y Nombre.")
        elif not input_dni.strip():
            st.error("Por favor ingresá tu Número de Documento.")
        elif not input_cel.strip():
            st.error("Por favor ingresá tu número de Celular / WhatsApp.")
        else:
            # Procesar archivo del pedido médico si fue cargado (opcional)
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

            with st.spinner("Guardando tu información en KION..."):
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
