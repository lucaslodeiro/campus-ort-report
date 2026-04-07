#!/usr/bin/env python3
"""
Wrapper para generar reportes de Campus ORT con formato Telegram
Genera reportes de Benja y Valen y los formatea para envío por Telegram
"""

import subprocess
import sys
import re
import json
import os
from datetime import datetime
from pathlib import Path

SKILL_PATH = "/usr/local/lib/node_modules/openclaw/skills/campus-ort-report"
REPORT_BENJA = "/tmp/reporte_academico_benja.txt"
REPORT_VALEN = "/tmp/reporte_academico_valen.txt"
TASKS_BENJA = "/tmp/tareas_benja.json"
TASKS_VALEN = "/tmp/tareas_valen.json"

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
        'otros': [],
        'tareas': []
    }
    
    # Cargar tareas desde JSON si existe
    tasks_file = filepath.replace('reporte_academico_', 'tareas_').replace('.txt', '.json')
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r') as f:
                data['tareas'] = json.load(f)
        except:
            pass
    
    # Extraer nombre y curso
    nombre_match = re.search(r'📚\s+(\w+)\s+-\s+(.+?)\n', content)
    if nombre_match:
        data['nombre'] = nombre_match.group(1)
        data['curso'] = nombre_match.group(2).strip()
    
    # Extraer líneas con eventos (buscar por patrón de fecha)
    for line in content.split('\n'):
        line = line.strip()
        
        # Buscar líneas con formato: emoji fecha - título (categoría)
        # El emoji puede ser 🏖️ (beach), 📚 (books), 📝 (memo), 📌 (pushpin)
        # Usar patrón más simple que busque la estructura fecha - titulo (categoria)
        match = re.search(r'(\d{2}/\d{2}/\d{4})\s+-\s+(.+)', line)
        if match and any(emoji in line for emoji in ['🏖', '📚', '📝', '📌']):
            fecha = match.group(1)
            resto = match.group(2)
            
            # Extraer categoría del final si existe
            cat_match = re.search(r'\s*\(([^)]+)\)$', resto)
            if cat_match:
                categoria = cat_match.group(1).lower()
                titulo = resto[:cat_match.start()].strip()
            else:
                categoria = 'otro'
                titulo = resto
            
            line_formatted = f"{fecha} - {titulo} ({categoria.capitalize()})"
            
            # Usar categoría directamente del reporte (viene de los colores HTML)
            # Mapeo de categorías del scraper a secciones del reporte
            if categoria in ['examenes', 'entregas']:
                data['evaluaciones'].append(line_formatted)
            elif categoria in ['feriados']:
                data['asuetos'].append(line_formatted)
            elif categoria in ['academico', 'conmemoraciones', 'otro']:
                data['otros'].append(line_formatted)
            else:
                data['otros'].append(line_formatted)
    
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
    
    # TAREAS PENDIENTES
    if benja_data['tareas']:
        mensaje += "\n📚 Tareas Pendientes:\n\n"
        for tarea in benja_data['tareas'][:10]:
            mensaje += f"• {tarea['materia']}: {tarea['pending']} pendiente(s)\n"
    
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
    
    # TAREAS PENDIENTES
    if valen_data['tareas']:
        mensaje += "\n📚 Tareas Pendientes:\n\n"
        for tarea in valen_data['tareas'][:10]:
            mensaje += f"• {tarea['materia']}: {tarea['pending']} pendiente(s)\n"
    
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
    
    # Contar total de tareas pendientes
    total_tareas_benja = sum(t['pending'] for t in benja_data['tareas'])
    total_tareas_valen = sum(t['pending'] for t in valen_data['tareas'])
    
    mensaje += "\n───\n"
    mensaje += f"\n📊 Resumen: Benja: {len(benja_data['evaluaciones'])} eval, {len(benja_data['asuetos'])} asuetos, {total_tareas_benja} tareas pendientes | Valen: {len(valen_data['evaluaciones'])} eval, {len(valen_data['asuetos'])} asuetos, {total_tareas_valen} tareas pendientes"
    
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
    
    # Enviar mensaje por Telegram
    print("5. Enviando mensaje por Telegram...")
    try:
        # Guardar mensaje en archivo temporal
        msg_file = "/tmp/telegram_msg.txt"
        with open(msg_file, 'w') as f:
            f.write(mensaje)
        
        # Usar shell con el mensaje leído del archivo
        cmd = f'/usr/local/bin/openclaw message send -t 7527142707 --message "$(cat {msg_file})"'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ Mensaje enviado por Telegram")
        else:
            print(f"⚠ No se pudo enviar automáticamente: {result.stderr}")
    except Exception as e:
        print(f"⚠ Error enviando mensaje: {e}")
    
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