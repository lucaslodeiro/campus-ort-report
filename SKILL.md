# campus-ort-report

Generate academic reports for ORT Campus students. Extracts calendar events using iCal feed with LLM-based categorization.

## Description

This skill generates comprehensive academic reports for students using ORT Campus Virtual. It extracts:
- Calendar events (exams, deliveries, holidays, academic events) - **via iCal feed with LLM categorization**
- Event categorization powered by Ollama LLM (Examen, Entrega, Feriado, Evento Academico, Otro)
- Unified event list for next 15 days

## Prerequisites

- 1Password CLI (`op`) configured with service account token
- The token must be available as `OP_SERVICE_ACCOUNT_TOKEN` environment variable
- 1Password vault "Klaw" with credentials for each student
- Ollama running locally with `kimi-k2.5:cloud` model

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

### LLM-Based Event Categorization
Each event is categorized using Ollama LLM based on title and description:

**Categories:**
- **Examen**: evaluaciones, pruebas, tests, parciales, reading, listening, oral, escrito
- **Entrega**: assignments, tareas, trabajos prácticos, proyectos, informes
- **Feriado**: días no laborables, festivos judíos (Pesaj, Iom Hashoa, etc.)
- **Evento Academico**: reuniones, charlas, actividades especiales, conmemoraciones
- **Otro**: eventos que no encajan en las categorías anteriores

**LLM Prompt:**
```
Analiza este evento escolar y clasificalo en una de estas categorias:
- Examen: evaluaciones, pruebas, tests, parciales, exámenes orales/escritos
- Entrega: trabajos prácticos, assignments, tareas, proyectos, informes
- Feriado: días no laborables, festivos judíos, asuetos
- Evento Academico: reuniones, charlas, actividades especiales, conmemoraciones
- Otro: eventos que no encajan en las anteriores

Evento: {title}
Descripción: {description}

Responde SOLO con el nombre de la categoría.
```

## Dependencies

- Playwright
- Python 3.9+
- 1Password CLI (`op`)
- Ollama (local LLM server)

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

**Ejemplo real:**
```
📚 Reporte Campus ORT - Martes 7/4/2026

───

**BENJA** - 2° año NE2N

📆 Próximas Evaluaciones:

• 10/04/2026 - Evaluación de Historia (Examen)
• 10/04/2026 - Literature Assignment -Pili- (Entrega)
• 13/04/2026 - Evaluación Tecnología (Examen)
• 15/04/2026 - Evaluación de Fuentes (Examen)
• 15/04/2026 - Evaluación de matemática (Examen)
• 16/04/2026 - Listening Test -Pili- (Examen)
• 16/04/2026 - Listening Test (Benyakar) (Examen)
• 17/04/2026 - Use of English test -Pili- (Examen)
• 17/04/2026 - English Test Units 1-2 M.Laura (Examen)
• 17/04/2026 - Use of English (Benyakar) (Examen)
• 20/04/2026 - Evaluación De Etica (Examen)

📅 Asuetos y Feriados:

• 🏖️ 08/04/2026 - Pesaj 7mo día - Asueto (Feriado)
• 🏖️ 09/04/2026 - Pesaj 8vo día - Asueto (Feriado)
• 🏖️ 14/04/2026 - Iom Hashoa (Feriado)
• 🏖️ 21/04/2026 - Iom Hazikaron (Evento Academico)
• 🏖️ 22/04/2026 - Iom Haatzmaut (Feriado)

📋 Otros Eventos:

• 17/04/2026 - Use of English (Benyakar) (Otro)

───

**VALEN** - 7° año GA7E

📆 Próximas Evaluaciones:

• 15/04/2026 - Evaluación de Matemática (Examen)
• 16/04/2026 - READING TEST (ENGLISH T4 Prof. Mariana) (Examen)
• 16/04/2026 - Evaluación de Sociales (U1) (Examen)
• 17/04/2026 - Evaluación CyT (Examen)
• 20/04/2026 - Reading task (T3 Paula) (Examen)
• 20/04/2026 - UE test shirly. (Examen)
• 22/04/2026 - English test (T3 Paula) (Examen)
• 22/04/2026 - Reading comprehension test. Shirly (Examen)

📅 Asuetos y Feriados:

• 🏖️ 08/04/2026 - Pesaj 7mo día - Asueto (Feriado)
• 🏖️ 09/04/2026 - Pesaj 8vo día - Asueto (Feriado)
• 🏖️ 14/04/2026 - Iom Hashoa (Feriado)
• 🏖️ 21/04/2026 - Iom Hazikaron (Evento Academico)
• 🏖️ 22/04/2026 - Iom Haatzmaut (Feriado)

───

📊 Resumen: Benja: 11 eval, 5 asuetos, 1 otros | Valen: 8 eval, 5 asuetos, 0 otros
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
        
        # 5. Categorize with LLM
        category = await categorize_event_with_llm(title, description)
```

### LLM Categorization

```python
async def categorize_event_with_llm(title: str, description: str) -> str:
    prompt = f"""Analiza este evento escolar y clasificalo...
    
    Evento: {title}
    Descripción: {description}
    
    Responde SOLO con la categoría."""
    
    response = ollama.generate(model="kimi-k2.5:cloud", prompt=prompt)
    return normalize_category(response)
```

**Timeout:** 30 seconds per event
**Fallback:** Keyword matching if LLM fails

### File Structure

```
campus-ort-report/
├── SKILL.md                      # This documentation
├── generate_report.py             # Main report generator (TXT format)
├── generate_telegram_report.py    # Telegram-formatted report
└── scraper.py                     # Campus ORT scraper with iCal extraction
```

## Automation

### Daily Reports via OpenClaw Cron

```bash
# Check current cron jobs
openclaw cron list

# The skill should have a cron job configured like:
# Name: "Daily Academic Reports - Benja y Valen"
# Schedule: "0 18 * * 1,2,3,4,5" (weekdays at 18:00)
# Command: python3 generate_telegram_report.py
```

## Troubleshooting

- **1Password token not found**: Ensure `OP_SERVICE_ACCOUNT_TOKEN` is exported
- **Ollama not responding**: Check Ollama is running with `ollama list`
- **iCal URL not found**: The embedCode input may not be loaded yet (navigation issue)
- **LLM timeout**: Events will be categorized with keyword fallback
- **Empty report**: Check `/tmp/calendar_page.html` for debugging

## Recent Changes

### v3.0 - iCal + LLM Categorization
- Migrated from HTML scraping to iCal feed extraction
- Added LLM-based event categorization (Ollama)
- Unified event list (no more separate sections)
- Categories: Examen, Entrega, Feriado, Evento Academico, Otro
- Removed pizarron message extraction (focus on calendar events)

## Author

Generated from ORT Campus Tracker project
