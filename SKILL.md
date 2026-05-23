---
name: campus-ort-report
description: Generate ORT Campus academic reports for configured students using the Campus calendar iCal feed and deterministic keyword-based categorization. Use when creating or refreshing student academic summaries, Telegram-ready school reports, or ORT Campus cron/reporting flows for Benja, Valen, or similar students.
---

# Campus ORT Report

Generate academic reports for ORT Campus students from the calendar iCal feed.

## Use the bundled scripts

Main files:
- `generate_report.py` for per-student text reports
- `generate_telegram_report.py` for the combined Telegram-ready report
- `scraper.py` for Campus login, iCal extraction, and event categorization
- `daily_reports.sh` for local scheduled execution if needed

## Prerequisites

Require:
- Python 3.9+
- Playwright installed and browsers available
- 1Password CLI configured
- `OP_SERVICE_ACCOUNT_TOKEN` available in the environment
- 1Password item per student named `ORT Campus - {StudentName}` with `username` and `password`

## Run the report

Use the local skill path, not a guessed global path.

Examples:

```bash
python3 /Users/lucas.lodeiro/.openclaw/workspace/skills/campus-ort-report/generate_report.py --student "Benja"
python3 /Users/lucas.lodeiro/.openclaw/workspace/skills/campus-ort-report/generate_report.py --student "Valen" --days 15
python3 /Users/lucas.lodeiro/.openclaw/workspace/skills/campus-ort-report/generate_telegram_report.py
```

Outputs:
- `/tmp/reporte_academico_{student}.txt`
- `/tmp/reporte_telegram.txt`

## Operational model

The report flow is deterministic.

It:
1. logs into Campus ORT
2. navigates to the calendar
3. extracts the iCal URL
4. downloads upcoming events
5. categorizes them with keyword matching
6. writes text or Telegram-formatted output

Current categories:
- `Examenes`
- `Entregas`
- `Feriados`
- `Academico`
- `Conmemoraciones`
- `Otro`

Prefer this deterministic categorization over LLM classification for this skill.

## Cron / workflow usage

Use this skill when maintaining the ORT academic reporting workflow, especially the weekly report that writes `/tmp/reporte_telegram.txt`.

If reviewing automation output:
- verify the report file was generated
- verify upcoming events are present
- verify category quality on a few sample events
- verify 1Password credentials still resolve correctly

## Troubleshooting

- If 1Password fails, verify `OP_SERVICE_ACCOUNT_TOKEN` and item names.
- If Playwright fails, install browsers again.
- If the iCal URL is missing, verify the Campus navigation path still works.
- If the report is empty, inspect the calendar extraction step first.

## Notes

Treat this as a local workspace skill.
Prefer the real workspace paths above over legacy global installation paths.
