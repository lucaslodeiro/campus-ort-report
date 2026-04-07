"""
ORT Campus Scraper V3 - Improved with private messages and academic filtering
"""

import asyncio
import os
import re
import subprocess
import urllib.request
from playwright.async_api import async_playwright
from typing import Optional, List, Dict
import json
from datetime import datetime, timedelta


async def categorize_events_batch(events: List[Dict]) -> List[str]:
    """Categorize multiple events using keyword matching (faster and reliable)"""
    
    if not events:
        return []
    
    # Use keyword matching - faster and more reliable for obvious cases
    categories = []
    for evt in events:
        title_lower = (evt.get('title', '') + " " + evt.get('description', '')).lower()
        
        # Check for Iom first (conmemoraciones, not feriados)
        if any(w in title_lower for w in ['iom hashoa', 'iom hazikaron', 'iom haatzmaut']):
            categories.append('Conmemoraciones')
        elif any(w in title_lower for w in ['pesaj', 'asueto', 'vacaciones', 'feriado', 'shavuot', 'rosh', 'yom']):
            categories.append('Feriado')
        elif any(w in title_lower for w in ['evaluacion', 'evaluación', 'examen', 'prueba', 'parcial', 'test', 'oral', 'escrito']):
            categories.append('Examen')
        elif any(w in title_lower for w in ['entrega', 'assignment', 'tarea', 'tp', 'práctico', 'proyecto', 'informe']):
            categories.append('Entrega')
        elif any(w in title_lower for w in ['charla', 'reunion', 'reunión', 'actividad', 'conmemoración', 'conmemoracion']):
            categories.append('Evento Academico')
        else:
            categories.append('Otro')
    
    return categories


def get_credentials_from_1password(item_name: str) -> tuple:
    """Get username and password from 1Password CLI"""
    try:
        if not os.getenv("OP_SERVICE_ACCOUNT_TOKEN"):
            raise Exception("OP_SERVICE_ACCOUNT_TOKEN not set")
        
        result = subprocess.run(
            ["op", "item", "list", "--vault", "Klaw", "--format", "json"],
            capture_output=True, text=True, check=True
        )
        items = json.loads(result.stdout)
        
        item_id = None
        for item in items:
            if item_name.lower() in item.get("title", "").lower():
                item_id = item["id"]
                break
        
        if not item_id:
            raise Exception(f"Item '{item_name}' not found in 1Password")
        
        result = subprocess.run(
            ["op", "item", "get", item_id, "--vault", "Klaw", "--format", "json"],
            capture_output=True, text=True, check=True
        )
        item_data = json.loads(result.stdout)
        
        username = None
        password = None
        
        for field in item_data.get("fields", []):
            if field.get("id") == "username":
                username = field.get("value")
            elif field.get("id") == "password":
                password = field.get("value")
        
        return username, password
        
    except Exception as e:
        print(f"Error getting credentials from 1Password: {e}")
        return None, None


# Academic keywords for filtering messages
ACADEMIC_KEYWORDS = [
    'tarea', 'tareas', 'deberes',
    'evaluación', 'evaluacion', 'examen', 'examenes', 'exámenes',
    'prueba', 'pruebas', 'parcial', 'parciales',
    'entrega', 'entregas', 'trabajo práctico', 'trabajo practico', 'tp',
    'actividad', 'actividades',
    'calificación', 'calificacion', 'nota', 'notas',
    'carpeta', 'carpetas',
    'libro', 'libros', 'página', 'pagina', 'ejercicio', 'ejercicios',
    'práctico', 'practico', 'teórico', 'teorico',
    'recuperatorio', 'recuperatorios',
    'fecha', 'fechas',
    'leer', 'estudiar', 'repasar',
    'trabajo', 'trabajos',
    'proyecto', 'proyectos',
    'presentación', 'presentacion',
    'debate', 'informe', 'resumen',
]


def is_academic_message(content: str) -> bool:
    """Check if message is academic-related"""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in ACADEMIC_KEYWORDS)


