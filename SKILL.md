# campus-ort-report

Generate academic reports for ORT Campus students. Extracts calendar events using iCal feed with keyword‑based categorization.

## Description

This skill generates comprehensive academic reports for students using ORT Campus Virtual. It extracts:
- Calendar events (exams, deliveries, holidays, academic events) - **via iCal feed with deterministic keyword categorization**
- Event categorization using keyword matching (Examenes, Entregas, Feriados, Academico, Conmemoraciones, Otro)
- Unified event list for next 15 days

## Prerequisites

- 1Password CLI (`op`) configured with service account token
- The token must be available as `OP_SERVICE_ACCOUNT_TOKEN` environment variable
- 1Password vault "Klaw" with credentials for each student
- Python 3.9+ with Playwright installed (see Dependencies)

## 1Password Setup

### Option 1: Global Environment (Recommended)

Create `~/.zshenv` with the service account token:

```bash
# ~/.zshenv
export OP_SERVICE_ACCOUNT_TOKEN="your_token_here"
```

### Credential Items

Create credential items in 1Password:
- Title: "ORT Campus - {StudentName}" (e.g., "ORT Campus - Benja")
- Fields:
  - `username`: Campus ORT username (e.g., "52165518")
  - `password`: Campus ORT password

## Usage

### Generate Standard Report (TXT file)

```bash
# Generate report for a student
python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py --student "Benja"

# Generate report with custom date filter
python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py --student "Valen" --days 15
```

### Generate Telegram Formatted Report (Recommended for Cron)

```bash
# Generate both reports formatted for Telegram
python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_telegram_report.py

# Output saved to: /tmp/reporte_telegram.txt
```

## How It Works

### iCal Feed Extraction
The skill navigates to the calendar and extracts the iCal feed:
1. Login to Campus ORT
2. Navigate via UI: Menu → Mi Curso → MÁS EVENTOS
3. Extract iCal URL from `embedCode` input
4. Download full iCal feed (typically 1000+ events)
5. Parse events for next 15 days

### Keyword‑Based Event Categorization
Each event is categorized using deterministic keyword matching based on title and description:

**Categories (priority order):**
- **Feriados**: días no laborables, festivos judíos (Pesaj, Iom Hashoa, etc.), asuetos
- **Examenes**: evaluaciones, pruebas, tests, parciales, reading, listening, oral, escrito
- **Entregas**: assignments, tareas, trabajos prácticos, proyectos, informes
- **Academico**: inicio/fin de ciclo, inscripciones, períodos académicos
- **Conmemoraciones**: días conmemorativos (Iom Hazikaron, etc.)
- **Otro**: eventos que no encajan en las categorías anteriores

**Keyword Matching Logic:**
```python
# Priority: Feriados > Examenes > Entregas > Academico > Conmemoraciones > Otro
if any(keyword in text for keyword in feriados_keywords):
    category = "Feriados"
elif any(keyword in text for keyword in examenes_keywords):
    category = "Examenes"
# ... etc.
```

## Dependencies

- Playwright (for browser automation)
- Python 3.9+
- 1Password CLI (`op`)
- No external LLM required – categorization uses keyword matching

## Output

Reports are saved to:
- `/tmp/reporte_academico_{student}.txt` - Individual reports
- `/tmp/reporte_telegram.txt` - Combined Telegram-formatted report

## Report Format (Telegram Message)

```
📚 Reporte Campus ORT - {Día} {Fecha}

───

**{ESTUDIANTE}** - {Año} {Grupo}

📆 Próximas Evaluaciones:

• {fecha} - {título} ({categoría})
• {fecha} - {título} ({categoría})
...

📅 Asuetos y Feriados:

• 🏖️ {fecha} - {título} ({categoría})
• 🏖️ {fecha} - {título} ({categoría})
...

📋 Otros Eventos:

• {fecha} - {título} ({categoría})
...

───

📊 Resumen: {Estudiante}: {N} eval, {N} asuetos, {N} otros | {Estudiante}: {N} eval, {N} asuetos, {N} otros
```

