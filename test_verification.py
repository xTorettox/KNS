import sys
import os
import json
import py_compile
from datetime import date, time

print("=== 1. VERIFICANDO SINTAXIS DE TODOS LOS ARCHIVOS ===")
files = [
    'app.py',
    'utils/auth.py',
    'utils/quotes.py',
    'utils/whatsapp.py',
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
msg_w = template_recordatorio_turno("Carlos", "13/09/2026", "08:30")
url_w = generate_whatsapp_url(tel_norm, msg_w)
assert "KNS%20Kinesiolog%C3%ADa" in url_w
print("  [OK] Normalización y plantillas de WhatsApp verificadas.")

print("\n=== TODAS LAS PRUEBAS AUTOMATIZADAS PASARON EXITOSAMENTE (100%) ===")
