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

print("\n=== 3. PROBANDO CONFIGURACIÓN DE MARCA Y LOGO ===")
from utils.supabase_client import get_app_config, update_app_config
cfg = get_app_config()
assert cfg["clinic_name"] == "KNS"
assert cfg["subtitle"] == "KINESIOLOGÍA"
ok_cfg, _ = update_app_config({"logo_icon": "🦴"})
assert ok_cfg
print("  [OK] Personalización de logo y marca operativa.")

print("\n=== 4. VALIDANDO DATASET FRASES.JSON (100 FRASES) ===")
with open('frases.json', 'r', encoding='utf-8') as f:
    frases = json.load(f)
assert len(frases) == 100
print(f"  [OK] Dataset contiene exactamente 100 frases.")

print("\n=== 5. PROBANDO INTEGRACIÓN DE WHATSAPP ===")
from utils.whatsapp import normalize_phone_number, generate_whatsapp_url, template_recordatorio_turno
tel_norm = normalize_phone_number("011 15 6789 0123")
assert tel_norm == "5491167890123"
msg_w = template_recordatorio_turno("Carlos", "13/09/2026", "08:30", gcal_url="https://calendar.google.com/test")
url_w = generate_whatsapp_url(tel_norm, msg_w)
assert "KNS%20Kinesiolog%C3%ADa" in url_w
assert "calendar.google.com" in url_w
print("  [OK] Normalización y plantillas de WhatsApp con Google Calendar verificadas.")

print("\n=== 6. PROBANDO GENERADOR DE GOOGLE CALENDAR Y .ICS ===")
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

test_turnos = [
    {
        "id": "t1",
        "fecha": "2026-09-25",
        "hora_inicio": "08:30:00",
        "hora_fin": "09:15:00",
        "paciente_nombre": "Carlos Menéndez",
        "paciente_obra_social": "OSDE 210",
        "estado": "Pendiente",
        "notas": "Fisioterapia"
    }
]
ics_text = generate_ics_content(test_turnos, clinic_name="KNS Kinesiología")
assert "BEGIN:VCALENDAR" in ics_text
assert "BEGIN:VEVENT" in ics_text
assert "Carlos Menéndez" in ics_text
assert "END:VCALENDAR" in ics_text
print("  [OK] Generador de archivo iCal estándar (.ics) verificado.")

print("\n=== 7. PROBANDO FILTRO DE FECHAS EN AGENDA (MES Y RANGOS) ===")
from utils.supabase_client import get_turnos
turnos_rango = get_turnos(start_date=date.today(), end_date=date.today() + timedelta(days=30))
assert isinstance(turnos_rango, list)
print(f"  [OK] Consulta por rango de fechas (Vista Mensual y Próximos Turnos) funcionando. ({len(turnos_rango)} turnos)")

print("\n=== TODAS LAS PRUEBAS AUTOMATIZADAS PASARON EXITOSAMENTE (100%) ===")