**Ejemplo real (basado en salida actual):**
```
📚 Reporte Campus ORT - Sábado 11/4/2026

───

**BENJA** - 2° año NE2N

📆 Próximas Evaluaciones:

• 13/04/2026 - Evaluación Tecnología (Examenes)
• 15/04/2026 - Evaluación de Fuentes (Examenes)
• 15/04/2026 - Evaluación de matemática (Examenes)
• 16/04/2026 - Listening Test -Pili- (Examenes)
• 16/04/2026 - Listening Test (Benyakar) (Examenes)
• 17/04/2026 - Use of English test -Pili- (Examenes)
• 17/04/2026 - English Test Units 1-2 M.Laura (Examenes)
• 20/04/2026 - Evaluación De Etica (Examenes)
• 27/04/2026 - Evaluación Biología (Examenes)

📅 Asuetos y Feriados:

• 🏖️ 14/04/2026 - Iom Hashoa (Conmemoraciones)
• 🏖️ 21/04/2026 - Iom Hazikaron (Conmemoraciones)
• 🏖️ 22/04/2026 - Iom Haatzmaut (Conmemoraciones)

📋 Otros Eventos:

• 17/04/2026 - Use of English (Benyakar) (Otro)

───

**VALEN** - 7° año GA7E

📚 Tareas Pendientes:

• Taller De Diseño, Arte, Tecnologia Y Comunicacion 7   1-2-91 - 2026 -  GA7E - ALM: 1 pendiente(s)

📆 Próximas Evaluaciones:

• 16/04/2026 - READING TEST (ENGLISH T4 Prof. Mariana) (Examenes)
• 16/04/2026 - Evaluación de Sociales (U1) (Examenes)
• 17/04/2026 - Evaluación CyT (Examenes)
• 20/04/2026 - UE test shirly. (Examenes)
• 22/04/2026 - Evaluación de Matemática (Examenes)
• 22/04/2026 - English test (T3 Paula) (Examenes)
• 22/04/2026 - Reading comprehension test. Shirly (Examenes)
• 23/04/2026 - Evaluación de Cs. Naturales 1er Bimestre (Examenes)
• 27/04/2026 - Examen Moby Dick (Examenes)

📅 Asuetos y Feriados:

• 🏖️ 14/04/2026 - Iom Hashoa (Conmemoraciones)
• 🏖️ 21/04/2026 - Iom Hazikaron (Conmemoraciones)
• 🏖️ 22/04/2026 - Iom Haatzmaut (Conmemoraciones)

📋 Otros Eventos:

• 20/04/2026 - Reading task (T3 Paula) (Otro)

───

📊 Resumen: Benja: 9 eval, 0 asuetos, 0 tareas pendientes | Valen: 9 eval, 0 asuetos, 1 tareas pendientes
```

## Technical Details

### iCal Extraction Process

```python
async def get_calendar_ical(self):
    # 1. Navigate via UI
    await page.goto("https://campus.ort.edu.ar/mi-curso/calendario")
    
    # 2. Extract iCal URL from embedCode input
    ical_url = await page.evaluate('document.getElementById("embedCode")?.value')
    
    # 3. Download iCal feed
    ical_data = download(ical_url)
    
    # 4. Parse VEVENT blocks
    for vevent in parse_ical(ical_data):
        title = extract_summary(vevent)
        description = extract_description(vevent)
        date = extract_date(vevent)
        
        # 5. Categorize with keyword matching
        category = categorize_event_with_keywords(title, description)
```

### Keyword Categorization

```python
def categorize_event_with_keywords(title: str, description: str) -> str:
    """Categorize event using deterministic keyword matching."""
    text = (title + " " + description).lower()
    
    # Keyword lists (simplified)
    feriados_keywords = ['feriado', 'asueto', 'no hay clases', ...]
    examenes_keywords = ['examen', 'evaluacion', 'prueba', ...]
    entregas_keywords = ['entrega', 'tp', 'trabajo practico', ...]
    academico_keywords = ['inicio', 'fin', 'inscripcion', ...]
    conmemoraciones_keywords = ['iom', 'dia de', 'conmemoracion', ...]
    
    # Priority: Feriados > Examenes > Entregas > Academico > Conmemoraciones > Otro
    if any(k in text for k in feriados_keywords):
        return "Feriados"
    elif any(k in text for k in examenes_keywords):
        return "Examenes"
    elif any(k in text for k in entregas_keywords):
        return "Entregas"
    elif any(k in text for k in academico_keywords):
        return "Academico"
    elif any(k in text for k in conmemoraciones_keywords):
        return "Conmemoraciones"
    else:
        return "Otro"
```

**Characteristics:**
- **Deterministic**: Same input always yields same category
- **Fast**: No network calls or LLM latency
- **Language‑aware**: Keywords in Spanish, covers ORT‑specific terms (Pesaj, Iom, etc.)

### File Structure

```
campus-ort-report/
├── SKILL.md                      # This documentation
├── generate_report.py             # Main report generator (TXT format)
├── generate_telegram_report.py    # Telegram-formatted report
└── scraper.py                     # Campus ORT scraper with iCal extraction
```

## Automation

### Weekly Reports via OpenClaw Cron

```bash
# Check current cron jobs
openclaw cron list

# The skill should have a cron job configured like:
# Name: "Weekly Academic Reports - Benja y Valen"
# Schedule: "0 18 * * 3" (Wednesdays at 18:00, local time)
# Command: python3 generate_telegram_report.py
```

## Troubleshooting

- **1Password token not found**: Ensure `OP_SERVICE_ACCOUNT_TOKEN` is exported
- **Playwright not installed**: Run `pip3 install playwright && playwright install`
- **iCal URL not found**: The embedCode input may not be loaded yet (navigation issue)
- **SSL certificate error**: The script uses unverified SSL context for ORT's certificate
- **Empty report**: Check `/tmp/calendar_page.html` for debugging

## Recent Changes

### v3.0 - iCal + Keyword Categorization
- Migrated from HTML scraping to iCal feed extraction
- **Replaced LLM with deterministic keyword matching** (no Ollama dependency)
- Unified event list (no more separate sections)
- Categories: Examenes, Entregas, Feriados, Academico, Conmemoraciones, Otro
- Removed pizarron message extraction (focus on calendar events)
- Added SSL bypass for ORT's certificate

## Author

Generated from ORT Campus Tracker project
