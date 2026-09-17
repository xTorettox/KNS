import sys
import os
import json
import py_compile
from datetime import date, time, datetime, timedelta

print("=== 1. VERIFICANDO SINTAXIS DE TODOS LOS ARCHIVOS ===")
files = [
    'app.py',
    'utils/auth.py',
    'utils/quotes.py',
    'utils/whatsapp.py',
    'utils/google_calendar.py',
    'utils/ui.py',
    'utils/supabase_client.py',
    'views/agenda.py',
    'views/pacientes.py',
    'views/historial.py',
    'views/configuracion.py'
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  [OK] {f}")
    except Exception as e:
        print(f"  [ERROR] en {f}: {e}")
        sys.exit(1)

print("\n=== 2. PROBANDO SISTEMA DE AUTENTICACIÓN Y ROLES ===")
from utils.auth import (
    verify_password,
    hash_password,
    get_usuarios,
    get_usuario_by_username,
    create_usuario,
    update_usuario,
    delete_usuario
)

# Test Usuario 1: fcendra (admin)
user_fc = get_usuario_by_username("fcendra")
assert user_fc is not None, "Usuario fcendra no encontrado"
assert user_fc["rol"] == "admin", "fcendra debe ser admin"
assert verify_password("C4n1ch3r1426", user_fc["password_hash"]), "Clave de fcendra incorrecta"
print("  [OK] Usuario Administrador 'fcendra' validado con éxito.")

# Test Usuario 2: anita (kinesio)
user_an = get_usuario_by_username("anita")
assert user_an is not None, "Usuario anita no encontrado"
assert user_an["rol"] == "kinesio", "anita debe ser kinesio"
assert verify_password("bella2026", user_an["password_hash"]), "Clave de anita incorrecta"
print("  [OK] Usuario Kinesióloga 'anita' validado con éxito.")

# Test ABM: Creación, actualización y eliminación de usuario de prueba
ok_c, msg_c = create_usuario("test_kinesio", "clave123", "Test Profesional", "kinesio")
assert ok_c, f"Fallo al crear usuario de prueba: {msg_c}"
u_test = get_usuario_by_username("test_kinesio")
assert u_test is not None

ok_up, msg_up = update_usuario(u_test["id"], {"nombre": "Test Profesional Modificado"})
assert ok_up

ok_del, msg_del = delete_usuario(u_test["id"])
assert ok_del
print("  [OK] ABM de usuarios (crear, editar, eliminar) probado y funcional.")

print("\n=== 3. PROBANDO GESTIÓN DE DATOS DEL PACIENTE (FECHA NACIMIENTO, AFILIADO, OBRA SOCIAL / PARTICULAR) ===")
from utils.supabase_client import (
    create_paciente,
    get_pacientes,
    get_paciente_by_id,
    update_paciente,
    delete_paciente
)
from views.pacientes import calcular_edad

# 3.1. Test cálculo de edad
assert calcular_edad(date(1990, 5, 15)) is not None
assert calcular_edad(None) is None

# 3.2. Crear paciente con obra social
ok_p1, msg_p1, p1 = create_paciente({
    "nombre_completo": "Laura Santillán",
    "dni": "31456789",
    "fecha_nacimiento": "1985-03-20",
    "edad": 41,
    "telefono": "+5491145678901",
    "obra_social": "OSDE 310",
    "numero_afiliado": "0310-998877-01",
    "monto_coseguro_default": 4500.0,
    "patologia": "Rehabilitación postquirúrgica menisco externo",
    "sesiones_totales": 10
})
assert ok_p1, f"Error creando paciente con obra social: {msg_p1}"
assert p1["fecha_nacimiento"] == "1985-03-20"
assert p1["numero_afiliado"] == "0310-998877-01"
assert p1["monto_coseguro_default"] == 4500.0
print("  [OK] Paciente con Obra Social, credencial/afiliado y coseguro manual registrado con éxito.")

# 3.3. Crear paciente Particular (sin obra social)
ok_p2, msg_p2, p2 = create_paciente({
    "nombre_completo": "Gonzalo Morales",
    "dni": "40123456",
    "fecha_nacimiento": "1997-10-12",
    "edad": 28,
    "telefono": "+5491178901234",
    "obra_social": "Particular",
    "numero_afiliado": "",
    "monto_coseguro_default": 15000.0,
    "patologia": "Contractura cervical aguda",
    "sesiones_totales": 5
})
assert ok_p2, f"Error creando paciente Particular: {msg_p2}"
assert p2["obra_social"] == "Particular"
assert p2["monto_coseguro_default"] == 15000.0
print("  [OK] Paciente Particular (sin cobertura) y valor de sesión/consulta manual registrado con éxito.")

# 3.4. Búsqueda por número de afiliado
pacs_busq = get_pacientes(query="0310-998877-01")
assert any(p["id"] == p1["id"] for p in pacs_busq), "Búsqueda por afiliado falló"
print("  [OK] Búsqueda de pacientes por número de afiliado / credencial operativa.")

print("\n=== 4. PROBANDO SISTEMA FLEXIBLE DE PAGOS, COSEGUROS Y SALDOS ===")
from utils.supabase_client import (
    create_pago,
    get_pagos,
    get_resumen_financiero_paciente,
    delete_pago,
    create_turno,
    get_turnos
)

p1_id = p1["id"]
p2_id = p2["id"]

# 4.1. Pago individual por sesión (Coseguro)
ok_pay1, msg_pay1, pay1 = create_pago({
    "paciente_id": p1_id,
    "fecha_pago": date.today().isoformat(),
    "monto": 4500.0,
    "concepto": "Coseguro Sesión #1",
    "modalidad": "Por sesión",
    "metodo_pago": "Efectivo",
    "sesiones_cubiertas": 1,
    "notas": "Abonó en efectivo al finalizar sesión"
})
assert ok_pay1, f"Error registrando pago por sesión: {msg_pay1}"
assert pay1["monto"] == 4500.0
assert pay1["modalidad"] == "Por sesión"
print("  [OK] Cobro individual 'por sesión' registrado exitosamente.")

# 4.2. Pago de Tratamiento Completo ("Todo junto")
ok_pay2, msg_pay2, pay2 = create_pago({
    "paciente_id": p1_id,
    "fecha_pago": date.today().isoformat(),
    "monto": 40500.0,
    "monto_total_esperado": 40500.0,
    "concepto": "Pago Tratamiento Completo (9 sesiones restantes)",
    "modalidad": "Tratamiento completo",
    "metodo_pago": "Transferencia / MP",
    "sesiones_cubiertas": 9,
    "notas": "Transferencia bancaria con descuento"
})
assert ok_pay2, f"Error registrando tratamiento completo: {msg_pay2}"
assert pay2["modalidad"] == "Tratamiento completo"
assert pay2["sesiones_cubiertas"] == 9
print("  [OK] Cobro de 'Tratamiento completo (todo junto)' registrado exitosamente.")

# 4.3. Pago Parcial / Seña para Paciente Particular
# Gonzalo Morales tiene 5 sesiones a $15.000 c/u = Total pactado $75.000. Deja seña de $25.000.
ok_pay3, msg_pay3, pay3 = create_pago({
    "paciente_id": p2_id,
    "fecha_pago": date.today().isoformat(),
    "monto": 25000.0,
    "monto_total_esperado": 75000.0,
    "concepto": "Seña inicial paquete 5 sesiones particulares",
    "modalidad": "Pago parcial / Seña",
    "metodo_pago": "Transferencia / MP",
    "sesiones_cubiertas": 2,
    "notas": "Seña abonada por Mercado Pago. Saldo pendiente: $50.000"
})
assert ok_pay3, f"Error registrando seña: {msg_pay3}"
assert pay3["modalidad"] == "Pago parcial / Seña"
assert pay3["monto_total_esperado"] == 75000.0

# 4.4. Verificar cálculo de resumen financiero y saldo pendiente
resumen_p2 = get_resumen_financiero_paciente(p2_id)
assert resumen_p2["total_abonado"] == 25000.0, f"Esperado $25000, obtenido {resumen_p2['total_abonado']}"
assert resumen_p2["monto_total_pactado"] == 75000.0
assert resumen_p2["saldo_pendiente"] == 50000.0, f"Esperado saldo $50000, obtenido {resumen_p2['saldo_pendiente']}"
print("  [OK] Pago parcial / seña y cálculo de saldo pendiente ($50.000) verificado con total precisión.")

# 4.5. Vincular cobro a un turno de agenda
ok_t, _, t_creado = create_turno({
    "paciente_id": p1_id,
    "fecha": date.today().isoformat(),
    "hora_inicio": time(11, 0),
    "hora_fin": time(11, 45),
    "duracion_minutos": 45,
    "estado": "Asistió",
    "monto_coseguro": 4500.0,
    "notas": "Sesión evaluativa"
})
assert ok_t

ok_pay_t, _, pay_t = create_pago({
    "paciente_id": p1_id,
    "turno_id": t_creado["id"],
    "fecha_pago": date.today().isoformat(),
    "monto": 4500.0,
    "concepto": "Coseguro Turno Asistido",
    "modalidad": "Por sesión",
    "metodo_pago": "Efectivo",
    "sesiones_cubiertas": 1
})
assert ok_pay_t
print("  [OK] Vinculación de cobro de coseguro con turno asistido validada.")

# Limpieza de datos de prueba
delete_paciente(p1_id)
delete_paciente(p2_id)
print("  [OK] Limpieza de pacientes de prueba y cascada de pagos completada.")

print("\n=== 5. PROBANDO CONFIGURACIÓN DE MARCA Y LOGO ===")
from utils.supabase_client import get_app_config, update_app_config
cfg = get_app_config()
assert cfg["clinic_name"] == "KNS"
assert cfg["subtitle"] == "KINESIOLOGÍA"
ok_cfg, _ = update_app_config({"logo_icon": "🦴"})
assert ok_cfg
print("  [OK] Personalización de logo y marca operativa.")

print("\n=== 6. VALIDANDO DATASET FRASES.JSON (100 FRASES) ===")
with open('frases.json', 'r', encoding='utf-8') as f:
    frases = json.load(f)
assert len(frases) == 100
print(f"  [OK] Dataset contiene exactamente 100 frases.")

print("\n=== 7. PROBANDO INTEGRACIÓN DE WHATSAPP ===")
from utils.whatsapp import normalize_phone_number, generate_whatsapp_url, template_recordatorio_turno
tel_norm = normalize_phone_number("011 15 6789 0123")
assert tel_norm == "5491167890123"
msg_w = template_recordatorio_turno("Carlos", "13/09/2026", "08:30", gcal_url="https://calendar.google.com/test")
url_w = generate_whatsapp_url(tel_norm, msg_w)
assert "KNS%20Kinesiolog%C3%ADa" in url_w
assert "calendar.google.com" in url_w
print("  [OK] Normalización y plantillas de WhatsApp con Google Calendar verificadas.")

print("\n=== 8. PROBANDO GENERADOR DE GOOGLE CALENDAR Y .ICS ===")
from utils.google_calendar import generate_google_calendar_url, generate_turno_google_url, generate_ics_content
g_url = generate_google_calendar_url(
    title="Turno KNS",
    start_dt=datetime(2026, 9, 20, 9, 0),
    end_dt=datetime(2026, 9, 20, 9, 45),
    details="Prueba turno",
    location="Consultorio KNS"
)
assert "https://calendar.google.com/calendar/render" in g_url
assert "20260920T090000" in g_url
print("  [OK] URL 1-clic de Google Calendar generada correctamente.")

print("\n=== 9. PROBANDO GENERACIÓN Y VALIDACIÓN DE TOKENS DE SESIÓN PERSISTENTE ===")
from utils.auth import generate_session_token, validate_session_token
token_fc = generate_session_token(user_fc)
assert token_fc and isinstance(token_fc, str)
validated_user = validate_session_token(token_fc)
assert validated_user is not None
assert validated_user["username"] == "fcendra"
assert validated_user["rol"] == "admin"

invalid_token = token_fc[:-4] + "ABCD"
assert validate_session_token(invalid_token) is None
print("  [OK] Generación, firma criptográfica HMAC y validación de tokens de sesión verificada.")

print("\n=== TODAS LAS PRUEBAS AUTOMATIZADAS PASARON EXITOSAMENTE (100%) ===")