def extract_materia_from_group(group_name: str) -> str:
    """Extract materia name from group name"""
    # Common patterns in ORT group names
    group_lower = group_name.lower()
    
    materias_map = {
        'biologia': 'Biología',
        'biología': 'Biología',
        'matematica': 'Matemática',
        'matemática': 'Matemática',
        'lengua': 'Lengua y Literatura',
        'literatura': 'Lengua y Literatura',
        'historia': 'Historia',
        'geografia': 'Geografía',
        'geografía': 'Geografía',
        'ingles': 'Inglés',
        'inglés': 'Inglés',
        'tecnologia': 'Tecnología',
        'tecnología': 'Tecnología',
        'etica': 'Ética',
        'ética': 'Ética',
        'sociales': 'Sociales',
        'ciencias naturales': 'Ciencias Naturales',
        'naturales': 'Ciencias Naturales',
        'arte': 'Arte',
        'artes': 'Arte',
        'educacion fisica': 'Ed. Física',
        'educación física': 'Ed. Física',
        'ed fisica': 'Ed. Física',
        'ed. fisica': 'Ed. Física',
        'fisica': 'Ed. Física',
        'física': 'Ed. Física',
        'educacion judia': 'Educación Judía',
        'educación judía': 'Educación Judía',
    }
    
    for key, value in materias_map.items():
        if key in group_lower:
            return value
    
    # Try to extract from pattern "Materia X Curso"
    if ' - ' in group_name:
        parts = group_name.split(' - ')
        if len(parts) > 0:
            return parts[0].strip()
    
    return group_name


