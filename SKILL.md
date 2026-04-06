# campus-ort-report

Generate academic reports for ORT Campus students. Extracts calendar events, pizarron messages, and pending assignments.

## Description

This skill generates comprehensive academic reports for students using ORT Campus Virtual. It extracts:
- Calendar events (exams, deliveries, academic events) - **auto-detected via navigation**
- Pizarron messages (last 2 weeks)
- Group memberships
- Urgent items (≤7 days)

## Prerequisites

- 1Password CLI (`op`) configured with service account token
- The token must be available as `OP_SERVICE_ACCOUNT_TOKEN` environment variable
- 1Password vault "Klaw" with credentials for each student

## 1Password Setup

### Option 1: Global Environment (Recommended)

Create `~/.zshenv` with the service account token (loaded in all zsh sessions):

```bash
# ~/.zshenv
export OP_SERVICE_ACCOUNT_TOKEN="your_token_here"
```

### Option 2: Legacy (~/.zshrc)

```bash
export OP_SERVICE_ACCOUNT_TOKEN="your_token_here"
```

> **Note:** `~/.zshenv` is preferred because it loads in all zsh sessions (interactive and non-interactive), while `~/.zshrc` only loads in interactive shells.

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
python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py --student "Valen" --days 14
```

### Generate Telegram Formatted Report (Recommended for Cron)

```bash
# Generate both reports formatted for Telegram
python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_telegram_report.py

# Output saved to: /tmp/reporte_telegram.txt
```

## How It Works

### Calendar Auto-Discovery
The skill automatically navigates to the calendar using the UI flow:
1. Click on menu icon (☰)
2. Click on "Mi Curso"
3. Click on "MÁS EVENTOS"
4. Extract events from the loaded calendar page

**No manual URL configuration needed.**

### Pizarron Extraction
The skill scans all student groups and extracts messages from the last 2 weeks.

### Event Processing
Calendar events are automatically processed to extract:
- Date (from ISO format in HTML)
- Event title and description
- Event type (exam, delivery, other)
- Subject/materia (extracted from title)

## Dependencies

- Playwright
- Python 3.9+
- 1Password CLI (`op`)

## Output

Reports are saved to `/tmp/reporte_academico_{student}.txt`

## Report Format (Telegram Message)

When sending reports via Telegram, use this exact format:

```
📚 Reporte Campus ORT - {Día} {Fecha}

───

{ESTUDIANTE} - {Año} {Grupo}

🚨 URGENTE - Próximos 7 días:

• {emoji} {fecha} ({día relativo}) - {materia}: {título}
• {emoji} {fecha} ({día relativo}) - {materia}: {título}
...

📆 Próximas Evaluaciones ({N} total):

• {fecha} - {materia}
• {fecha} - {materia}
...

📅 Asuetos: {lista de asuetos}

💬 Mensajes ({N}):

• {materia} ({fecha}): "{preview del mensaje}..."
• {materia} ({fecha}): "{preview del mensaje}..."
...

───

📊 Resumen: {Estudiante}: {N} evaluaciones, {N} urgentes, {N} mensajes | {Estudiante}: {N} evaluaciones, {N} urgentes, {N} mensajes
```

**Ejemplo real:**
```
📚 Reporte Campus ORT - Domingo 5/4/2026

───

BENJA - 2° año NE2N

🚨 URGENTE - Próximos 7 días:

• 🏖️ 08/04 (martes) - Pesaj 7mo día - Asueto
• 🏖️ 09/04 (miércoles) - Pesaj 8vo día - Asueto
• 📌 10/04 (viernes) - Inglés: Literature Assignment -Pili-
• 📝 10/04 (viernes) - Historia: Evaluación
• 📝 13/04 (lunes) - Tecnología: Evaluación

📆 Próximas Evaluaciones (10 total):

• 10/04 - Historia
• 13/04 - Tecnología
• 15/04 - Matemática
• ...

📅 Asuetos: Pesaj (8-9/4), Iom Hashoa (14/4), Iom Hazikaron (21/4), Iom Haatzmaut (22/4)

💬 Mensajes (1):

• Biología (30/3): "Chicos! Para la clase que viene (lunes 6/4) tienen q..."

───

VALEN - 7° año GA7E

🚨 URGENTE - Próximos 7 días:

• 📝 06/04 (HOY) - Inglés: TEST ENGLISH UNITS 1&2 (PROF. Mariana)
• 📌 06/04 (HOY) - Assignment in class (T3 Paula)
• 📌 06/04 (HOY) - English exam (Pablo B)
• 🏖️ 08/04 (martes) - Pesaj 7mo día - Asueto
• 🏖️ 09/04 (miércoles) - Pesaj 8vo día - Asueto

📆 Próximas Evaluaciones (9 total):

• 06/04 - Inglés: TEST ENGLISH
• 15/04 - Matemática
• ...

📅 Asuetos: Mismos que Benja

💬 Mensajes (7):

• Educación Judía (23/3): "hola profe no pude realizar la actividad uno porque..."
• Inglés (22/3): "Hello! Les comparto links al student's book y al wor..."
• ...

───

📊 Resumen: Benja: 10 evaluaciones, 5 urgentes, 1 mensaje | Valen: 9 evaluaciones, 5 urgentes, 7 mensajes
```

## Report Sections (Archivo TXT)

1. **🚨 Urgent (≤7 days)**: Exams, deliveries, holidays, and urgent pizarron tasks
2. **📆 Upcoming Evaluations**: List of upcoming exams and deliveries with dates
3. **📅 Academic Events**: Important academic dates (bimester start/end)
4. **💬 Pizarron Messages**: Tasks and messages from last 2 weeks

## File Structure

```
campus-ort-report/
├── SKILL.md              # This documentation
├── generate_report.py    # Main report generator
└── scraper.py            # Campus ORT scraper with auto-discovery
```

## Technical Details

### Auto-Discovery Implementation
The scraper uses Playwright to:
- Navigate via UI elements (material-icons menu)
- Extract calendar events from HTML using regex patterns
- Parse ISO dates from hidden form fields
- Handle dynamic content loading

### Event Extraction
Events are extracted from `CalendarMesInfo` divs that contain event divs with:
- Background color indicating event type
- `title` attribute with event description
- Associated date from `isoDay_{day}` hidden inputs

## Troubleshooting

- **1Password token not found**: Ensure `OP_SERVICE_ACCOUNT_TOKEN` is exported in `~/.zshenv` (or `~/.zshrc`)
  - Verify with: `echo $OP_SERVICE_ACCOUNT_TOKEN`
  - For non-interactive shells, use `~/.zshenv` instead of `~/.zshrc`
- **Calendar not found**: The skill will exit if "MÁS EVENTOS" navigation fails
- **No events extracted**: Check `/tmp/calendar_page.html` for debugging

## Automation

### Daily Reports via Cron

Schedule automatic reports (e.g., weekdays at 18:00):

```bash
# Using OpenClaw cron
openclaw cron add --name "Daily Reports" \
  --schedule "0 18 * * 1-5" \
  --command "python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py --student Benja && python3 /usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py --student Valen"
```

Or use a wrapper script:

```bash
#!/bin/zsh
# /Users/lucas.lodeiro/.openclaw/workspace/scripts/daily_reports.sh
SCRIPT_PATH="/usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py"
python3 "$SCRIPT_PATH" --student "Benja"
python3 "$SCRIPT_PATH" --student "Valen"
```

## Author

Generated from ORT Campus Tracker project
