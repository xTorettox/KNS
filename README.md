# 🩺 KNS - Sistema de Gestión de Consultorio Kinesiológico

Aplicación web profesional desarrollada en **Python** y **Streamlit**, con base de datos **PostgreSQL** y almacenamiento de imágenes en **Supabase Storage**. Diseñada específicamente para optimizar la operativa diaria de kinesiólogos y centros de rehabilitación física.

![KNS Preview](https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=1200&q=80)

---

## 🚀 Características Principales

### 👥 1. Gestión de Pacientes y Fichas Clínicas
- **CRUD Completo:** Registro de Nombre y Apellido, DNI, Edad, Teléfono, Obra Social/Prepaga, Patología o Motivo de consulta (texto libre) y notas de antecedentes.
- **Control Inteligente de Sesiones:** Registro de sesiones autorizadas por orden médica (ej. 10 sesiones) con descuento automático al registrar la asistencia del paciente.
- **Alertas de Vencimiento de Órdenes:** Indicador visual de alerta cuando al paciente le restan $\le 1$ sesión para solicitar una nueva prescripción médica.

### 📅 2. Agenda de Turnos y Superposición Controlada
- **Horario Laboral Estricto:** Configurado de **08:00 a 15:00 hs**.
- **Capacidad de Superposición:** Permite hasta **2 pacientes en simultáneo** (validación en tiempo real; bloquea si se intenta un tercer turno superpuesto).
- **Duraciones Dinámicas:** Configuración de turnos en bloques de **30, 45 o 60 minutos** con cálculo automático de la hora de finalización.
- **Ajuste de Horarios y Llegadas Tarde:** Edición flexible de horas de inicio/fin y registro de motivos de desfasaje.
- **Matriz Visual de Ocupación:** Visualizador tipo timeline de 08:00 a 15:00 hs por bloques de 30 min para evaluar la carga de camillas.

### 🩺 3. Historial Clínico y Evoluciones
- Registro cronológico de evoluciones médicas por sesión.
- Seguimiento del dolor mediante la **Escala Visual Analógica (EVA 0-10)** y gráfico interactivo de progreso.
- Detalle del tratamiento kinesiológico aplicado (TENS, magnetoterapia, masoterapia, ejercicios propioceptivos, etc.).

### 📁 4. Manejo de Archivos y Supabase Storage
- Subida de imágenes y documentos escaneados vinculados a cada paciente:
  - Órdenes médicas.
  - Radiografías (Rx).
  - Resonancias Magnéticas (RMN).
  - Ecografías e Informes.
- Previsualización de imágenes directa en la ficha médica y enlaces de descarga.

### 📲 5. Integración con WhatsApp (1-Clic)
- Generación dinámica de enlaces `wa.me` con normalización automática de teléfonos argentinos e internacionales (`+54 9 11...`).
- Plantillas contextuales listas para enviar:
  - Recordatorios de turnos del día.
  - Confirmaciones de nuevos turnos agendados.
  - Avisos de reprogramación horaria.
  - Solicitud de nueva orden médica por sesiones completadas.

### 📼 6. Easter Egg: Frases de Culto 80s/90s
- Base de datos en `frases.json` con **100 frases icónicas y bizarras** del cine de acción y la cultura pop argentina (Guillermo Francella, Los Simuladores, Ricardo Darín, Alberto Olmedo, Arnold Schwarzenegger, Sylvester Stallone, Bruce Willis, Jim Carrey, etc.).
- Rotación automática de una frase distinta cada día en la barra lateral (sidebar) mediante cálculo determinístico por fecha.

---

## 🛠️ Estructura del Proyecto

```
KNS/
├── .streamlit/
│   ├── config.toml              # Tema visual (colores oscuros modernos, fuentes, layout)
│   ├── secrets.toml             # Credenciales activas de Supabase (ignorado en git)
│   └── secrets.toml.example     # Plantilla para Streamlit Cloud y colaboradores
├── views/
│   ├── __init__.py
│   ├── agenda.py                # Agenda 08-15hs, control máx 2 superposiciones, WhatsApp
│   ├── pacientes.py             # CRUD pacientes, control sesiones, ficha clínica y storage
│   ├── historial.py             # Evoluciones clínicas y gráfico EVA
│   └── configuracion.py         # Diagnóstico de Supabase, visualizador SQL y frases
├── utils/
│   ├── __init__.py
│   ├── supabase_client.py       # Cliente Supabase, helpers CRUD y fallback en memoria
│   ├── whatsapp.py              # Limpieza de teléfonos y generador de links wa.me
│   ├── quotes.py                # Lector determinístico de frases.json
│   └── ui.py                    # CSS personalizado, badges, KPIs y tarjetas
├── app.py                       # Punto de entrada principal y enrutador
├── frases.json                  # Dataset con las 100 frases pre-pobladas
├── supabase_schema.sql          # Script DDL completo para Supabase (tablas, triggers, bucket)
├── requirements.txt             # Dependencias del proyecto
└── .gitignore                   # Exclusiones de Git
```

---

## ⚙️ Configuración de Base de Datos (Supabase)

### Paso 1: Ejecutar el Script SQL
1. Ingresa a tu panel de control en [Supabase](https://supabase.com).
2. Ve a la sección **SQL Editor** (`/project/_/sql`).
3. Abre o copia el contenido de [`supabase_schema.sql`](supabase_schema.sql) y haz clic en **Run**.
   - Creará las tablas `pacientes`, `turnos`, `evoluciones`, `archivos_pacientes`.
   - Creará los índices y el trigger `sync_paciente_sesiones` para descontar sesiones automáticamente.
   - Creará el bucket público de almacenamiento `pacientes-adjuntos` en Supabase Storage.

### Paso 2: Credenciales de Supabase
Configura el archivo `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://kgdbgjuezooecsobfwfy.supabase.co"
key = "TU_SUPABASE_KEY"
bucket_name = "pacientes-adjuntos"

[app]
clinic_name = "KNS - Consultorio Kinesiológico"
professional_name = "Lic. Kinesiología & Fisiatría"
phone = "+5491112345678"
work_start_hour = 8
work_end_hour = 15
max_simultaneous_patients = 2
```

---

## 💻 Ejecución Local

1. Clona el repositorio e ingresa a la carpeta:
```bash
git clone https://github.com/TU-USUARIO/KNS.git
cd KNS
```

2. Crea y activa un entorno virtual de Python:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / MacOS
python3 -m venv .venv
source .venv/bin/activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Inicia la aplicación Streamlit:
```bash
streamlit run app.py
```

La app se abrirá automáticamente en tu navegador en `http://localhost:8501`.

---

## ☁️ Despliegue en Streamlit Community Cloud

1. Sube tu código a un repositorio en **GitHub**.
2. Ingresa a [share.streamlit.io](https://share.streamlit.io) y selecciona **New app**.
3. Selecciona tu repositorio, rama `main` y archivo principal `app.py`.
4. En **Advanced Settings** ➔ **Secrets**, pega el contenido de `.streamlit/secrets.toml.example` con tus claves reales de Supabase.
5. Haz clic en **Deploy!** 🚀

---

## 📄 Licencia y Créditos
Desarrollado para consultorios de kinesiología y fisioterapia. Libre para uso profesional y adaptaciones.
