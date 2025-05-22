import requests
from bs4 import BeautifulSoup
import sqlite3
from ttkthemes import ThemedTk
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from dataclasses import dataclass
import random
import os
import tempfile
import io
import urllib.request
import ssl
import certifi
import webbrowser
from PIL import Image, ImageTk
import re
import unicodedata

@dataclass
class Monster:
    name: str
    cr: float
    type: str
    size: str
    xp: int
    ac: str = None
    hp: str = None
    speed: str = None
    str_score: int = None
    dex_score: int = None
    con_score: int = None
    int_score: int = None
    wis_score: int = None
    cha_score: int = None
    skills: str = None
    damage_resistances: str = None
    senses: str = None
    languages: str = None
    traits: str = None
    actions: str = None
    legendary_actions: str = None

CONDITIONS = {
    "Aveuglé": {"emoji": "🌀", "description": "Ne voit pas, échoue aux jets de perception visuelle, désavantage aux attaques, avantage contre elle."},
    "Charmé": {"emoji": "❤️", "description": "Ne peut pas attaquer ou nuire à la créature qui l'a charmée."},
    "Étourdi": {"emoji": "😵", "description": "Incapable d'agir ou de se déplacer, échoue aux résistances au déplacement."},
    "Inconscient": {"emoji": "💤", "description": "Incapable d'agir, aveuglé, sourd, étourdi, tombe au sol."},
    "Paralysé": {"emoji": "⚡", "description": "Incapable d'agir ou de se déplacer, étourdi, échoue aux jets de Force/Dextérité."},
    "Pétrifié": {"emoji": "🗿", "description": "Transformé en pierre, incapable d'agir, immunisé aux poisons/maladies."},
    "Poisonné": {"emoji": "🤢", "description": "Désavantage aux attaques, tests et jets de sauvegarde."},
    "Sourd": {"emoji": "🙉", "description": "Ne peut pas entendre, échoue aux jets de perception auditive."},
    "Brûlé": {"emoji": "🔥", "description": "Subit des dégâts de feu réguliers jusqu'à extinction."},
    "Couvert": {"emoji": "🛡️", "description": "Bonus à la CA et jets de Dextérité contre certaines attaques."},
}

