#!/bin/zsh
# Daily Academic Reports for Benja and Valen

SCRIPT_PATH="/usr/local/lib/node_modules/openclaw/skills/campus-ort-report/generate_report.py"

# Generate Benja's report
python3 "$SCRIPT_PATH" --student "Benja" > /tmp/report_benja.log 2>&1

# Generate Valen's report  
python3 "$SCRIPT_PATH" --student "Valen" > /tmp/report_valen.log 2>&1

echo "✅ Daily reports generated at $(date)"
echo "📋 Benja: /tmp/reporte_academico_benja.txt"
echo "📋 Valen: /tmp/reporte_academico_valen.txt"
