#!/usr/bin/env python3
"""
ORT Campus Report Generator Skill V3 - Complete Academic Report
Generates comprehensive academic reports for ORT Campus students
Versión con filtrado académico y formato jerárquico
"""

import asyncio
import argparse
import sys
import os
import re
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import OrtCampusScraperV2 as OrtCampusScraper, get_credentials_from_1password


def get_emoji_for_event(evt_type: str, title: str = "") -> str:
    """Get appropriate emoji based on event type and title"""
    title_lower = title.lower()
    
    # Holidays and breaks
    if any(word in title_lower for word in ['pesaj', 'asueto', 'vacaciones', 'feriado', 'fin de', 'iom']):
        return '🏖️'
    
    # Evaluations
    if evt_type == 'examen' or any(word in title_lower for word in ['evaluación', 'evaluacion', 'examen', 'prueba', 'parcial', 'test']):
        return '📝'
    
    # Deliveries/Assignments
    if evt_type == 'entrega' or 'entrega' in title_lower:
        return '📚'
    
    return '📌'


def format_date_spanish(date_obj) -> str:
    """Format date in Spanish with day name"""
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
              'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
    day_name = days[date_obj.weekday()]
    month_name = months[date_obj.month - 1]
    
    return f"{day_name} {date_obj.day} de {month_name}"


def truncate_text(text: str, max_length: int = 60) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) > max_length:
        return text[:max_length - 3] + '...'
    return text


