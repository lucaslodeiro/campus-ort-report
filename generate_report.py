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
        
        # Messages extraction disabled - only calendar events reported
        
        # Extract calendar automatically (using iCal feed)
        print("Extracting calendar...")
        calendar_events = await scraper.get_calendar_ical()
        print(f"✓ Found {len(calendar_events)} calendar events\n")
        
        # Detect grade from username prefix
        grade_info = "7° año GA7E" if username.startswith("53") else "2° año NE2N"
        
        # Categorize events
        holidays = [e for e in calendar_events if any(word in e['title'].lower() for word in ['pesaj', 'asueto', 'vacaciones', 'feriado', 'iom'])]
        evaluations = [e for e in calendar_events if e['type'] in ['examen', 'entrega'] and e not in holidays]
        other_events = [e for e in calendar_events if e not in holidays and e not in evaluations]
        
        # URGENT events (next 7 days)
        # Filter events for next 15 days
        upcoming_events = [e for e in calendar_events 
                          if 0 <= (e['date_obj'] - today).days <= 15]
        
        # Build improved report with table format
        lines = [
            "═══════════════════════════════════════════════════════════",
            f"📚 {student_name.upper()} - {grade_info}",
            f"📅 {format_date_spanish(today)}",
            "═══════════════════════════════════════════════════════════",
            "",
        ]
        
        # Get all upcoming events (sorted by date)
        upcoming_events = [e for e in calendar_events 
                          if 0 <= (e['date_obj'] - today).days <= 15]
        upcoming_events.sort(key=lambda x: x['date_obj'])
        
        # EVENTOS PRÓXIMOS (15 días) - Sección única con categoría LLM
        if upcoming_events:
            lines.extend([
                "📅 PRÓXIMOS EVENTOS (Próximos 15 días)",
                "───────────────────────────────────────────────────────────",
            ])
            
            for evt in upcoming_events:
                emoji = get_emoji_for_event(evt['type'], evt['title'])
                title = evt['title']
                categoria = evt.get('categoria', 'Otro')
                lines.append(f"{emoji} {evt['date']} - {title} ({categoria})")
            
            lines.append("")
        
        # SUMMARY BAR
        urgent_count = len([e for e in calendar_events if 0 <= (e['date_obj'] - today).days <= 7])
        total_evals = len([e for e in calendar_events if e['type'] in ['examen', 'entrega']])
        
        lines.extend([
            "───────────────────────────────────────────────────────────",
            f"📊 Resumen: {len(upcoming_events)} eventos | {total_evals} evaluaciones | {urgent_count} urgentes",
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
