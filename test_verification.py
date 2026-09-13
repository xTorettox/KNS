import sys
import os
import json
import py_compile
from datetime import date, time

print("=== 1. VERIFICANDO SINTAXIS DE ARCHIVOS PYTHON ===")
files = [
    'app.py',
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

print("\n=== 2. VALIDANDO DATASET FRASES.JSON ===")
with open('frases.json', 'r', encoding='utf-8') as f:
    frases = json.load(f)
print(f"  Total de frases cargadas: {len(frases)}")
assert len(frases) == 100, f"Se esperaban 100 frases, se encontraron {len(frases)}"
for i, item in enumerate(frases, 1):
    assert "frase" in item and "autor" in item and "obra" in item and "año" in item and "categoria" in item, f"Frase {i} incompleta: {item}"
print("  [OK] frases.json contiene exactamente 100 frases completas con todas sus propiedades.")

print("\n=== 3. PROBANDO LECTURA DE FRASES Y EASTER EGG ===")
from utils.quotes import get_daily_quote, get_random_quote
q = get_daily_quote(date(2026, 9, 13))
print(f"  Frase del día para 13/09/2026: \"{q['frase']}\" — {q['autor']} ({q['obra']}, {q['año']}) [{q['categoria']}]")
assert q["frase"] and q["autor"]
print("  [OK] Lector de frase diaria determinístico operativo.")

print("\n=== 4. PROBANDO GENERADOR DE WHATSAPP Y PLANTILLAS ===")
from utils.whatsapp import (
    normalize_phone_number,
    generate_whatsapp_url,
    template_recordatorio_turno,
    template_confirmacion_turno,
    template_aviso_sesiones_completadas
)
tel1 = normalize_phone_number("11 4444 5555")
tel2 = normalize_phone_number("+54 9 11 1234-5678")
tel3 = normalize_phone_number("011 15 6789 0123")
print(f"  Normalización '11 4444 5555' -> {tel1}")
print(f"  Normalización '+54 9 11 1234-5678' -> {tel2}")
print(f"  Normalización '011 15 6789 0123' -> {tel3}")
assert tel1 == "5491144445555"
assert tel2 == "5491112345678"
assert tel3 == "5491167890123"

msg = template_recordatorio_turno("Carlos", "13/09/2026", "09:00", "KNS")
wa_url = generate_whatsapp_url(tel1, msg)
print(f"  URL wa.me generada: {wa_url[:60]}...")
assert "wa.me/5491144445555" in wa_url
print("  [OK] Integración de WhatsApp validada con éxito.")

print("\n=== 5. PROBANDO AGENDA, SUPERPOSICIÓN (MÁX 2) Y CONTROL DE SESIONES ===")
from utils.supabase_client import (
    get_turnos,
    get_pacientes,
    check_turnos_overlap,
    create_turno,
    update_turno,
    get_paciente_by_id
)

# Caso 1: Probar solapamiento a las 09:10 hs (a las 09:10 están Carlos 08:30-09:15 y Florencia 09:00-09:45 -> 2 simultáneos)
is_valid, count, msg = check_turnos_overlap(date.today(), time(9, 10), time(9, 40))
print(f"  Prueba 1: Turno 09:10 - 09:40 hs -> Válido: {is_valid} (Solapamientos: {count}). Mensaje: {msg}")
assert not is_valid, "Debería rechazar un 3er turno en 09:10"

# Caso 2: Probar horario con solo 1 paciente (08:30 - 09:00 hs -> solo Carlos)
is_valid2, count2, msg2 = check_turnos_overlap(date.today(), time(8, 30), time(9, 0))
print(f"  Prueba 2: Turno 08:30 - 09:00 hs -> Válido: {is_valid2} (Solapamientos: {count2}). Mensaje: {msg2}")
assert is_valid2, "Debería permitir un 2do paciente en 08:30"

print("\n=== TODAS LAS PRUEBAS AUTOMATIZADAS PASARON EXITOSAMENTE (100%) ===")