class EncounterBuilder:
    def __init__(self):
        self.monsters = []
        self.db_path = "monsters.db"
        self.base_url_fr = "https://www.aidedd.org/dnd-filters/monstres.php"
        self.monster_cache_dir = os.path.join(tempfile.gettempdir(), "dnd_monsters")
        if not os.path.exists(self.monster_cache_dir):
            os.makedirs(self.monster_cache_dir)
        
        self.monster_info_cache = {}
        print("Monster info cache cleared at startup.")

        self.scrape_monsters()
        self.load_monsters()

    def normalize_name(self, name):
        name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
        name = name.lower().strip()
        name = re.sub(r'\s+', ' ', name)
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'û': 'u', 'ü': 'u',
            'ç': 'c'
        }
        for char, replacement in replacements.items():
            name = name.replace(char, replacement)
        return name

    def cr_to_xp(self, cr):
        cr_xp_map = {
            0: 10, 0.125: 25, 0.25: 50, 0.5: 100, 1: 200, 2: 450, 3: 700, 4: 1100,
            5: 1800, 6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900, 11: 7200,
            12: 8400, 13: 10000, 14: 11500, 15: 13000, 16: 15000, 17: 18000,
            18: 20000, 19: 22000, 20: 25000, 21: 33000, 22: 41000, 23: 50000,
            24: 62000, 25: 75000, 30: 155000
        }
        return cr_xp_map.get(cr, 0)

    def calculate_modifier(self, score):
        if score == 1:
            return -5
        elif 2 <= score <= 3:
            return -4
        elif 4 <= score <= 5:
            return -3
        elif 6 <= score <= 7:
            return -2
        elif 8 <= score <= 9:
            return -1
        elif 10 <= score <= 11:
            return 0
        elif 12 <= score <= 13:
            return 1
        elif 14 <= score <= 15:
            return 2
        elif 16 <= score <= 17:
            return 3
        elif 18 <= score <= 19:
            return 4
        elif 20 <= score <= 21:
            return 5
        return 0

    def scrape_monsters(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(self.base_url_fr, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            monster_table = soup.find('table', id='liste')
            if not monster_table:
                print("Tableau des monstres non trouvé")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS monsters
                            (normalized_name TEXT PRIMARY KEY, name TEXT, cr REAL, type TEXT, size TEXT, xp INTEGER,
                             ac TEXT, hp TEXT, speed TEXT, str_score INTEGER, dex_score INTEGER, con_score INTEGER,
                             int_score INTEGER, wis_score INTEGER, cha_score INTEGER, skills TEXT, damage_resistances TEXT,
                             senses TEXT, languages TEXT, traits TEXT, actions TEXT, legendary_actions TEXT)''')
            
            cursor.execute("SELECT normalized_name FROM monsters")
            existing_names = {row[0] for row in cursor.fetchall()}

            seen_names = set()
            monster_data = []

            for row in monster_table.find('tbody').find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 8:
                    name = cols[1].find('a').text.strip()
                    normalized_name = self.normalize_name(name)
                    
                    if normalized_name in seen_names:
                        print(f"Doublon détecté dans le scraping pour {name} (normalisé: {normalized_name}), ignoré.")
                        continue
                    seen_names.add(normalized_name)
                    
                    cr_str = cols[4].get('data-sort-value', cols[4].text.strip())
                    cr = float(cr_str.split('/')[0]) / float(cr_str.split('/')[1]) if '/' in cr_str else float(cr_str)
                    monster_type = cols[5].text.strip()
                    size_map = {1: 'TP', 2: 'P', 3: 'M', 4: 'G', 5: 'TG', 6: 'Gig'}
                    size = size_map.get(int(cols[6].get('data-sort-value', '3')), 'M')
                    xp = self.cr_to_xp(cr)
                    
                    monster_data.append((name, cr, monster_type, size, xp, normalized_name))
                    print(f"Extrait: {name} (normalisé: {normalized_name}, CR {cr}, Type: {monster_type}, Taille: {size}, XP: {xp})")

            for data in monster_data:
                name, cr, monster_type, size, xp, normalized_name = data
                if normalized_name not in existing_names:
                    cursor.execute('INSERT INTO monsters (normalized_name, name, cr, type, size, xp) VALUES (?, ?, ?, ?, ?, ?)',
                                  (normalized_name, name, cr, monster_type, size, xp))
                    print(f"Ajouté: {name} (normalisé: {normalized_name})")
                else:
                    print(f"Déjà présent: {name} (normalisé: {normalized_name}), ignoré.")
            
            conn.commit()
            conn.close()
            print("Scraping et synchronisation terminés")
        except Exception as e:
            print(f"Erreur lors du scraping : {e}")

    def load_monsters(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM monsters")
        rows = cursor.fetchall()
        seen_names = set()
        self.monsters = []
        for row in rows:
            name, cr, monster_type, size, xp = row[1:6]
            normalized_name = row[0]
            if normalized_name in seen_names:
                print(f"Doublon détecté lors du chargement: {name} (normalisé: {normalized_name}), ignoré.")
                continue
            seen_names.add(normalized_name)
            self.monsters.append(Monster(
                name=name,
                cr=cr,
                type=monster_type,
                size=size,
                xp=xp,
                ac=row[6],
                hp=row[7],
                speed=row[8],
                str_score=row[9],
                dex_score=row[10],
                con_score=row[11],
                int_score=row[12],
                wis_score=row[13],
                cha_score=row[14],
                skills=row[15],
                damage_resistances=row[16],
                senses=row[17],
                languages=row[18],
                traits=row[19],
                actions=row[20],
                legendary_actions=row[21]
            ))
            print(f"Chargé: {name} (normalisé: {normalized_name})")
        conn.close()
        print(f"Loaded {len(self.monsters)} monsters from database.")

    def extract_monster_info(self, monster_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM monsters WHERE name = ?", (monster_name,))
        monster_data = cursor.fetchone()
        conn.close()

        if monster_data and monster_data[7] is not None:
            print(f"Using database data for {monster_name} (manual creature)")
            print(f"Raw monster data: {monster_data}")

            stats = {
                "Classe d'armure": monster_data[6] if monster_data[6] else "N/A",
                "Points de vie": monster_data[7] if monster_data[7] else "N/A",
                "Vitesse": monster_data[8] if monster_data[8] else "N/A"
            }
            abilities = {
                "Force": f"{monster_data[9]} ({self.calculate_modifier(monster_data[9]):+d})" if monster_data[9] is not None else "N/A",
                "Dextérité": f"{monster_data[10]} ({self.calculate_modifier(monster_data[10]):+d})" if monster_data[10] is not None else "N/A",
                "Constitution": f"{monster_data[11]} ({self.calculate_modifier(monster_data[11]):+d})" if monster_data[11] is not None else "N/A",
                "Intelligence": f"{monster_data[12]} ({self.calculate_modifier(monster_data[12]):+d})" if monster_data[12] is not None else "N/A",
                "Sagesse": f"{monster_data[13]} ({self.calculate_modifier(monster_data[13]):+d})" if monster_data[13] is not None else "N/A",
                "Charisme": f"{monster_data[14]} ({self.calculate_modifier(monster_data[14]):+d})" if monster_data[14] is not None else "N/A"
            }
            details = []
            if monster_data[15]:
                details.append(f"Compétences: {monster_data[15]}")
            if monster_data[16]:
                details.append(f"Résistances aux dégâts: {monster_data[16]}")
            if monster_data[17]:
                details.append(f"Sens: {monster_data[17]}")
            if monster_data[18]:
                details.append(f"Langues: {monster_data[18]}")
            traits = [(trait.strip(), "") for trait in monster_data[19].split('\n') if trait.strip()] if monster_data[19] else []
            actions = [(action.strip(), "") for action in monster_data[20].split('\n') if action.strip()] if monster_data[20] else []
            legendary_actions = [(action.strip(), "") for action in monster_data[21].split('\n') if action.strip()] if monster_data[21] else []

            if not re.match(r"^\d+(?:\s*\(.*\))?$", monster_data[7] or ""):
                print(f"Warning: Invalid HP format for {monster_name}: {monster_data[7]}")
            if not re.match(r"^\d+\s*m(?:,\s*\w+\s*\d+\s*m)*$", monster_data[8] or ""):
                print(f"Warning: Invalid speed format for {monster_name}: {monster_data[8]}")
            for stat, value in abilities.items():
                if not re.match(r"^-?\d+\s*\(\+\d+\)$|^-?\d+\s*\(-\d+\)$|^-?\d+\s*\(\+0\)$", value):
                    print(f"Warning: Invalid {stat} value for {monster_name}: {value}")

            average_hp = 1
            hp_formula = monster_data[7] or ""
            print(f"HP formula for {monster_name}: {hp_formula}")
            if hp_formula:
                match = re.match(r"(\d+)(?:\s*\((?:.*)\))?", hp_formula)
                if match:
                    average_hp = int(match.group(1))
                    print(f"Extracted HP for {monster_name}: {average_hp} from formula {hp_formula}")
                else:
                    print(f"Could not parse HP for {monster_name}: {hp_formula}, defaulting to 1")
                    average_hp = 1
            else:
                print(f"No HP formula found for {monster_name}, defaulting to 1")
                average_hp = 1

            if average_hp <= 0:
                print(f"Warning: Invalid HP ({average_hp}) for {monster_name}, setting to 1")
                average_hp = 1

            monster_info = {
                'name': monster_name,
                'url': None,
                'html': f'<h2>{monster_name}</h2><p>Monstre personnalisé</p>',
                'image_urls': [],
                'hp': average_hp,
                'hp_formula': hp_formula,
                'type': monster_data[3] or '',
                'stats': stats,
                'abilities': abilities,
                'details': details,
                'traits': traits,
                'actions': actions,
                'legendary_actions': legendary_actions
            }
            print(f"Returning monster_info for {monster_name} (manual) with HP: {monster_info['hp']}")
            return monster_info

        print(f"Fetching data for {monster_name} from web (scraped creature)")
        def normalize_name(name):
            name = unicodedata.normalize('NFD', name.lower()).encode('ascii', 'ignore').decode('utf-8')
            name = name.replace(' ', '-').replace(',', '')
            replacements = {
                'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                'à': 'a', 'â': 'a', 'ä': 'a',
                'î': 'i', 'ï': 'i',
                'ô': 'o', 'ö': 'o',
                'û': 'u', 'ü': 'u',
                'ç': 'c'
            }
            for char, replacement in replacements.items():
                name = name.replace(char, replacement)
            return name
        
        base_name = normalize_name(monster_name)
        url = f"https://www.aidedd.org/dnd/monstres.php?vf={base_name}"
        print(f"Scraping URL: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            monster_block = soup.find('div', class_='jaune') or soup.find('div', class_='col1')
            if not monster_block:
                print(f"Monster block not found for {monster_name} at {url}")
                return {'name': monster_name, 'error': 'Fiche non trouvée', 'html': f'<h2>{monster_name}</h2><p>Fiche non disponible.</p>', 'image_urls': [], 'url': url}

            image_urls = []
            picture_div = soup.find('div', class_='picture')
            if picture_div:
                img = picture_div.find('img')
                if img and img.get('src'):
                    src = img['src']
                    full_url = src if src.startswith('http') else f"https://www.aidedd.org{src}"
                    image_urls.append(full_url)

            if image_urls:
                print(f"Found image URLs for {monster_name}: {image_urls}")
            else:
                print(f"No image URLs found for {monster_name} at {url}")

            stats = {}
            hp_formula = ""
            red_div = soup.find('div', class_='red')
            if red_div:
                current_key = None
                current_value = []
                for child in red_div.children:
                    if child.name == 'strong':
                        if current_key and current_value:
                            stats[current_key] = " ".join(current_value).strip()
                            if current_key == "Points de vie":
                                hp_formula = stats[current_key]
                                print(f"HP formula for {monster_name}: {hp_formula}")
                        current_key = child.text.strip()
                        current_value = []
                    elif child.name == 'br':
                        continue
                    elif child.string:
                        current_value.append(child.string.strip())
                    elif child.name == 'div':
                        continue
                if current_key and current_value:
                    stats[current_key] = " ".join(current_value).strip()
                    if current_key == "Points de vie":
                        hp_formula = stats[current_key]
                        print(f"HP formula for {monster_name}: {hp_formula}")

            average_hp = 0
            if hp_formula:
                hp_formula = hp_formula.strip()
                match = re.match(r"(\d+)(?:\s*\(.*\))?", hp_formula)
                if match:
                    average_hp = int(match.group(1))
                    print(f"Extracted HP for {monster_name}: {average_hp} from formula {hp_formula}")
                else:
                    print(f"Could not parse HP for {monster_name}: {hp_formula}")
                    average_hp = 1
            else:
                print(f"No HP formula found for {monster_name}, defaulting to 1")
                average_hp = 1

            abilities_raw = {strong.text.strip(): div.text.replace(strong.text, '').strip() for div in soup.find_all('div', class_='carac') if div.find('strong') for strong in [div.find('strong')]}
            abilities = {}
            for key, value in abilities_raw.items():
                match = re.match(r"(\d+)", value)
                if match:
                    score = int(match.group(1))
                    modifier = self.calculate_modifier(score)
                    abilities[key] = f"{score} ({modifier:+d})"
                else:
                    abilities[key] = value

            monster_data = {
                'name': monster_name,
                'url': url,
                'html': str(monster_block).replace('src="/', 'src="https://www.aidedd.org/').replace('href="/', 'href="https://www.aidedd.org/'),
                'image_urls': image_urls,
                'hp': average_hp,
                'hp_formula': hp_formula,
                'type': soup.find('div', class_='type').text.strip() if soup.find('div', class_='type') else '',
                'stats': stats,
                'abilities': abilities,
                'details': [p.text.strip() for p in soup.find_all('p') if any(kw in p.text for kw in ['Compétences', 'Résistances', 'Immunités', 'Sens', 'Langues', 'Puissance'])],
                'traits': [(p.find('strong').text.strip(), p.text.replace(p.find('strong').text, '').strip()) for p in soup.find_all('p') if p.find('strong') and p.find('em')],
                'actions': [],
                'legendary_actions': []
            }
            current_section = 'actions'
            for tag in soup.find_all(['div', 'p']):
                if 'rub' in tag.get('class', []):
                    title = tag.text.strip()
                    content = next((sib.text.strip() for sib in tag.find_next_siblings() if sib.name == 'p'), "")
                    if 'action' in title.lower():
                        current_section = 'actions'
                    elif 'légendaire' in title.lower():
                        current_section = 'legendary_actions'
                    if current_section in ['actions', 'legendary_actions']:
                        monster_data[current_section].append((title, content))

            if monster_data['hp'] <= 0:
                print(f"Warning: Invalid HP ({monster_data['hp']}) for {monster_name}, setting to 1")
                monster_data['hp'] = 1
            print(f"Returning monster_data for {monster_name} (scraped) with HP: {monster_data['hp']}")
            return monster_data
        except Exception as e:
            print(f"Erreur avec {url}: {e}")
            return {'name': monster_name, 'error': 'Fiche non trouvée', 'html': f'<h2>{monster_name}</h2><p>Fiche non disponible.</p>', 'image_urls': [], 'url': url}

    def download_and_cache_image(self, image_url):
        try:
            image_filename = os.path.join(self.monster_cache_dir, image_url.split('/')[-1])
            print(f"Attempting to download image from {image_url} to {image_filename}")
            if not os.path.exists(image_filename):
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                context = ssl.create_default_context(cafile=certifi.where())
                with urllib.request.urlopen(urllib.request.Request(image_url, headers=headers), context=context) as response:
                    with open(image_filename, 'wb') as f:
                        f.write(response.read())
                print(f"Successfully downloaded image to {image_filename}")
            return image_filename
        except Exception as e:
            print(f"Erreur lors du téléchargement de l'image {image_url}: {e}")
            return None

    def get_monster_summary(self, monster_info):
        return {k: monster_info.get(k, []) if k in ['traits', 'actions', 'legendary_actions', 'details'] else monster_info.get(k, '') for k in ['name', 'type', 'stats', 'abilities', 'details', 'traits', 'actions', 'legendary_actions']}

class EncounterApp:
    def __init__(self, root):
        self.builder = EncounterBuilder()
        self.encounter = []
        self.party = []
        self.initiative_order = []
        self.current_turn = 0
        self.round_count = 0
        self.hp_popup = None
        self.condition_tooltips = {}
        self.rename_tooltips = {}
        
        self.root = root
        self.root.title("Créateur de Rencontres D&D 5e")
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg="#F5E8C7")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", font=("Georgia", 12), foreground="#2F1E0F", background="#F5E8C7")
        style.configure("TButton", font=("Georgia", 12), foreground="#2F1E0F", background="#D9A66C", bordercolor="#8B4513", relief="flat")
        style.map("TButton", background=[('active', '#A0522D')], foreground=[('active', '#FFFFFF')])
        style.configure("Title.TLabel", font=("Georgia", 16, "bold"), foreground="#8B4513")
        style.configure("TLabelframe", background="#F5E8C7", foreground="#8B4513", font=("Georgia", 14, "bold"), relief="ridge", borderwidth=2)
        style.configure("TLabelframe.Label", background="#F5E8C7", foreground="#8B4513")
        style.configure("TEntry", font=("Georgia", 12), fieldbackground="#FFF8E1", relief="flat")
        style.configure("TSpinbox", font=("Georgia", 12), fieldbackground="#FFF8E1", relief="flat")
        style.configure("TCombobox", font=("Georgia", 12), fieldbackground="#FFF8E1", relief="flat")
        style.configure("Highlight.TLabel", font=("Georgia", 12, "bold"), foreground="#FFFFFF", background="#A0522D")
        style.configure("Green.TButton", font=("Georgia", 12), foreground="#FFFFFF", background="#6B8E23", relief="flat")
        style.map("Green.TButton", background=[('active', '#556B2F')])
        style.configure("Red.TButton", font=("Georgia", 12), foreground="#FFFFFF", background="#A52A2A", relief="flat")
        style.map("Red.TButton", background=[('active', '#8B0000')])
        style.configure("Small.TLabel", font=("Georgia", 10), foreground="#2F1E0F", background="#F5E8C7")
        style.configure("Parchment.TFrame", background="#F5E8C7")
        
        # Styles pour les barres de vie
        style.configure("Green.Horizontal.TProgressbar", troughcolor="#FFF8E1", background="#00FF00")
        style.configure("Yellow.Horizontal.TProgressbar", troughcolor="#FFF8E1", background="#FFFF00")
        style.configure("Red.Horizontal.TProgressbar", troughcolor="#FFF8E1", background="#FF0000")
        
        self.config_frame = ttk.LabelFrame(root, text="Configuration", padding=10)
        self.config_frame.pack(padx=20, pady=15, fill="both", expand=True)
        
        self.combat_frame = ttk.LabelFrame(root, text="Affrontement", padding=10)
        self.combat_frame.pack_forget()
        
        self.monster_stats_frame = ttk.LabelFrame(self.combat_frame, text="Résumé du Monstre", padding=10)
        self.monster_stats_frame.pack(side=tk.RIGHT, fill="both", padx=10, expand=True)
        self.monster_stats_frame.pack_forget()
        
        self.monster_image_label = ttk.Label(self.monster_stats_frame, background="#FFF8E1")
        self.monster_image_label.pack(pady=5)
        
        self.monster_stats_text = scrolledtext.ScrolledText(self.monster_stats_frame, height=20, width=40, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
        self.monster_stats_text.pack(fill="both", expand=True)
        
        self.toggle_detail_btn = ttk.Button(self.monster_stats_frame, text="Voir la Fiche Complète", command=self.toggle_monster_detail)
        self.toggle_detail_btn.pack(pady=10)
        self.showing_full_detail = False
        
        self.setup_config_frame()

    def setup_config_frame(self):
        self.config_frame.columnconfigure(1, weight=1)
        ttk.Label(self.config_frame, text="Nombre de PJ :", style="TLabel").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.party_size = tk.IntVar(value=4)
        ttk.Entry(self.config_frame, textvariable=self.party_size, width=5).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        ttk.Label(self.config_frame, text="Niveau des PJ :", style="TLabel").grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.party_level = tk.IntVar(value=1)
        ttk.Spinbox(self.config_frame, from_=1, to=20, textvariable=self.party_level, width=5).grid(row=0, column=3, padx=10, pady=5, sticky="w")
        
        ttk.Label(self.config_frame, text="Rechercher :", style="TLabel").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.search_var = tk.StringVar()
        ttk.Entry(self.config_frame, textvariable=self.search_var).grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        self.search_var.trace("w", self.update_monster_list)
        
        self.monster_listbox = tk.Listbox(self.config_frame, height=10, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", selectbackground="#A0522D", relief="flat")
        self.monster_listbox.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.update_monster_list()
        
        ttk.Label(self.config_frame, text="Quantité :", style="TLabel").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.quantity_var = tk.IntVar(value=1)
        ttk.Spinbox(self.config_frame, from_=1, to=99, textvariable=self.quantity_var, width=5).grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        ttk.Button(self.config_frame, text="Ajouter", command=self.add_monster).grid(row=3, column=3, padx=10, pady=5)
        
        self.encounter_text = scrolledtext.ScrolledText(self.config_frame, height=6, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
        self.encounter_text.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        
        btn_frame = ttk.Frame(self.config_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        ttk.Button(btn_frame, text="Effacer", command=self.clear_encounter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Démarrer", command=self.start_encounter).pack(side=tk.LEFT, padx=5)

    def update_monster_list(self, *args):
        search_term = self.search_var.get().lower()
        self.monster_listbox.delete(0, tk.END)
        sorted_monsters = sorted(self.builder.monsters, key=lambda m: (m.name.lower(), m.cr))
        seen_entries = set()
        for monster in sorted_monsters:
            entry = f"{monster.name} (CR {monster.cr})"
            normalized_entry = self.builder.normalize_name(monster.name)
            if search_term in monster.name.lower() and normalized_entry not in seen_entries:
                self.monster_listbox.insert(tk.END, entry)
                seen_entries.add(normalized_entry)
                print(f"Affiché: {entry} (normalisé: {normalized_entry})")

    def add_monster(self):
        selected = self.monster_listbox.curselection()
        if not selected:
            messagebox.showwarning("Aucune sélection", "Sélectionnez un monstre.")
            return
        monster_name = self.monster_listbox.get(selected[0]).split(" (CR")[0]
        monster = next((m for m in self.builder.monsters if m.name == monster_name), None)
        if monster:
            self.encounter.append((monster, self.quantity_var.get()))
            self.update_encounter_display()

    def update_encounter_display(self):
        self.encounter_text.delete(1.0, tk.END)
        total_xp = 0
        for monster, qty in self.encounter:
            xp = monster.xp * qty
            total_xp += xp
            self.encounter_text.insert(tk.END, f"{qty}x {monster.name} (CR {monster.cr}, {xp} XP)\n")
        self.encounter_text.insert(tk.END, f"\nTotal XP : {total_xp}")

    def clear_encounter(self):
        self.encounter = []
        self.update_encounter_display()

    def update_hp_bar_color(self, hp_bar, hp_current, hp_max):
        if hp_max <= 0:
            percentage = 0
        else:
            percentage = (hp_current / hp_max) * 100
        
        if percentage > 50:
            hp_bar.configure(style="Green.Horizontal.TProgressbar")
        elif percentage > 25:
            hp_bar.configure(style="Yellow.Horizontal.TProgressbar")
        else:
            hp_bar.configure(style="Red.Horizontal.TProgressbar")
        
        hp_bar.configure(value=hp_current)

    def update_hp_bar(self, index):
        hp_bar, hp_current, hp_max = self.hp_bars[index]
        try:
            current = hp_current.get()
            maximum = hp_max.get()
            if maximum <= 0:
                maximum = 1
            hp_bar.configure(maximum=maximum, value=current)
            self.update_hp_bar_color(hp_bar, current, maximum)
        except tk.TclError:
            pass

    def start_encounter(self):
        if not self.encounter or self.party_size.get() < 1:
            messagebox.showwarning("Erreur", "Ajoutez des monstres et définissez un groupe valide.")
            return
        self.config_frame.pack_forget()
        
        self.current_turn = 0
        self.round_count = 0
        self.initiative_order = []
        
        for widget in self.combat_frame.winfo_children():
            if widget != self.monster_stats_frame:
                widget.destroy()
        
        self.combat_frame.pack(padx=20, pady=15, fill="both", expand=True)
        self.monster_stats_frame.pack_forget()
        self.monster_image_label.config(image="", text="")
        
        self.initiative_order = [
            [f"PJ {i+1}", tk.IntVar(value=0), tk.IntVar(value=100), tk.IntVar(value=100), [], False, {"damage_dealt": 0, "damage_taken": 0, "healing_done": 0}]
            for i in range(self.party_size.get())
        ]
        for monster, qty in self.encounter:
            base_name = monster.name
            monster_info = self.builder.extract_monster_info(base_name)
            hp = monster_info.get('hp', 1)
            if hp <= 0:
                hp = 1
                print(f"Warning: HP for {monster.name} was {hp}, setting to 1")
            print(f"Setting HP for {monster.name}: {hp}")
            for i in range(qty):
                self.initiative_order.append([
                    f"{monster.name} {i+1}",
                    tk.IntVar(value=0),
                    tk.IntVar(value=hp),
                    tk.IntVar(value=hp),
                    [],
                    False,
                    {"damage_dealt": 0, "damage_taken": 0, "healing_done": 0}
                ])
        
        self.initiative_frame = ttk.LabelFrame(self.combat_frame, text="Initiative", padding=10)
        self.initiative_frame.pack(side=tk.LEFT, fill="y", padx=10, pady=10, expand=False)
        
        headers = ["Nom", "Initiative", "Cond.", "PV", "Barre de Vie", "Renommer"]
        for col, header in enumerate(headers):
            ttk.Label(self.initiative_frame, text=header, style="Title.TLabel").grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        
        self.hp_bars = []
        
        for i, (name, init_var, hp_current, hp_max, conditions, concentrating, _) in enumerate(self.initiative_order):
            ttk.Label(self.initiative_frame, text=name, style="TLabel").grid(row=i+1, column=0, padx=5, pady=2, sticky="w")
            init_frame = ttk.Frame(self.initiative_frame)
            init_frame.grid(row=i+1, column=1, padx=5, pady=2)
            ttk.Entry(init_frame, textvariable=init_var, width=5).pack(side=tk.LEFT)
            ttk.Button(init_frame, text="🎲", width=2, command=lambda idx=i: self.roll_initiative(self.initiative_order[idx][1])).pack(side=tk.LEFT)
            cond_btn = ttk.Button(self.initiative_frame, text="📕" if not concentrating else "📖", width=2, command=lambda idx=i: self.toggle_concentration(idx))
            cond_btn.grid(row=i+1, column=2, padx=5, pady=2)
            self.setup_condition_tooltip(cond_btn, conditions)
            hp_frame = ttk.Frame(self.initiative_frame)
            hp_frame.grid(row=i+1, column=3, padx=5, pady=2)
            ttk.Entry(hp_frame, textvariable=hp_current, width=5).pack(side=tk.LEFT)
            ttk.Label(hp_frame, text="/", style="Small.TLabel").pack(side=tk.LEFT)
            ttk.Entry(hp_frame, textvariable=hp_max, width=5).pack(side=tk.LEFT)
            
            hp_bar = ttk.Progressbar(self.initiative_frame, length=100, maximum=hp_max.get(), value=hp_current.get())
            hp_bar.grid(row=i+1, column=4, padx=5, pady=2)
            self.hp_bars.append((hp_bar, hp_current, hp_max))
            
            self.update_hp_bar_color(hp_bar, hp_current.get(), hp_max.get())
            
            hp_current.trace_add("write", lambda *args, idx=i: self.update_hp_bar(idx))
            hp_max.trace_add("write", lambda *args, idx=i: self.update_hp_bar(idx))
            
            if name.startswith("PJ"):
                rename_btn = ttk.Button(self.initiative_frame, text="✏️", width=2, command=lambda idx=i: self.show_rename_popup(idx))
                rename_btn.grid(row=i+1, column=5, padx=5, pady=2)
                self.setup_rename_tooltip(rename_btn)
            else:
                ttk.Label(self.initiative_frame, text="").grid(row=i+1, column=5, padx=5, pady=2)
        
        ttk.Button(self.initiative_frame, text="Confirmer", command=self.confirm_initiative).grid(row=len(self.initiative_order)+1, column=0, columnspan=6, pady=10)
        self.root.bind("<Return>", lambda e: self.confirm_initiative())
        
        self.order_listbox = tk.Listbox(self.combat_frame, height=10, width=40, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", selectbackground="#A0522D", relief="flat")
        self.order_listbox.pack(fill="both", padx=10, pady=10, expand=True)
        self.order_listbox.bind('<<ListboxSelect>>', self.on_select_character)
        
        nav_frame = ttk.Frame(self.combat_frame, relief="flat", borderwidth=0)
        nav_frame.pack(pady=5)
        ttk.Button(nav_frame, text="◄ Annuler", command=self.previous_turn).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="Suivant ►", command=self.next_turn).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.combat_frame, text="Retour", command=self.back_to_config).pack(pady=5)
        ttk.Button(self.combat_frame, text="Rapport", command=self.show_battle_report).pack(pady=5)

        self.update_turn_order()

    def confirm_initiative(self):
        self.initiative_order.sort(key=lambda x: x[1].get(), reverse=True)
        self.current_turn = 0
        self.round_count = 0
        self.update_turn_order()

    def roll_initiative(self, var):
        var.set(random.randint(1, 20))

    def toggle_concentration(self, index):
        self.initiative_order[index][5] = not self.initiative_order[index][5]
        self.update_turn_order()

    def update_turn_order(self):
        self.order_listbox.delete(0, tk.END)
        for i, (name, init_var, hp_current, hp_max, conditions, concentrating, _) in enumerate(self.initiative_order):
            cond_str = " ".join(CONDITIONS[c]["emoji"] for c in conditions) if conditions else "⚙"
            conc_str = "📖" if concentrating else "📕"
            prefix = "💀 " if hp_current.get() == 0 and not name.startswith("PJ") else ""
            text = f"{prefix}{name:<20} | {cond_str} | {conc_str} | PV: {hp_current.get()}/{hp_max.get()}"
            self.order_listbox.insert(tk.END, text)
            self.order_listbox.itemconfig(i, {'bg': '#A0522D' if i == self.current_turn else '#FFF8E1', 'fg': '#FFFFFF' if i == self.current_turn else '#2F1E0F'})
        
        for i, (name, _, _, _, _, concentrating, _) in enumerate(self.initiative_order):
            ttk.Label(self.initiative_frame, text=name, style="TLabel").grid(row=i+1, column=0, padx=5, pady=2, sticky="w")
            cond_btn = self.initiative_frame.grid_slaves(row=i+1, column=2)[0]
            cond_btn.config(text="📖" if concentrating else "📕")
            self.update_hp_bar(i)

    def show_condition_menu(self, index):
        window = tk.Toplevel(self.root)
        window.title(f"Conditions - {self.initiative_order[index][0]}")
        window.configure(bg="#F5E8C7")
        window.geometry("400x400")
        
        conditions = self.initiative_order[index][4]
        ttk.Label(window, text="Conditions actuelles :", style="TLabel").pack(pady=5)
        cond_list = tk.Listbox(window, height=6, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
        cond_list.pack(pady=5, fill="x", padx=10)
        for cond in conditions:
            cond_list.insert(tk.END, f"{CONDITIONS[cond]['emoji']} {cond}\n{CONDITIONS[cond]['description']}")
        if not conditions:
            cond_list.insert(tk.END, "Aucune condition")
        
        frame = ttk.Frame(window, relief="flat", borderwidth=0)
        frame.pack(pady=5, fill="x", padx=10)
        cond_var = tk.StringVar()
        ttk.Combobox(frame, textvariable=cond_var, values=list(CONDITIONS.keys())).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Ajouter", command=lambda: self.add_condition(index, cond_var.get(), cond_list, window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Supprimer toutes", command=lambda: self.remove_all_conditions(index, cond_list, window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(window, text="Fermer", command=window.destroy).pack(pady=5)

    def add_condition(self, index, condition, cond_list, window):
        if condition in CONDITIONS and condition not in self.initiative_order[index][4]:
            self.initiative_order[index][4].append(condition)
            cond_list.delete(0, tk.END)
            for cond in self.initiative_order[index][4]:
                cond_list.insert(tk.END, f"{CONDITIONS[cond]['emoji']} {cond}\n{CONDITIONS[cond]['description']}")
            self.update_turn_order()
            if window:
                window.destroy()

    def remove_all_conditions(self, index, cond_list, window):
        self.initiative_order[index][4].clear()
        cond_list.delete(0, tk.END)
        cond_list.insert(tk.END, "Aucune condition")
        self.update_turn_order()
        if window:
            window.destroy()

    def setup_condition_tooltip(self, widget, conditions):
        def show(event):
            tooltip = tk.Toplevel(self.root)
            tooltip.wm_overrideredirect(1)
            tooltip.wm_geometry(f"+{event.x_root}+{event.y_root}")
            text = "\n".join([f"{cond}: {CONDITIONS[cond]['description']}" for cond in conditions]) if conditions else "Aucune condition"
            ttk.Label(tooltip, text=text, wraplength=200, justify="left", background="#F5E8C7", foreground="#2F1E0F").pack(padx=5, pady=5)
            self.condition_tooltips[widget] = tooltip
        
        def hide(event):
            if widget in self.condition_tooltips:
                self.condition_tooltips[widget].destroy()
                del self.condition_tooltips[widget]
        
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def setup_rename_tooltip(self, widget):
        def show(event):
            tooltip = tk.Toplevel(self.root)
            tooltip.wm_overrideredirect(1)
            tooltip.wm_geometry(f"+{event.x_root}+{event.y_root}")
            ttk.Label(tooltip, text="Renommer ce PJ", wraplength=150, justify="left", background="#F5E8C7", foreground="#2F1E0F").pack(padx=5, pady=5)
            self.rename_tooltips[widget] = tooltip
        
        def hide(event):
            if widget in self.rename_tooltips:
                self.rename_tooltips[widget].destroy()
                del self.rename_tooltips[widget]
        
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def show_rename_popup(self, index):
        window = tk.Toplevel(self.root)
        window.title(f"Renommer {self.initiative_order[index][0]}")
        window.configure(bg="#F5E8C7")
        window.geometry("350x150")
        
        ttk.Label(window, text=f"Nouveau nom pour {self.initiative_order[index][0]} :", style="TLabel").pack(pady=10)
        new_name_var = tk.StringVar(value=self.initiative_order[index][0])
        name_entry = ttk.Entry(window, textvariable=new_name_var, width=25)
        name_entry.pack(pady=10, padx=15)
        
        def save_new_name():
            new_name = new_name_var.get().strip()
            current_name = self.initiative_order[index][0]
            default_pj_names = [f"PJ {i+1}" for i in range(self.party_size.get())]
            conflict = any(new_name == pj_name and current_name != pj_name for pj_name in default_pj_names)
            if conflict:
                messagebox.showerror("Erreur", "Ce nom correspond à un nom par défaut ('PJ X'). Veuillez choisir un autre nom.", parent=window)
                return
            if new_name:
                self.initiative_order[index][0] = new_name
                self.update_turn_order()
                window.destroy()
            else:
                messagebox.showwarning("Nom invalide", "Veuillez entrer un nom valide.", parent=window)
        
        ttk.Button(window, text="Enregistrer", command=save_new_name).pack(pady=5)
        ttk.Button(window, text="Annuler", command=window.destroy).pack(pady=5)

    def on_select_character(self, event):
        selected = self.order_listbox.curselection()
        if not selected:
            return
        index = selected[0]
        name, _, hp_current, hp_max, conditions, concentrating, stats = self.initiative_order[index]
        
        if self.hp_popup:
            self.hp_popup.destroy()
        
        if not name.startswith("PJ"):
            base_name = " ".join(name.split()[:-1])
            monster_info = self.builder.extract_monster_info(base_name)
            if 'error' not in monster_info:
                self.monster_stats_frame.pack(side=tk.RIGHT, fill="both", padx=10, expand=True)
                self.display_monster_stats(monster_info)
            else:
                self.monster_stats_frame.pack_forget()
        
        self.hp_popup = tk.Toplevel(self.root)
        self.hp_popup.title(f"Gestion des PV - {name}")
        self.hp_popup.configure(bg="#F5E8C7")
        self.hp_popup.geometry("900x700")
        self.hp_popup.resizable(True, True)
        self.hp_popup.transient(self.root)
        self.hp_popup.geometry(f"+{self.root.winfo_x()+200}+{self.root.winfo_y()+100}")
        
        main_canvas = tk.Canvas(self.hp_popup, bg="#F5E8C7")
        scrollbar = ttk.Scrollbar(self.hp_popup, orient=tk.VERTICAL, command=main_canvas.yview)
        main_frame = ttk.Frame(main_canvas, padding=10, relief="flat", borderwidth=0)
        
        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        main_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        main_canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        def configure_canvas(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        main_frame.bind("<Configure>", configure_canvas)
        
        hp_frame = ttk.LabelFrame(main_frame, text="Points de Vie", padding=10)
        hp_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        hp_frame.columnconfigure(1, weight=1)
        hp_frame.columnconfigure(3, weight=1)
        ttk.Label(hp_frame, text="Vie actuelle :", style="TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(hp_frame, textvariable=hp_current, width=8).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(hp_frame, text="Vie maximale :", style="TLabel").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ttk.Entry(hp_frame, textvariable=hp_max, width=8).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(hp_frame, text="Modification :", style="TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.hp_mod_var = tk.StringVar(value="0")
        ttk.Entry(hp_frame, textvariable=self.hp_mod_var, width=8).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(hp_frame, text="Cible :", style="TLabel").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.target_var = tk.StringVar()
        ttk.Combobox(hp_frame, textvariable=self.target_var, values=[e[0] for e in self.initiative_order if e[0] != name]).grid(row=1, column=3, padx=5, pady=5)
        
        button_frame = ttk.Frame(hp_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=5, sticky="ew")
        ttk.Button(button_frame, text="Soins", style="Green.TButton", command=lambda: self.apply_healing(index)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Dégâts", style="Red.TButton", command=lambda: self.apply_damage(index)).pack(side=tk.LEFT, padx=5)
        
        cond_frame = ttk.LabelFrame(main_frame, text="Conditions", padding=10)
        cond_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        cond_frame.columnconfigure(1, weight=1)
        ttk.Label(cond_frame, text="Conditions actuelles :", style="TLabel").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        cond_text = tk.Text(cond_frame, height=4, width=40, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
        cond_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        for cond in conditions:
            cond_text.insert(tk.END, f"{CONDITIONS[cond]['emoji']} {cond}: {CONDITIONS[cond]['description']}\n")
        if not conditions:
            cond_text.insert(tk.END, "Aucune condition\n")
        cond_text.config(state=tk.DISABLED)
        cond_btn_frame = ttk.Frame(cond_frame, relief="flat", borderwidth=0)
        cond_btn_frame.grid(row=2, column=0, columnspan=2, pady=5)
        cond_var = tk.StringVar()
        ttk.Combobox(cond_btn_frame, textvariable=cond_var, values=list(CONDITIONS.keys())).pack(side=tk.LEFT, padx=5)
        ttk.Button(cond_btn_frame, text="Ajouter", command=lambda: self.add_condition(index, cond_var.get(), cond_text, None)).pack(side=tk.LEFT, padx=5)
        ttk.Button(cond_btn_frame, text="Supprimer toutes", command=lambda: self.remove_all_conditions(index, cond_text, None)).pack(side=tk.LEFT, padx=5)

        if name.startswith("PJ"):
            rename_frame = ttk.LabelFrame(main_frame, text="Renommer", padding=10)
            rename_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
            rename_frame.columnconfigure(1, weight=1)
            ttk.Label(rename_frame, text=f"Nom actuel : {name}", style="TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            new_name_var = tk.StringVar(value=name)
            name_entry = ttk.Entry(rename_frame, textvariable=new_name_var, width=25)
            name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            
            def save_new_name():
                new_name = new_name_var.get().strip()
                current_name = self.initiative_order[index][0]
                default_pj_names = [f"PJ {i+1}" for i in range(self.party_size.get())]
                conflict = any(new_name == pj_name and current_name != pj_name for pj_name in default_pj_names)
                if conflict:
                    messagebox.showerror("Erreur", "Ce nom correspond à un nom par défaut ('PJ X'). Veuillez choisir un autre nom.", parent=self.hp_popup)
                    return
                if new_name:
                    self.initiative_order[index][0] = new_name
                    self.update_turn_order()
                    self.hp_popup.title(f"Gestion des PV - {new_name}")
                    self.hp_popup.destroy()
                else:
                    messagebox.showwarning("Nom invalide", "Veuillez entrer un nom valide.", parent=self.hp_popup)
            
            ttk.Button(rename_frame, text="Renommer", command=save_new_name).grid(row=1, column=0, columnspan=2, pady=5)

        if not name.startswith("PJ"):
            base_name = " ".join(name.split()[:-1])
            monster_info = self.builder.extract_monster_info(base_name)
            if 'error' not in monster_info:
                summary_frame = ttk.LabelFrame(main_frame, text=f"Caractéristiques ({base_name})", padding=10)
                summary_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
                summary_frame.columnconfigure((0, 1, 2), weight=1, uniform="column")
                
                summary_text = scrolledtext.ScrolledText(summary_frame, height=15, width=80, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
                summary_text.grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
                
                monster_summary = self.builder.get_monster_summary(monster_info)
                
                summary_text.insert(tk.END, f"{monster_summary['name']}\n", "bold")
                summary_text.insert(tk.END, f"{monster_summary['type']}\n\n", "italic")
                summary_text.insert(tk.END, "Statistiques\n", "bold")
                for key, value in monster_summary['stats'].items():
                    if value and value != "N/A":
                        summary_text.insert(tk.END, f"{key}: {value}\n")
                
                summary_text.insert(tk.END, "\nCaractéristiques\n", "bold")
                for key, value in monster_summary['abilities'].items():
                    if value and value != "N/A":
                        summary_text.insert(tk.END, f"{key}: {value}\n")
                
                if monster_summary['details']:
                    summary_text.insert(tk.END, "\nDétails\n", "bold")
                    for detail in monster_summary['details']:
                        if detail:
                            summary_text.insert(tk.END, f"{detail}\n")
                
                if monster_summary['traits']:
                    summary_text.insert(tk.END, "\nTraits\n", "bold")
                    for title, content in monster_summary['traits']:
                        if title:
                            summary_text.insert(tk.END, f"{title}\n{content}\n")
                
                if monster_summary['actions']:
                    summary_text.insert(tk.END, "\nActions\n", "bold")
                    for title, content in monster_summary['actions']:
                        if title:
                            summary_text.insert(tk.END, f"{title}\n{content}\n")
                
                if monster_summary['legendary_actions']:
                    summary_text.insert(tk.END, "\nActions Légendaires\n", "bold")
                    for title, content in monster_summary['legendary_actions']:
                        if title:
                            summary_text.insert(tk.END, f"{title}\n{content}\n")
                
                summary_text.tag_configure("bold", font=("Georgia", 12, "bold"), foreground="#8B4513")
                summary_text.tag_configure("italic", font=("Georgia", 12, "italic"))
                summary_text.config(state=tk.DISABLED)
                
                ttk.Button(summary_frame, text="Voir la Fiche Complète", command=lambda: self.open_monster_webpage(monster_info)).grid(row=1, column=0, columnspan=3, pady=10)

        def on_mouse_wheel(event):
            main_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        main_canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    def apply_healing(self, index):
        try:
            amount = float(self.hp_mod_var.get())
            if amount < 0:
                amount = 0
        except ValueError:
            amount = 0
        target_name = self.target_var.get()
        if target_name:
            for i, (n, _, hp_c, hp_m, _, _, s) in enumerate(self.initiative_order):
                if n == target_name:
                    hp_c.set(min(hp_m.get(), hp_c.get() + int(amount)))
                    s["healing_done"] += amount
                    self.update_turn_order()
                    return
        name, _, hp_c, hp_m, _, _, s = self.initiative_order[index]
        hp_c.set(min(hp_m.get(), hp_c.get() + int(amount)))
        s["healing_done"] += amount
        self.update_turn_order()

    def apply_damage(self, index):
        try:
            amount = float(self.hp_mod_var.get())
            if amount < 0:
                amount = 0
        except ValueError:
            amount = 0
        target_name = self.target_var.get()
        if target_name:
            for i, (n, _, hp_c, hp_m, _, _, s) in enumerate(self.initiative_order):
                if n == target_name:
                    hp_c.set(max(0, hp_c.get() - int(amount)))
                    s["damage_taken"] += amount
                    self.initiative_order[index][6]["damage_dealt"] += amount
                    self.update_turn_order()
                    return
        name, _, hp_c, hp_m, _, _, s = self.initiative_order[index]
        hp_c.set(max(0, hp_c.get() - int(amount)))
        s["damage_taken"] += amount
        self.update_turn_order()

    def open_monster_webpage(self, monster_info):
        if 'url' in monster_info and monster_info['url']:
            webbrowser.open(monster_info['url'])
        else:
            messagebox.showwarning("Avertissement", "Aucune URL disponible pour cette créature.")

    def display_monster_stats(self, monster_info):
        self.monster_stats_text.delete(1.0, tk.END)
        
        if 'image_urls' in monster_info and monster_info['image_urls']:
            try:
                image_url = monster_info['image_urls'][0]
                image_path = self.builder.download_and_cache_image(image_url)
                if image_path and os.path.exists(image_path):
                    image = Image.open(image_path)
                    image = image.resize((150, 150), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image)
                    self.monster_image_label.config(image=photo)
                    self.monster_image_label.image = photo
                    print(f"Successfully displayed image for {monster_info['name']}")
                else:
                    self.monster_image_label.config(image="", text="Erreur de téléchargement")
                    print(f"Failed to download image for {monster_info['name']}")
            except Exception as e:
                print(f"Erreur lors du chargement de l'image pour {monster_info['name']}: {e}")
                self.monster_image_label.config(image="", text="Image non disponible")
        else:
            self.monster_image_label.config(image="", text="Aucune image")
            print(f"No image available for {monster_info['name']}")

        if 'error' in monster_info:
            self.monster_stats_text.insert(tk.END, f"Erreur : {monster_info['error']}\n")
            return
        summary = self.builder.get_monster_summary(monster_info)
        self.monster_stats_text.insert(tk.END, f"{summary['name']}\n", "bold")
        self.monster_stats_text.insert(tk.END, f"{summary['type']}\n\n")
        self.monster_stats_text.insert(tk.END, "Statistiques\n", "bold")
        for k, v in summary['stats'].items():
            if v and v != "N/A":
                self.monster_stats_text.insert(tk.END, f"{k}: {v}\n")
        self.monster_stats_text.insert(tk.END, "\nCaractéristiques\n", "bold")
        for k, v in summary['abilities'].items():
            if v and v != "N/A":
                self.monster_stats_text.insert(tk.END, f"{k}: {v}\n")
        if summary['details']:
            self.monster_stats_text.insert(tk.END, "\nDétails\n", "bold")
            for d in summary['details']:
                if d:
                    self.monster_stats_text.insert(tk.END, f"{d}\n")
        if summary['traits']:
            self.monster_stats_text.insert(tk.END, "\nTraits\n", "bold")
            for t, c in summary['traits']:
                if t:
                    self.monster_stats_text.insert(tk.END, f"{t}\n{c}\n")
        if summary['actions']:
            self.monster_stats_text.insert(tk.END, "\nActions\n", "bold")
            for t, c in summary['actions']:
                if t:
                    self.monster_stats_text.insert(tk.END, f"{t}\n{c}\n")
        if summary['legendary_actions']:
            self.monster_stats_text.insert(tk.END, "\nActions Légendaires\n", "bold")
            for t, c in summary['legendary_actions']:
                if t:
                    self.monster_stats_text.insert(tk.END, f"{t}\n{c}\n")
        self.monster_stats_text.tag_configure("bold", font=("Georgia", 12, "bold"), foreground="#8B4513")

    def toggle_monster_detail(self):
        selected = self.order_listbox.curselection()
        if selected:
            index = selected[0]
            name = self.initiative_order[index][0]
            if not name.startswith("PJ"):
                base_name = " ".join(name.split()[:-1])
                monster_info = self.builder.extract_monster_info(base_name)
                if 'error' not in monster_info and 'url' in monster_info:
                    self.open_monster_webpage(monster_info)

    def next_turn(self):
        if self.initiative_order:
            self.current_turn = (self.current_turn + 1) % len(self.initiative_order)
            if self.current_turn == 0:
                self.round_count += 1
            self.update_turn_order()

    def previous_turn(self):
        if self.initiative_order:
            self.current_turn = (self.current_turn - 1) % len(self.initiative_order)
            if self.current_turn == len(self.initiative_order) - 1 and self.round_count > 0:
                self.round_count -= 1
            self.update_turn_order()

    def back_to_config(self):
        self.combat_frame.pack_forget()
        self.config_frame.pack(padx=20, pady=15, fill="both", expand=True)
        if self.hp_popup:
            self.hp_popup.destroy()
        if hasattr(self, 'initiative_frame'):
            self.initiative_frame.destroy()
        self.monster_stats_frame.pack_forget()
        self.monster_image_label.config(image="", text="")
        self.builder.monster_info_cache.clear()

    def show_battle_report(self):
        if not self.initiative_order:
            return
        
        window = tk.Toplevel(self.root)
        window.title("Rapport de Bataille")
        window.configure(bg="#F5E8C7")
        window.geometry("800x600")
        
        report_text = scrolledtext.ScrolledText(window, height=25, width=80, font=("Georgia", 12), bg="#FFF8E1", fg="#2F1E0F", relief="flat")
        report_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        total_damage_dealt = sum(stats["damage_dealt"] for _, _, _, _, _, _, stats in self.initiative_order)
        total_damage_taken = sum(stats["damage_taken"] for _, _, _, _, _, _, stats in self.initiative_order)
        total_healing = sum(stats["healing_done"] for _, _, _, _, _, _, stats in self.initiative_order)
        
        report_text.insert(tk.END, f"📜 Rapport de Bataille - Tour {self.round_count} 📜\n\n", "title")
        report_text.insert(tk.END, f"⚔️ Total des dégâts infligés : {total_damage_dealt}\n")
        report_text.insert(tk.END, f"🛡️ Total des dégâts subis : {total_damage_taken}\n")
        report_text.insert(tk.END, f"🩹 Total des soins effectués : {total_healing}\n")
        report_text.insert(tk.END, "-" * 50 + "\n\n", "separator")

        players = [(name, hp_c, stats) for name, _, hp_c, _, _, _, stats in self.initiative_order if name.startswith("PJ")]
        monsters = [(name, hp_c, stats) for name, _, hp_c, _, _, _, stats in self.initiative_order if not name.startswith("PJ")]

        report_text.insert(tk.END, "👥 Personnages Joueurs\n\n", "section_title")
        if not players:
            report_text.insert(tk.END, "Aucun PJ dans la bataille.\n\n")
        else:
            for name, hp_c, stats in players:
                status = "Vivant 🟢" if hp_c.get() > 0 else "Inconscient 🔴"
                report_text.insert(tk.END, f"{name} ({status})\n", "character_" + ("alive" if hp_c.get() > 0 else "dead"))
                report_text.insert(tk.END, f"  ⚔️ Dégâts infligés : {stats['damage_dealt']}\n")
                report_text.insert(tk.END, f"  🛡️ Dégâts subis : {stats['damage_taken']}\n")
                report_text.insert(tk.END, f"  🩹 Soins effectués : {stats['healing_done']}\n")
                report_text.insert(tk.END, "-" * 30 + "\n", "separator")
            report_text.insert(tk.END, "\n")

        report_text.insert(tk.END, "👹 Monstres\n\n", "section_title")
        if not monsters:
            report_text.insert(tk.END, "Aucun monstre dans la bataille.\n\n")
        else:
            for name, hp_c, stats in monsters:
                status = "Vivant 🟢" if hp_c.get() > 0 else "Mort 💀"
                report_text.insert(tk.END, f"{name} ({status})\n", "character_" + ("alive" if hp_c.get() > 0 else "dead"))
                report_text.insert(tk.END, f"  ⚔️ Dégâts infligés : {stats['damage_dealt']}\n")
                report_text.insert(tk.END, f"  🛡️ Dégâts subis : {stats['damage_taken']}\n")
                report_text.insert(tk.END, f"  🩹 Soins effectués : {stats['healing_done']}\n")
                report_text.insert(tk.END, "-" * 30 + "\n", "separator")
            report_text.insert(tk.END, "\n")

        ttk.Button(window, text="Fermer", command=window.destroy).pack(pady=5)

        report_text.tag_configure("title", font=("Georgia", 14, "bold"), foreground="#8B4513", justify="center")
        report_text.tag_configure("section_title", font=("Georgia", 13, "bold"), foreground="#A0522D")
        report_text.tag_configure("character_alive", font=("Georgia", 12, "bold"), foreground="#2E7D32")
        report_text.tag_configure("character_dead", font=("Georgia", 12, "bold"), foreground="#D32F2F")
        report_text.tag_configure("separator", foreground="#8B4513", justify="center")

if __name__ == "__main__":
    root = ThemedTk(theme="clam")
    app = EncounterApp(root)
    root.mainloop()