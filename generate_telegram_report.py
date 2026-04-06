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
        'urgentes': [],
        'evaluaciones': [],
        'asuetos': [],
        'mensajes': []
    }
    
    # Extraer nombre y curso
    nombre_match = re.search(r'📚\s+(\w+)\s+-\s+(.+?)\n', content)
    if nombre_match:
        data['nombre'] = nombre_match.group(1)
        data['curso'] = nombre_match.group(2).strip()
    
    # Extraer urgentes
    urgente_section = re.search(r'🚨 URGENTE.*?\n─+\n(.*?)(?=\n📆|\n📅|$)', content, re.DOTALL)
    if urgente_section:
        for line in urgente_section.group(1).split('\n'):
            line = line.strip()
            # Buscar líneas con emojis o bullets
            if line.startswith('🏖️') or line.startswith('📝') or line.startswith('📌'):
                # Limpiar el item - remover emoji al inicio, espacios extras, caracteres ocultos y subtítulo
                item = re.sub(r'^[🏖️📝📌]\s*', '', line)
                item = re.sub(r'\s+└─.*', '', item)
                item = re.sub(r'[\s\uFE0F]+', ' ', item)  # Normalizar espacios y emoji modifiers
                item = item.strip()
                if item and not item.startswith('─'):
                    data['urgentes'].append(item)
    
    # Extraer evaluaciones
    eval_section = re.search(r'📆 Próximas Evaluaciones.*?\n─+\n(.*?)(?=\n📅|\n📋|$)', content, re.DOTALL)
    if eval_section:
        for line in eval_section.group(1).split('\n'):
            line = line.strip()
            # Buscar líneas con emoji de evaluación
            if line.startswith('📝'):
                item = re.sub(r'^[📝]\s*', '', line)
                item = re.sub(r'\s+└─.*', '', item)  # Remover subtítulo
                # Extraer fecha y materia
                match = re.match(r'(\d{2}/\d{2}/\d{4})[^-]*-\s*(.+)', item)
                if match and 'total' not in item.lower():
                    data['evaluaciones'].append(f"{match.group(1)} - {match.group(2).strip()}")
    
    # Extraer asuetos
    asueto_section = re.search(r'📅 Asuetos y Feriados.*?\n─+\n(.*?)(?=\n📋|$)', content, re.DOTALL)
    if asueto_section:
        asuetos_text = []
        for line in asueto_section.group(1).split('\n'):
            if line.strip().startswith('🏖️'):
                item = line.strip()
                item = re.sub(r'^🏖️\s*', '', item)
                # Extraer solo nombre del feriado
                feriado_match = re.search(r'-\s+(.+)$', item)
                if feriado_match:
                    asuetos_text.append(feriado_match.group(1))
        data['asuetos'] = asuetos_text
    
    # Extraer mensajes
    msg_section = re.search(r'💬 Mensajes.*?\n─+\n(.*?)(?=\n─+|$)', content, re.DOTALL)
    if msg_section:
        current_materia = ""
        for line in msg_section.group(1).split('\n'):
            line = line.strip()
            if line.startswith('📌'):
                # Nueva materia
                materia_match = re.search(r'📌\s*(.+?)(?:\s+\(|$)', line)
                if materia_match:
                    current_materia = materia_match.group(1).strip()
            elif line.startswith('💬') and current_materia:
                # Mensaje
                msg_match = re.search(r'💬\s*(\d{1,2}/\d{1,2}/?.*?):\s*(.+)$', line)
                if msg_match:
                    data['mensajes'].append({
                        'materia': current_materia,
                        'fecha': msg_match.group(1),
                        'texto': msg_match.group(2)[:60] + '...' if len(msg_match.group(2)) > 60 else msg_match.group(2)
                    })
    
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
    mensaje += "\n🚨 URGENTE - Próximos 7 días:\n\n"
    
    for urgente in benja_data['urgentes'][:5]:
        urgente_clean = urgente.strip()
        # Determinar emoji según contenido
        if 'asueto' in urgente_clean.lower() or 'pesaj' in urgente_clean.lower() or 'feriado' in urgente_clean.lower():
            emoji = "🏖️"
        elif 'evaluación' in urgente_clean.lower() or 'test' in urgente_clean.lower() or 'examen' in urgente_clean.lower():
            emoji = "📝"
        else:
            emoji = "📌"
        
        mensaje += f"• {emoji} {urgente_clean}\n"
    
    mensaje += f"\n📆 Próximas Evaluaciones ({len(benja_data['evaluaciones'])} total):\n\n"
    for eval in benja_data['evaluaciones'][:8]:
        mensaje += f"• {eval}\n"
    
    if benja_data['asuetos']:
        mensaje += f"\n📅 Asuetos: {', '.join(benja_data['asuetos'][:4])}\n"
    
    if benja_data['mensajes']:
        mensaje += f"\n💬 Mensajes ({len(benja_data['mensajes'])}):\n\n"
        for msg in benja_data['mensajes'][:3]:  # Limitar a 3
            mensaje += f"• {msg['materia']} ({msg['fecha']}): \"{msg['texto']}\"\n"
    
    # VALEN
    mensaje += "\n───\n"
    mensaje += f"\n**VALEN** - {valen_data['curso']}\n"
    mensaje += "\n🚨 URGENTE - Próximos 7 días:\n\n"
    
    for urgente in valen_data['urgentes'][:5]:
        urgente_clean = urgente.strip()
        if 'asueto' in urgente_clean.lower() or 'pesaj' in urgente_clean.lower():
            emoji = "🏖️"
        elif 'evaluación' in urgente_clean.lower() or 'test' in urgente_clean.lower() or 'examen' in urgente_clean.lower() or 'english' in urgente_clean.lower():
            emoji = "📝"
        else:
            emoji = "📌"
        
        mensaje += f"• {emoji} {urgente_clean}\n"
    
    mensaje += f"\n📆 Próximas Evaluaciones ({len(valen_data['evaluaciones'])} total):\n\n"
    for eval in valen_data['evaluaciones'][:8]:
        mensaje += f"• {eval}\n"
    
    if valen_data['asuetos']:
        mensaje += f"\n📅 Asuetos: {', '.join(valen_data['asuetos'][:4])}\n"
    
    if valen_data['mensajes']:
        mensaje += f"\n💬 Mensajes ({len(valen_data['mensajes'])}):\n\n"
        for msg in valen_data['mensajes'][:5]:  # Limitar a 5 para Valen
            mensaje += f"• {msg['materia']} ({msg['fecha']}): \"{msg['texto']}\"\n"
    
    mensaje += "\n───\n"
    mensaje += f"\n📊 Resumen: Benja: {len(benja_data['evaluaciones'])} evaluaciones, {len(benja_data['urgentes'])} urgentes, {len(benja_data['mensajes'])} mensajes | Valen: {len(valen_data['evaluaciones'])} evaluaciones, {len(valen_data['urgentes'])} urgentes, {len(valen_data['mensajes'])} mensajes"
    
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