class OrtCampusScraperV2:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def init(self):
        """Initialize browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self.page = await self.context.new_page()

    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self, username: str, password: str) -> bool:
        """Login to campus"""
        try:
            print(f"Logging in as {username}...")
            
            await self.page.goto("https://campus.ort.edu.ar/", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Click user icon
            user_selectors = [
                "i.material-icons:has-text('person')",
                "i.material-icons.md-dark",
            ]
            
            clicked = False
            for sel in user_selectors:
                try:
                    elem = await self.page.query_selector(sel)
                    if elem:
                        await elem.click()
                        clicked = True
                        break
                except:
                    continue
            
            await asyncio.sleep(3)
            
            # Fill login form
            await self.page.fill("input[type='text']", username)
            await self.page.fill("input[type='password']", password)
            await self.page.click("input[type='submit']")
            
            await asyncio.sleep(5)
            
            # Check if logged in
            current_url = self.page.url
            if "secundaria" in current_url or "primaria" in current_url:
                print(f"✓ Login successful")
                return True
            
            return False
                
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False

    async def get_dashboard_tareas(self) -> List[Dict]:
        """Scrape dashboard for pending assignments/tasks"""
        tareas = []
        try:
            print("\n📋 Scraping dashboard for tasks...")
            await self.page.goto("https://campus.ort.edu.ar/dashboard/")
            await asyncio.sleep(5)
            
            # Get HTML content
            html = await self.page.content()
            
            # Find all conclusionEstado elements with their positions
            conclusion_pattern = r'<p[^>]*id="conclusionEstado-(\d+)"[^>]*>'
            conclusions = []
            for match in re.finditer(conclusion_pattern, html):
                try:
                    pos = match.start()
                    estado_id = match.group(1)
                    # Get the text content after this element - look for the closing </p>
                    start_content = match.end()
                    end_pos = html.find('</p>', start_content)
                    if end_pos > 0:
                        # Extract content between <p> and </p>
                        content = html[start_content:end_pos]
                        # Remove HTML tags
                        text = re.sub(r'<[^>]+\u003e', ' ', content).strip()
                        text = re.sub(r'\s+', ' ', text)
                        if text:
                            conclusions.append((pos, estado_id, text))
                            print(f"   DEBUG conclusion {estado_id}: {text[:80]}...")
                except Exception as e:
                    continue
            
            print(f"   Found {len(conclusions)} conclusion elements")
            
            # Find all materia titles with their positions
            materia_pattern = r'<p[^>]*class="[^"]*dsb[^"]*bold[^"]*"[^>]*>([^<]+)</p>'
            materias = []
            for match in re.finditer(materia_pattern, html):
                pos = match.start()
                nombre = match.group(1).strip()
                materias.append((pos, nombre))
            
            print(f"   Found {len(materias)} materia titles")
            
            # Match each conclusion with its nearest materia (the one just before it)
            for conclusion in conclusions:
                try:
                    conclusion_pos, estado_id, text = conclusion
                    
                    # Check if this conclusion has "Ya entregaste"
                    if "ya entregaste" not in text.lower():
                        continue
                    
                    # Parse the numbers
                    match = re.search(r'(\d+)\s*<strong>\s*de\s*</strong>\s*(\d+)', text, re.IGNORECASE)
                    if not match:
                        match = re.search(r'(\d+)\s+de\s+(\d+)', text, re.IGNORECASE)
                    if not match:
                        continue
                    
                    completed = int(match.group(1))
                    total = int(match.group(2))
                    pending = total - completed
                    
                    if pending > 0:
                        # Find the closest materia before this conclusion
                        materia_nombre = f"Materia {estado_id}"
                        closest_materia = None
                        closest_dist = float('inf')
                        
                        for materia_pos, materia_name in materias:
                            if materia_pos < conclusion_pos:
                                dist = conclusion_pos - materia_pos
                                if dist < closest_dist:
                                    closest_dist = dist
                                    closest_materia = materia_name
                        
                        if closest_materia:
                            materia_nombre = closest_materia
                        
                        tareas.append({
                            "materia": materia_nombre,
                            "pending": pending,
                            "completed": completed,
                            "total": total,
                            "status_text": f"Ya entregaste {completed} de {total}"
                        })
                        print(f"   📌 {materia_nombre}: {pending} pendiente(s)")
                        
                except Exception as e:
                    continue
            
            print(f"   ✓ Found {len(tareas)} subjects with pending tasks")
            return tareas
            
        except Exception as e:
            print(f"✗ Error scraping dashboard: {e}")
            import traceback
            traceback.print_exc()
            return []
            traceback.print_exc()
            return []

    async def get_all_groups(self) -> List[Dict]:
        """Get all groups with their correct IDs"""
        groups = []
        try:
            await self.page.goto("https://campus.ort.edu.ar/grupos/")
            await asyncio.sleep(3)
            
            # Extract group links with IDs
            links = await self.page.query_selector_all("a[href*='/grupo/']")
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    text = await link.text_content()
                    if href and text:
                        # Extract ID from URL
                        match = re.search(r'/grupo/(\d+)/', href)
                        if match:
                            group_id = match.group(1)
                            # Clean name
                            name = text.strip()
                            if name and len(name) > 3:
                                groups.append({
                                    "name": name,
                                    "id": group_id,
                                    "url": f"https://campus.ort.edu.ar/grupo/{group_id}",
                                    "materia": extract_materia_from_group(name)
                                })
                except:
                    continue
            
            # Remove duplicates by ID
            unique_groups = []
            seen_ids = set()
            for g in groups:
                if g["id"] not in seen_ids and g["name"] not in ["Grupos", "Mi Curso"]:
                    unique_groups.append(g)
                    seen_ids.add(g["id"])
            
            print(f"✓ Found {len(unique_groups)} unique groups")
            return unique_groups
            
        except Exception as e:
            print(f"✗ Error getting groups: {e}")
            return []

    async def extract_pizarron_messages(self, group: Dict, days_back: int = 15) -> List[Dict]:
        """Extract academic messages from a group's pizarron"""
        messages = []
        
        try:
            print(f"\n📚 Processing: {group['name']}")
            
            # Navigate to group
            await self.page.goto(group['url'])
            await asyncio.sleep(4)
            
            # Get HTML content
            html = await self.page.content()
            
            # Parse messages from HTML using regex
            message_pattern = r'itemPizarronGrupo.*?<span class="bold">([^<]+).*?fechaHoraMensaje[^>]*>([\d/]+ \d+:\d+).*?contMensaje[^>]*>(.*?)</div>'
            
            matches = re.findall(message_pattern, html, re.DOTALL)
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for author, date_str, content_html in matches:
                # Clean content HTML
                content = re.sub(r'<[^>]+>', ' ', content_html)
                content = re.sub(r'\s+', ' ', content).strip()
                content = content.replace('\xa0', ' ')  # Remove &nbsp;
                
                if content and len(content) > 10:
                    # Parse date
                    try:
                        msg_date = datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
                        if msg_date < cutoff_date:
                            continue  # Skip old messages
                    except:
                        continue
                    
                    # Only keep academic messages
                    if is_academic_message(content):
                        messages.append({
                            "group": group['name'],
                            "materia": group.get('materia', group['name']),
                            "author": author.strip(),
                            "date": date_str.strip(),
                            "date_obj": msg_date.strftime("%Y-%m-%d"),
                            "content": content[:500],
                            "source": "pizarron",
                            "is_academic": True
                        })
            
            if messages:
                print(f"  ✓ Found {len(messages)} academic messages")
            else:
                print(f"  ℹ️ No academic messages found")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        return messages

    async def get_private_messages(self, days_back: int = 15) -> List[Dict]:
        """Extract academic messages from private/direct messages"""
        messages = []
        
        try:
            print("\n📩 Checking private messages...")
            
            # Navigate to messages page
            await self.page.goto("https://campus.ort.edu.ar/mensajes")
            await asyncio.sleep(4)
            
            # Get HTML content
            html = await self.page.content()
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Parse private messages from the collection list
            # Pattern based on actual HTML structure:
            # <li id="thread_XXX" ...>...<p class="title bold...">Author</p>...<p class="grey-text">Date</p>...<p class="italic mensaje_resumen">Content</p>...</li>
            
            # Find all message threads
            thread_pattern = r'<li[^>]*id="thread_\d+"[^>]*>.*?<p[^>]*class="[^"]*title[^"]*bold[^"]*"[^>]*>([^<]+)</p>.*?<p[^>]*class="[^"]*grey-text[^"]*"[^>]*>([^<]+)</p>.*?<p[^>]*class="[^"]*mensaje_resumen[^"]*"[^>]*>(.*?)</p>.*?</li>'
            
            matches = re.findall(thread_pattern, html, re.DOTALL | re.IGNORECASE)
            
            for author, date_str, content_html in matches:
                # Clean content
                content = re.sub(r'<[^>]+>', ' ', content_html)
                content = re.sub(r'\s+', ' ', content).strip()
                content = content.replace('\xa0', ' ').replace('\n', ' ')
                
                if content and len(content) > 10:
                    # Parse date - format: "Sábado, 13 de Diciembre de 2025 a las 08:49pm"
                    msg_date = None
                    try:
                        # Extract date components
                        date_match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', date_str, re.IGNORECASE)
                        if date_match:
                            day = int(date_match.group(1))
                            month_str = date_match.group(2).lower()
                            year = int(date_match.group(3))
                            
                            # Map Spanish month names to numbers
                            months = {
                                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                            }
                            month = months.get(month_str, 0)
                            
                            if month > 0:
                                msg_date = datetime(year, month, day)
                                
                        # Alternative format: DD/MM/YYYY
                        if not msg_date:
                            alt_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
                            if alt_match:
                                day = int(alt_match.group(1))
                                month = int(alt_match.group(2))
                                year = int(alt_match.group(3))
                                msg_date = datetime(year, month, day)
                    except Exception as e:
                        continue
                    
                    if msg_date and msg_date >= cutoff_date:
                        # Format date as DD/MM/YYYY
                        formatted_date = msg_date.strftime("%d/%m/%Y")
                        
                        # Only keep academic messages
                        if is_academic_message(content):
                            messages.append({
                                "group": "Mensajes Privados",
                                "materia": extract_materia_from_group(author.strip()),
                                "author": author.strip(),
                                "date": formatted_date,
                                "date_obj": msg_date.strftime("%Y-%m-%d"),
                                "content": content[:500],
                                "source": "privado",
                                "is_academic": True
                            })
            
            if messages:
                print(f"  ✓ Found {len(messages)} academic private messages")
            else:
                print(f"  ℹ️ No academic private messages found")
                
        except Exception as e:
            print(f"  ✗ Error getting private messages: {e}")
        
        return messages

    async def get_all_pizarron_messages(self, max_groups: int = None, days_back: int = 15) -> List[Dict]:
        """Get academic messages from all group pizarrones and private messages"""
        all_messages = []
        
        try:
            # Get all groups first
            groups = await self.get_all_groups()
            
            if max_groups:
                groups = groups[:max_groups]
            
            print(f"\n{'='*60}")
            print(f"Processing {len(groups)} groups...")
            print(f"{'='*60}")
            
            # Process each group
            for i, group in enumerate(groups):
                print(f"\n[{i+1}/{len(groups)}] ", end="")
                messages = await self.extract_pizarron_messages(group, days_back)
                all_messages.extend(messages)
            
            # Also get private messages
            private_msgs = await self.get_private_messages(days_back)
            all_messages.extend(private_msgs)
            
            # Sort by date (newest first)
            all_messages.sort(key=lambda x: x.get('date_obj', ''), reverse=True)
            
            # Save results
            with open("/tmp/all_pizarron_messages.json", "w", encoding="utf-8") as f:
                json.dump(all_messages, f, indent=2, ensure_ascii=False)
            
            print(f"\n{'='*60}")
            print(f"✅ TOTAL: {len(all_messages)} academic messages")
            print(f"💾 Saved to: /tmp/all_pizarron_messages.json")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        return all_messages

    async def get_calendar_auto(self) -> List[Dict]:
        """Automatically detect and extract calendar with materia info"""
        events = []
        try:
            print("\n🔍 Detecting calendar...")
            
            # Step 1: Click on menu icon (hamburger menu)
            print("   Step 1: Opening menu...")
            menu_selectors = [
                "i.material-icons:has-text('menu')",
                "i.material-icons.md-dark",
                "button i.material-icons",
                "[aria-label*='menú']",
                "[aria-label*='menu']",
            ]
            
            menu_clicked = False
            for selector in menu_selectors:
                try:
                    menu = await self.page.query_selector(selector)
                    if menu:
                        await menu.click()
                        await asyncio.sleep(1)
                        menu_clicked = True
                        print("   ✓ Menu opened")
                        break
                except:
                    continue
            
            if not menu_clicked:
                print("   ⚠️ Could not open menu, trying direct navigation...")
            
            # Step 2: Click on "Mi Curso"
            print("   Step 2: Looking for 'Mi Curso'...")
            mi_curso_clicked = False
            
            mi_curso_selectors = [
                "text=Mi Curso",
                "a:has-text('Mi Curso')",
                "span:has-text('Mi Curso')",
                "[href*='curso']",
            ]
            
            for selector in mi_curso_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        mi_curso_clicked = True
                        print("   ✓ Clicked on 'Mi Curso'")
                        break
                except:
                    continue
            
            if not mi_curso_clicked:
                print("   Trying direct navigation to course...")
                await self.page.goto("https://campus.ort.edu.ar/mi-curso")
                await asyncio.sleep(3)
            
            # Step 3: Click on "MÁS EVENTOS"
            print("   Step 3: Looking for 'MÁS EVENTOS'...")
            mas_eventos_clicked = False
            
            mas_eventos_selectors = [
                "text=MÁS EVENTOS",
                "text=Más eventos",
                "text=Mas eventos",
                "a:has-text('MÁS EVENTOS')",
                "button:has-text('MÁS EVENTOS')",
                "span:has-text('MÁS EVENTOS')",
                "[href*='eventos']",
                "[href*='calendario']",
            ]
            
            for selector in mas_eventos_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(3)
                        mas_eventos_clicked = True
                        print("   ✓ Clicked on 'MÁS EVENTOS'")
                        break
                except:
                    continue
            
            if not mas_eventos_clicked:
                print("   ✗ Could not navigate to calendar via 'MÁS EVENTOS'")
                return events
            
            # Get current URL for debugging
            current_url = self.page.url
            print(f"   Current URL: {current_url}")
            
            # Extract events from the calendar page
            print("   Extracting calendar events...")
            
            await asyncio.sleep(2)
            
            # Save HTML for debugging
            html = await self.page.content()
            with open("/tmp/calendar_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("   💾 Saved HTML to /tmp/calendar_page.html")
            
            # Parse HTML for events
            # New approach: find all calendar cells (td) and extract events from each
            today = datetime.now()
            
            # Pattern to find table cells with isoDay input and CalendarMesInfo
            # Structure: <td><input id="isoDay_X">...<div class="CalendarMesInfo" data-dia="X">...</div></td>
            cell_pattern = r'<td[^>]*>.*?<input[^>]*id="isoDay_(\d+)"[^>]*value="(\d{4}-\d{2}-\d{2})[^"]*"[^>]*>.*?<div[^>]*class="CalendarMesInfo"[^>]*data-dia="\1"[^>]*>(.*?)</div>\s*</td>'
            
            cells = re.findall(cell_pattern, html, re.DOTALL | re.IGNORECASE)
            
            for day_num, iso_date, content in cells:
                # Clean content
                content = content.replace('\n', ' ').replace('\t', ' ')
                
                # Skip if no events (no background-color divs)
                if 'background-color' not in content:
                    continue
                
                # Find all event divs in this cell
                # Pattern for event divs with title and span
                event_pattern = r'<div[^>]*style="[^"]*background-color:\s*#[^"]*"[^>]*title="([^"]*)"[^>]*>(.*?)</div>'
                event_matches = re.findall(event_pattern, content, re.IGNORECASE | re.DOTALL)
                
                for title, event_html in event_matches:
                    # Extract text from span
                    span_match = re.search(r'<span[^>]*>(.*?)</span>', event_html, re.DOTALL)
                    event_text = span_match.group(1).strip() if span_match else title
                    
                    title = title.strip()
                    event_text = event_text.strip() if event_text else title
                    
                    # Skip empty entries
                    if len(title) < 2 and len(event_text) < 2:
                        continue
                    
                    # Parse date
                    try:
                        date_part = iso_date.split(' ')[0] if ' ' in iso_date else iso_date
                        parts = date_part.split('-')
                        date_str = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        event_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    except:
                        continue
                    
                    # Skip past events
                    if event_date.date() < today.date():
                        continue
                    
                    # Extract background color to determine category
                    color_match = re.search(r'background-color:\s*(#[A-Fa-f0-9]{6})', content[:500], re.IGNORECASE)
                    bg_color = color_match.group(1).upper() if color_match else ''
                    
                    # Map color to category (exact colors from Campus ORT reference)
                    color_to_category = {
                        '#FF8A80': 'Feriados y Asuetos',
                        '#FFCCD3': 'Examen',
                        '#B0E0E6': 'Entregas',
                        '#AED581': 'Conmemoraciones',
                        '#AEC6CF': 'Otros',
                        '#C3D2F5': 'Calendario Académico'
                    }
                    
                    # Determine event type from category
                    categoria = color_to_category.get(bg_color, 'Otros')
                    
                    if categoria == 'Entregas':
                        evt_type = 'entrega'
                    elif categoria == 'Examen':
                        evt_type = 'examen'
                    elif categoria == 'Feriados y Asuetos':
                        evt_type = 'asueto'
                    else:
                        evt_type = 'otro'
                    
                    # Try to extract materia from the event text/title
                    materia = self._extract_materia_from_event(title + ' ' + event_text)
                    
                    events.append({
                        "date": date_str,
                        "date_obj": event_date,
                        "title": event_text[:100] if event_text else title[:100],
                        "materia": materia,
                        "type": evt_type,
                        "categoria": categoria,
                        "detalle": title
                    })
            
            # Remove duplicates
            seen = set()
            unique_events = []
            for e in events:
                key = (e['date'], e['title'])
                if key not in seen:
                    seen.add(key)
                    unique_events.append(e)
            events = unique_events
            
            # Sort by date
            events.sort(key=lambda x: x['date_obj'])
            
            if events:
                print(f"   ✓ Found {len(events)} calendar events")
                for evt in events[:5]:
                    print(f"      • {evt['date']}: {evt['title'][:50]} [{evt['materia']}]")
            else:
                print("   ⚠️ No calendar events found")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        return events

    def _extract_materia_from_event(self, text: str) -> str:
        """Extract materia from event text using keywords"""
        text_lower = text.lower()
        
        materia_keywords = {
            'biología': 'Biología',
            'biologia': 'Biología',
            'matemática': 'Matemática',
            'matematica': 'Matemática',
            'lengua': 'Lengua y Literatura',
            'literatura': 'Lengua y Literatura',
            'literature': 'Inglés',
            'historia': 'Historia',
            'geografía': 'Geografía',
            'geografia': 'Geografía',
            'inglés': 'Inglés',
            'ingles': 'Inglés',
            'english': 'Inglés',
            'tecnología': 'Tecnología',
            'tecnologia': 'Tecnología',
            'ética': 'Ética',
            'etica': 'Ética',
            'sociales': 'Sociales',
            'naturales': 'Ciencias Naturales',
            'arte': 'Arte',
            'artes': 'Arte',
            'educación física': 'Ed. Física',
            'educacion fisica': 'Ed. Física',
            'educación judía': 'Educación Judía',
            'educacion judia': 'Educación Judía',
            'fuentes': 'Fuentes',
            'química': 'Química',
            'quimica': 'Química',
            'física': 'Física',
            'fisica': 'Física',
        }
        
        for keyword, materia in materia_keywords.items():
            if keyword in text_lower:
                return materia
        
        # Check for holidays/asuetos
        if any(word in text_lower for word in ['pesaj', 'feriado', 'asueto', 'vacaciones']):
            return 'Asueto'
        
        return 'No especificada'



    async def get_calendar_ical(self) -> List[Dict]:
        """Extract calendar events from iCal feed"""
        import urllib.request
        from datetime import datetime, timedelta
        import re
        
        events = []
        try:
            print("\n📅 Extracting iCal calendar...")
            
            # Step 0: Navigate to calendar page via UI (same as get_calendar_auto)
            print("   Navigating to calendar via UI...")
            
            # Step 1: Click on menu
            menu_selectors = [
                "i.material-icons:has-text('menu')",
                "i.material-icons.md-dark",
                "button i.material-icons",
            ]
            
            for selector in menu_selectors:
                try:
                    menu = await self.page.query_selector(selector)
                    if menu:
                        await menu.click()
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            # Step 2: Click on "Mi Curso"
            mi_curso_selectors = [
                "text=Mi Curso",
                "a:has-text('Mi Curso')",
                "span:has-text('Mi Curso')",
            ]
            
            for selector in mi_curso_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            # Step 3: Click on "MÁS EVENTOS"
            mas_eventos_selectors = [
                "text=MÁS EVENTOS",
                "text=Más eventos",
                "a:has-text('MÁS EVENTOS')",
                "[href*='eventos']",
                "[href*='calendario']",
            ]
            
            for selector in mas_eventos_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        await asyncio.sleep(3)
                        break
                except:
                    continue
            
            await asyncio.sleep(2)
            
            # Step 1: Get iCal URL from the embedCode input (JavaScript-generated)
            print("   Getting iCal URL from embedCode input...")
            
            ical_url = None
            try:
                # First try: wait for the input to exist (max 10s)
                try:
                    await self.page.wait_for_selector('#embedCode', timeout=10000)
                    ical_url = await self.page.evaluate('() => document.getElementById("embedCode")?.value')
                except:
                    pass
                
                # Second try: extract from HTML directly using regex
                if not ical_url:
                    html = await self.page.content()
                    
                    # Pattern 1: Look for embedCode input with value
                    match = re.search(r'id=["\']embedCode["\'][^>]*?value=["\']([^"\']+)["\']', html, re.DOTALL | re.IGNORECASE)
                    if match:
                        ical_url = match.group(1)
                    
                    # Pattern 2: Look for any /ical/ URL
                    if not ical_url:
                        match = re.search(r'https?://[^"\'\s<>]+/ical/?[^"\'\s<>]*', html)
                        if match:
                            ical_url = match.group(0)
                    match = re.search(r'id=["\']embedCode["\'][^>]*?value=["\']([^"\']+)["\']', html, re.DOTALL | re.IGNORECASE)
                    if match:
                        ical_url = match.group(1)
                    
                    # Pattern 2: Look for any /ical/ URL
                    if not ical_url:
                        match = re.search(r'https?://[^"\'\s<>]+/ical/?[^"\'\s<>]*', html)
                        if match:
                            ical_url = match.group(0)
                
                if ical_url:
                    print(f"   ✓ Found iCal URL: {ical_url}")
            except Exception as e:
                print(f"   Error getting iCal URL: {e}")
            
            if not ical_url:
                raise Exception("iCal URL not found - embedCode input not available")
            
            # Step 2: Download iCal feed
            import urllib.request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            req = urllib.request.Request(ical_url, headers=headers)
            
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    ical_data = response.read().decode('utf-8')
            except Exception as e:
                raise Exception(f"Error downloading iCal: {e}")
            
            # Step 3: Parse iCal data
            today = datetime.now()
            
            # Parse VEVENT blocks
            vevent_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
            vevents = re.findall(vevent_pattern, ical_data, re.DOTALL)
            
            print(f"   ✓ Found {len(vevents)} events in iCal")
            
            # First pass: collect all events without categorization
            raw_events = []
            for vevent in vevents:
                try:
                    # Extract summary (title)
                    summary_match = re.search(r'SUMMARY:(.*?)(?:\r?\n|\Z)', vevent, re.DOTALL)
                    if not summary_match:
                        continue
                    
                    # Handle folded lines in iCal
                    summary = summary_match.group(1).replace('\n ', '').replace('\r\n ', '').strip()
                    
                    # Extract start date
                    dtstart_match = re.search(r'DTSTART(?:;VALUE=DATE)?[:;](\d{8})', vevent)
                    if dtstart_match:
                        date_str = dtstart_match.group(1)
                        event_date = datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                    else:
                        # Try datetime format
                        dtstart_match = re.search(r'DTSTART[:;](\d{8})T(\d{6})', vevent)
                        if dtstart_match:
                            date_str = dtstart_match.group(1)
                            event_date = datetime(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                        else:
                            continue
                    
                    # Filter: only future events (next 15 days)
                    days_diff = (event_date - today).days
                    if days_diff < 0 or days_diff > 15:
                        continue
                    
                    # Format date
                    date_formatted = f"{event_date.day:02d}/{event_date.month:02d}/{event_date.year}"
                    
                    # Extract description (optional)
                    desc_match = re.search(r'DESCRIPTION:(.*?)(?:\r?\n[\w-]+:|\Z)', vevent, re.DOTALL)
                    description = desc_match.group(1).replace('\n ', '').strip() if desc_match else ""
                    
                    raw_events.append({
                        "date": date_formatted,
                        "date_obj": event_date,
                        "title": summary[:100],
                        "description": description
                    })
                    
                except Exception as e:
                    continue
            
            print(f"   ✓ Collected {len(raw_events)} events for categorization")
            
            # Second pass: categorize all events in batch with LLM
            if raw_events:
                print(f"   Categorizing {len(raw_events)} events with LLM (batch mode)...")
                categories = await categorize_events_batch(raw_events)
                
                # Map to event type for compatibility
                type_map = {
                    'Examen': 'examen',
                    'Entrega': 'entrega', 
                    'Feriado': 'asueto',
                    'Evento Academico': 'evento_academico',
                    'Otro': 'otro'
                }
                
                for i, evt in enumerate(raw_events):
                    categoria = categories[i] if i < len(categories) else 'Otro'
                    evt_type = type_map.get(categoria, 'otro')
                    
                    events.append({
                        "date": evt["date"],
                        "date_obj": evt["date_obj"],
                        "title": evt["title"],
                        "materia": "No especificada",
                        "type": evt_type,
                        "categoria": categoria,
                        "detalle": evt["description"]
                    })
            
            # Sort by date
            events.sort(key=lambda x: x['date_obj'])
            
            print(f"   ✓ Extracted {len(events)} events for next 15 days")
            return events
            
        except Exception as e:
            print(f"✗ Error extracting iCal: {e}")
            raise



async def main():
    """Test the scraper"""
    print("=== ORT Campus Scraper V3 - Academic Messages Only ===\n")
    
    username, password = get_credentials_from_1password("ORT Campus - Benja")
    if not username or not password:
        print("✗ Failed to get credentials")
        return
    
    scraper = OrtCampusScraperV2()
    await scraper.init()
    
    try:
        success = await scraper.login(username, password)
        if not success:
            print("✗ Login failed")
            return
        
        # Get all academic messages
        messages = await scraper.get_all_pizarron_messages(max_groups=5, days_back=15)
        
        # Show sample
        if messages:
            print("\n📋 Sample academic messages:")
            for msg in messages[:3]:
                print(f"\n  📌 {msg['materia']} ({msg['source']})")
                print(f"     👤 {msg['author']}")
                print(f"     📅 {msg['date']}")
                print(f"     📝 {msg['content'][:150]}...")
        
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