async def generate_academic_report(student_name: str, days_back: int = 15):
    """Generate complete academic report for a student"""
    
    today = datetime.now()
    today_str = today.strftime('%d/%m/%Y')
    
    print(f"=== Generating Academic Report for {student_name} ===\n")
    
    # Get credentials from 1Password
    creds_item = f"ORT Campus - {student_name}"
    username, password = get_credentials_from_1password(creds_item)
    
    if not username or not password:
        print(f"✗ Failed to get credentials for {student_name}")
        return False
    
    scraper = OrtCampusScraper()
    await scraper.init()
    
    try:
        # Login
        success = await scraper.login(username, password)
        if not success:
            print("✗ Login failed")
            return False
        
        print("✓ Login successful\n")
        
        # Extract pizarron and private messages (academic only, last 15 days)
        print(f"Extracting academic messages (last {days_back} days)...")
        messages = await scraper.get_all_pizarron_messages(days_back=days_back)
        print(f"✓ Found {len(messages)} academic messages\n")
        
        # Extract calendar automatically
        print("Extracting calendar...")
        calendar_events = await scraper.get_calendar_auto()
        print(f"✓ Found {len(calendar_events)} calendar events\n")
        
        # Detect grade from username prefix
        grade_info = "7° año GA7E" if username.startswith("53") else "2° año NE2N"
        
        # Categorize events
        holidays = [e for e in calendar_events if any(word in e['title'].lower() for word in ['pesaj', 'asueto', 'vacaciones', 'feriado', 'iom'])]
        evaluations = [e for e in calendar_events if e['type'] in ['examen', 'entrega'] and e not in holidays]
        other_events = [e for e in calendar_events if e not in holidays and e not in evaluations]
        
        # URGENT events (next 7 days)
        urgent = [e for e in calendar_events if 0 <= (e['date_obj'] - today).days <= 7]
        
        # Build improved report with table format
        lines = [
            "═══════════════════════════════════════════════════════════",
            f"📚 {student_name.upper()} - {grade_info}",
            f"📅 {format_date_spanish(today)}",
            "═══════════════════════════════════════════════════════════",
            "",
        ]
        
        # URGENT section
        if urgent:
            lines.extend([
                "🚨 URGENTE - Próximos 7 días",
                "───────────────────────────────────────────────────────────",
            ])
            
            for evt in urgent:
                emoji = get_emoji_for_event(evt['type'], evt['title'])
                # Comparar solo fechas (sin hora/timezone) para evitar problemas de offset
                evt_date = evt['date_obj'].date()
                today_date = today.date()
                days_left = (evt_date - today_date).days
                days_text = "HOY" if days_left == 0 else f"en {days_left} día{'s' if days_left != 1 else ''}"
                
                materia_display = evt['materia'] if evt['materia'] != 'No especificada' else ''
                title_display = truncate_text(evt['title'], 45)
                
                if materia_display:
                    lines.append(f"{emoji} {evt['date']} ({days_text}) - {materia_display}")
                else:
                    lines.append(f"{emoji} {evt['date']} ({days_text}) - {title_display}")
                
                # Show detail if different from title
                detail = evt.get('detalle', '')
                if detail and detail != evt['title'] and len(detail) > 5:
                    detail_clean = truncate_text(detail, 50)
                    lines.append(f"   └─ {detail_clean}")
            
            lines.append("")
        
        # UPCOMING EVALUATIONS TABLE
        if evaluations:
            lines.extend([
                "📆 Próximas Evaluaciones",
                "───────────────────────────────────────────────────────────",
            ])
            
            # Sort by date
            evaluations.sort(key=lambda x: x['date_obj'])
            
            for evt in evaluations[:10]:
                emoji = get_emoji_for_event(evt['type'], evt['title'])
                tipo = "Evaluación" if evt['type'] == 'examen' else "Entrega"
                # Comparar solo fechas (sin hora/timezone)
                evt_date = evt['date_obj'].date()
                today_date = today.date()
                days_left = (evt_date - today_date).days
                
                materia = evt['materia'] if evt['materia'] != 'No especificada' else tipo
                
                lines.append(f"{emoji} {evt['date']} ({days_left} días) - {materia}")
                
                # Show title detail if available and different
                if evt['title'] and evt['title'] != materia and len(evt['title']) > 5:
                    title_short = truncate_text(evt['title'], 40)
                    lines.append(f"   └─ {title_short}")
            
            lines.append("")
        
        # HOLIDAYS/ASUETOS
        if holidays:
            lines.extend([
                "📅 Asuetos y Feriados",
                "───────────────────────────────────────────────────────────",
            ])
            
            for evt in holidays:
                emoji = get_emoji_for_event(evt['type'], evt['title'])
                days_left = (evt['date_obj'] - today).days
                title_short = truncate_text(evt['title'], 40)
                lines.append(f"{emoji} {evt['date']} (en {days_left} días) - {title_short}")
            
            lines.append("")
        
        # OTHER EVENTS (if any)
        if other_events:
            other_urgent = [e for e in other_events if 0 <= (e['date_obj'] - today).days <= 30]
            if other_urgent:
                lines.extend([
                    "📋 Otros Eventos Importantes",
                    "───────────────────────────────────────────────────────────",
                ])
                
                for evt in other_events[:5]:
                    emoji = get_emoji_for_event(evt['type'], evt['title'])
                    days_left = (evt['date_obj'] - today).days
                    materia = evt['materia'] if evt['materia'] != 'No especificada' else ''
                    title_short = truncate_text(evt['title'], 35)
                    
                    if materia:
                        lines.append(f"{emoji} {evt['date']} - {materia}: {title_short}")
                    else:
                        lines.append(f"{emoji} {evt['date']} - {title_short}")
                
                lines.append("")
        
        # ACADEMIC MESSAGES (filtered and grouped by materia)
        if messages:
            lines.extend([
                "💬 Mensajes Académicos Recientes (últimos 15 días)",
                "───────────────────────────────────────────────────────────",
            ])
            
            # Group by materia
            by_materia = {}
            for msg in messages:
                materia = msg.get('materia', 'General')
                if materia not in by_materia:
                    by_materia[materia] = []
                by_materia[materia].append(msg)
            
            # Show top 2 messages per materia
            for materia, msgs in sorted(by_materia.items())[:6]:
                lines.append(f"\n📌 {materia}")
                for msg in msgs[:2]:
                    date_short = msg['date'].split(' ')[0] if ' ' in msg['date'] else msg['date']
                    content_short = truncate_text(msg['content'], 55)
                    source_icon = '💬' if msg.get('source') == 'pizarron' else '✉️'
                    lines.append(f"   {source_icon} {date_short}: {content_short}")
                
                if len(msgs) > 2:
                    lines.append(f"   ... y {len(msgs) - 2} mensajes más")
            
            lines.append("")
        
        # SUMMARY BAR
        urgent_count = len([e for e in calendar_events if 0 <= (e['date_obj'] - today).days <= 7])
        total_evals = len(evaluations)
        
        lines.extend([
            "───────────────────────────────────────────────────────────",
            f"📊 Resumen: {total_evals} evaluaciones | {urgent_count} urgentes | {len(messages)} mensajes",
            "═══════════════════════════════════════════════════════════",
        ])
        
        report = "\n".join(lines)
        
        # Save report
        output_file = f"/tmp/reporte_academico_{student_name.lower()}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(report)
        print(f"\n✅ Report saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await scraper.close()


def main():
    parser = argparse.ArgumentParser(description="Generate ORT Campus Academic Report")
    parser.add_argument("--student", required=True, help="Student name (e.g., 'Benja', 'Valen')")
    parser.add_argument("--days", type=int, default=15, help="Days back for messages (default: 15)")
    
    args = parser.parse_args()
    
    asyncio.run(generate_academic_report(args.student, args.days))


if __name__ == "__main__":
    main()
