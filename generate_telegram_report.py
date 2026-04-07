#!/usr/bin/env python3
"""
Wrapper para generar reportes de Campus ORT con formato Telegram
Genera reportes de Benja y Valen y los formatea para envío por Telegram
"""

import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

SKILL_PATH = "/usr/local/lib/node_modules/openclaw/skills/campus-ort-report"
REPORT_BENJA = "/tmp/reporte_academico_benja.txt"
REPORT_VALEN = "/tmp/reporte_academico_valen.txt"

def run_report(student):
    """Ejecutar script de reporte para un estudiante"""
    cmd = [
        "python3",
        f"{SKILL_PATH}/generate_report.py",
        "--student", student,
        "--days", "15"
    ]
    
    # Ejecutar con ambiente completo (incluyendo 1Password)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**dict(subprocess.os.environ), "PATH": "/usr/local/bin:/opt/homebrew/bin:" + subprocess.os.environ.get("PATH", "")}
    )
    
    return result.returncode == 0

def parse_report(filepath):
    """Parsear archivo de reporte y extraer datos estructurados"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    data = {
        'nombre': '',
        'curso': '',
        'evaluaciones': [],
        'asuetos': [],
        'otros': []
    }
    
    # Extraer nombre y curso
    nombre_match = re.search(r'📚\s+(\w+)\s+-\s+(.+?)\n', content)
    if nombre_match:
        data['nombre'] = nombre_match.group(1)
        data['curso'] = nombre_match.group(2).strip()
    
    # Extraer evaluaciones (nuevo formato: fecha - título (categoría))
    eval_section = re.search(r'📆 Próximas Evaluaciones.*?\n─+\n(.*?)(?=\n📅|\n📋|$)', content, re.DOTALL)
    if eval_section:
        for line in eval_section.group(1).split('\n'):
            line = line.strip()
            # Buscar líneas con emoji de evaluación
            if line.startswith('📝'):
                # Formato: 📝 10/04/2026 - Evaluación de Historia (Examen)
                item = re.sub(r'^[📝🏖️📌]\s*', '', line)
                data['evaluaciones'].append(item)
    
    # Extraer asuetos (nuevo formato: 🏖️ fecha - título (categoría))
    asueto_section = re.search(r'📅 Asuetos y Feriados.*?\n─+\n(.*?)(?=\n📋|$)', content, re.DOTALL)
    if asueto_section:
        asuetos_text = []
        for line in asueto_section.group(1).split('\n'):
            line = line.strip()
            if line.startswith('🏖️'):
                # Formato: 🏖️ 07/04/2026 - Víspera 7mo día Pesaj (Asueto)
                item = line
                asuetos_text.append(item)
        data['asuetos'] = asuetos_text
    
    # Extraer otros eventos (nuevo formato: 📋 fecha - título (categoría))
    otros_section = re.search(r'📋 Otros Eventos.*?\n─+\n(.*?)(?=\n─+|$)', content, re.DOTALL)
    if otros_section:
        otros_text = []
        for line in otros_section.group(1).split('\n'):
            line = line.strip()
            if line and (line.startswith('📌') or line.startswith('🏖️') or line.startswith('📝')):
                # Formato: 📌 10/04/2026 - Literature Assignmen... (Otros)
                item = re.sub(r'^[📌🏖️📝]\s*', '', line)
                otros_text.append(item)
        data['otros'] = otros_text
    
    return data

def format_telegram_message(benja_data, valen_data):
    """Formatear datos en mensaje Telegram"""
    
    hoy = datetime.now()
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    dia_nombre = dias_semana[hoy.weekday()]
    dia_num = hoy.day
    mes_nombre = meses[hoy.month - 1]
    anio = hoy.year
    
    mensaje = f"📚 Reporte Campus ORT - {dia_nombre} {dia_num}/{hoy.month}/{anio}\n"
    mensaje += "\n───\n"
    
    # BENJA
    mensaje += f"\n**BENJA** - {benja_data['curso']}\n"
    
    mensaje += "\n📆 Próximas Evaluaciones:\n\n"
    for eval in benja_data['evaluaciones'][:15]:
        mensaje += f"• {eval}\n"
    
    if benja_data['asuetos']:
        mensaje += "\n📅 Asuetos y Feriados:\n\n"
        for asueto in benja_data['asuetos'][:15]:
            mensaje += f"• {asueto}\n"
    
    if benja_data['otros']:
        mensaje += "\n📋 Otros Eventos:\n\n"
        for otro in benja_data['otros'][:15]:
            mensaje += f"• {otro}\n"
    
    # VALEN
    mensaje += "\n───\n"
    mensaje += f"\n**VALEN** - {valen_data['curso']}\n"
    
    mensaje += "\n📆 Próximas Evaluaciones:\n\n"
    for eval in valen_data['evaluaciones'][:15]:
        mensaje += f"• {eval}\n"
    
    if valen_data['asuetos']:
        mensaje += "\n📅 Asuetos y Feriados:\n\n"
        for asueto in valen_data['asuetos'][:15]:
            mensaje += f"• {asueto}\n"
    
    if valen_data['otros']:
        mensaje += "\n📋 Otros Eventos:\n\n"
        for otro in valen_data['otros'][:15]:
            mensaje += f"• {otro}\n"
    
    mensaje += "\n───\n"
    mensaje += f"\n📊 Resumen: Benja: {len(benja_data['evaluaciones'])} eval, {len(benja_data['asuetos'])} asuetos, {len(benja_data['otros'])} otros | Valen: {len(valen_data['evaluaciones'])} eval, {len(valen_data['asuetos'])} asuetos, {len(valen_data['otros'])} otros"
    
    return mensaje

def main():
    """Función principal"""
    import os
    
    # Verificar si hay archivos existentes
    benja_exists = os.path.exists(REPORT_BENJA)
    valen_exists = os.path.exists(REPORT_VALEN)
    
    if benja_exists and valen_exists:
        print("Usando reportes existentes...")
        print("✓ Reporte de Benja encontrado")
        print("✓ Reporte de Valen encontrado")
    else:
        print("Generando reportes de Campus ORT...")
        print()
        
        # Generar reportes
        print("1. Generando reporte de Benja...")
        if not run_report("Benja"):
            print("✗ Error generando reporte de Benja")
            sys.exit(1)
        print("✓ Reporte de Benja generado")
        
        print("2. Generando reporte de Valen...")
        if not run_report("Valen"):
            print("✗ Error generando reporte de Valen")
            sys.exit(1)
        print("✓ Reporte de Valen generado")
    
    # Parsear reportes
    print("3. Parseando datos...")
    benja_data = parse_report(REPORT_BENJA)
    valen_data = parse_report(REPORT_VALEN)
    print("✓ Datos parseados")
    
    # Formatear mensaje
    print("4. Formateando mensaje para Telegram...")
    mensaje = format_telegram_message(benja_data, valen_data)
    
    # Guardar mensaje formateado
    output_file = "/tmp/reporte_telegram.txt"
    with open(output_file, 'w') as f:
        f.write(mensaje)
    
    print(f"✓ Mensaje guardado en: {output_file}")
    print()
    print("=" * 50)
    print("MENSAJE PARA TELEGRAM:")
    print("=" * 50)
    print()
    print(mensaje)
    
    return output_file

if __name__ == "__main__":
    output = main()
    print(f"\nArchivo generado: {output}")