import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ttkthemes import ThemedTk
import sqlite3
from dataclasses import dataclass
import re
import unicodedata

@dataclass
class CustomMonster:
    name: str
    size: str
    type: str
    cr: float
    xp: int
    ac: str
    hp: str
    speed: str
    str_score: int
    dex_score: int
    con_score: int
    int_score: int
    wis_score: int
    cha_score: int
    skills: str
    damage_resistances: str
    senses: str
    languages: str
    traits: str
    actions: str
    legendary_actions: str

class MonsterCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Créateur de Monstres - D&D 5e")
        self.root.geometry("1200x800")
        self.root.configure(bg="#F5E8C7")
        self.db_path = "monsters.db"
        self.selected_monster = None

        self.colors = {
            "background": "#F5E8C7",
            "text": "#3C2A1D",
            "accent": "#8B4513",
            "primary_btn": "#D4A017",
            "secondary_btn": "#A0522D",
            "entry_bg": "#FFF8E1",
            "border": "#8B4513"
        }

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", font=("Georgia", 12), foreground=self.colors["text"], background=self.colors["background"])
        style.configure("TButton", font=("Georgia", 12), foreground=self.colors["text"], background=self.colors["primary_btn"], relief="flat", padding=6)
        style.map("TButton", background=[('active', self.colors["accent"])], foreground=[('active', '#FFFFFF')])
        style.configure("Secondary.TButton", font=("Georgia", 12), foreground="#FFFFFF", background=self.colors["secondary_btn"], relief="flat", padding=6)
        style.map("Secondary.TButton", background=[('active', self.colors["accent"])])
        style.configure("Section.TLabel", font=("Georgia", 14, "bold"), foreground=self.colors["accent"], background=self.colors["background"])
        style.configure("TEntry", font=("Georgia", 12), fieldbackground=self.colors["entry_bg"], relief="flat", borderwidth=1, padding=3)
        style.configure("TSpinbox", font=("Georgia", 12), fieldbackground=self.colors["entry_bg"], relief="flat", borderwidth=1, padding=3)
        style.configure("TCombobox", font=("Georgia", 12), fieldbackground=self.colors["entry_bg"], relief="flat", borderwidth=1, padding=3)
        style.configure("Section.TFrame", background=self.colors["background"], relief="flat")

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=20, style="Section.TFrame")
        main_frame.pack(fill="both", expand=True)

        header_frame = ttk.Frame(main_frame, style="Section.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(header_frame, text="Créer ou Éditer un Monstre", style="Section.TLabel").pack(side=tk.LEFT)

        select_frame = ttk.Frame(header_frame, style="Section.TFrame")
        select_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(select_frame, text="Sélectionner un Monstre :").pack(side=tk.LEFT, padx=5)
        self.monster_select_var = tk.StringVar()
        self.monster_select = ttk.Combobox(select_frame, textvariable=self.monster_select_var, width=30)
        self.monster_select.pack(side=tk.LEFT, padx=5)
        self.load_monster_list()
        self.monster_select.bind("<<ComboboxSelected>>", self.load_selected_monster)

        btn_frame = ttk.Frame(header_frame, style="Section.TFrame")
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Nouveau", command=self.reset_fields).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Enregistrer", command=self.save_monster).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annuler", style="Secondary.TButton", command=self.root.destroy).pack(side=tk.RIGHT, padx=5)

        content_frame = ttk.Frame(main_frame, style="Section.TFrame")
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=0)
        content_frame.grid_rowconfigure((6, 7, 8), weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        basic_frame = ttk.Frame(content_frame, style="Section.TFrame")
        basic_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(basic_frame, text="Informations de Base", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        basic_subframe = ttk.Frame(basic_frame, style="Section.TFrame")
        basic_subframe.pack(fill="x")
        self.name_var = tk.StringVar()
        self.add_labeled_entry(basic_subframe, "Nom :", self.name_var, width=30, side=tk.LEFT)
        self.size_var = tk.StringVar(value="M")
        self.add_labeled_combobox(basic_subframe, "Taille :", self.size_var, values=["TP", "P", "M", "G", "TG", "Gig"], width=5, side=tk.LEFT)
        self.type_var = tk.StringVar()
        self.add_labeled_entry(basic_subframe, "Type :", self.type_var, width=20, side=tk.LEFT)
        self.cr_var = tk.DoubleVar(value=1.0)
        self.add_labeled_spinbox(basic_subframe, "CR :", self.cr_var, from_=0, to=30, increment=0.25, width=7, side=tk.LEFT)

        stats_frame = ttk.Frame(content_frame, style="Section.TFrame")
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(stats_frame, text="Statistiques", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        stats_subframe = ttk.Frame(stats_frame, style="Section.TFrame")
        stats_subframe.pack(fill="x")
        self.ac_var = tk.StringVar(value="10")
        self.add_labeled_entry(stats_subframe, "Classe d'armure :", self.ac_var, width=15, side=tk.LEFT)
        self.hp_var = tk.StringVar(value="10 (2d8 + 2)")
        self.add_labeled_entry(stats_subframe, "Points de vie :", self.hp_var, width=20, side=tk.LEFT)
        self.speed_var = tk.StringVar(value="9 m")
        self.add_labeled_entry(stats_subframe, "Vitesse :", self.speed_var, width=20, side=tk.LEFT)

        details_frame = ttk.Frame(content_frame, style="Section.TFrame")
        details_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(details_frame, text="Détails", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        details_subframe = ttk.Frame(details_frame, style="Section.TFrame")
        details_subframe.pack(fill="x")
        self.skills_var = tk.StringVar()
        self.add_labeled_entry(details_subframe, "Compétences :", self.skills_var, width=30, side=tk.LEFT)
        self.damage_resistances_var = tk.StringVar()
        self.add_labeled_entry(details_subframe, "Résistances :", self.damage_resistances_var, width=30, side=tk.LEFT)

        details_frame2 = ttk.Frame(content_frame, style="Section.TFrame")
        details_frame2.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        details_subframe2 = ttk.Frame(details_frame2, style="Section.TFrame")
        details_subframe2.pack(fill="x")
        self.senses_var = tk.StringVar()
        self.add_labeled_entry(details_subframe2, "Sens :", self.senses_var, width=30, side=tk.LEFT)
        self.languages_var = tk.StringVar()
        self.add_labeled_entry(details_subframe2, "Langues :", self.languages_var, width=30, side=tk.LEFT)

        scores_frame = ttk.Frame(content_frame, style="Section.TFrame")
        scores_frame.grid(row=4, column=0, sticky="ew", pady=(0, 15))
        ttk.Label(scores_frame, text="Caractéristiques", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        scores_grid = ttk.Frame(scores_frame, style="Section.TFrame")
        scores_grid.pack(anchor="w")
        scores = ["Force", "Dextérité", "Constitution", "Intelligence", "Sagesse", "Charisme"]
        self.score_vars = {}
        for i, score in enumerate(scores):
            self.score_vars[score] = tk.IntVar(value=10)
            ttk.Label(scores_grid, text=f"{score} :").grid(row=i//3, column=(i%3)*2, padx=5, pady=2, sticky="e")
            ttk.Spinbox(scores_grid, textvariable=self.score_vars[score], from_=1, to=30, width=5).grid(row=i//3, column=(i%3)*2+1, padx=5, pady=2)

        traits_frame = ttk.LabelFrame(content_frame, text="Traits", padding=5, style="Section.TFrame")
        traits_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 15))
        self.traits_text = scrolledtext.ScrolledText(traits_frame, height=4, font=("Georgia", 12), bg=self.colors["entry_bg"], fg=self.colors["text"], relief="flat", borderwidth=1)
        self.traits_text.pack(fill="both", expand=True)

        actions_frame = ttk.LabelFrame(content_frame, text="Actions", padding=5, style="Section.TFrame")
        actions_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 15))
        self.actions_text = scrolledtext.ScrolledText(actions_frame, height=4, font=("Georgia", 12), bg=self.colors["entry_bg"], fg=self.colors["text"], relief="flat", borderwidth=1)
        self.actions_text.pack(fill="both", expand=True)

        legendary_frame = ttk.LabelFrame(content_frame, text="Actions Légendaires", padding=5, style="Section.TFrame")
        legendary_frame.grid(row=7, column=0, sticky="nsew", pady=(0, 15))
        self.legendary_text = scrolledtext.ScrolledText(legendary_frame, height=4, font=("Georgia", 12), bg=self.colors["entry_bg"], fg=self.colors["text"], relief="flat", borderwidth=1)
        self.legendary_text.pack(fill="both", expand=True)

    def load_monster_list(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM monsters")
            monsters = cursor.fetchall()
            conn.close()
            monster_names = [monster[0] for monster in monsters]
            self.monster_select['values'] = monster_names
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des monstres : {e}")

    def load_selected_monster(self, event=None):
        selected_name = self.monster_select_var.get()
        if not selected_name:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, size, type, cr, xp, ac, hp, speed, str_score, dex_score, con_score, int_score, wis_score, cha_score, skills, damage_resistances, senses, languages, traits, actions, legendary_actions FROM monsters WHERE name = ?", (selected_name,))
            monster_data = cursor.fetchone()
            conn.close()
            if monster_data:
                self.selected_monster = selected_name
                self.name_var.set(monster_data[0] or "")
                self.size_var.set(monster_data[1] or "M")
                self.type_var.set(monster_data[2] or "")
                self.cr_var.set(monster_data[3] if monster_data[3] is not None else 1.0)
                self.ac_var.set(monster_data[5] or "10")
                self.hp_var.set(monster_data[6] or "10 (2d8 + 2)")
                self.speed_var.set(monster_data[7] or "9 m")
                self.score_vars["Force"].set(monster_data[8] if monster_data[8] is not None else 10)
                self.score_vars["Dextérité"].set(monster_data[9] if monster_data[9] is not None else 10)
                self.score_vars["Constitution"].set(monster_data[10] if monster_data[10] is not None else 10)
                self.score_vars["Intelligence"].set(monster_data[11] if monster_data[11] is not None else 10)
                self.score_vars["Sagesse"].set(monster_data[12] if monster_data[12] is not None else 10)
                self.score_vars["Charisme"].set(monster_data[13] if monster_data[13] is not None else 10)
                self.skills_var.set(monster_data[14] or "")
                self.damage_resistances_var.set(monster_data[15] or "")
                self.senses_var.set(monster_data[16] or "")
                self.languages_var.set(monster_data[17] or "")
                self.traits_text.delete("1.0", tk.END)
                self.traits_text.insert("1.0", monster_data[18] or "")
                self.actions_text.delete("1.0", tk.END)
                self.actions_text.insert("1.0", monster_data[19] or "")
                self.legendary_text.delete("1.0", tk.END)
                self.legendary_text.insert("1.0", monster_data[20] or "")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement du monstre : {e}")

    def reset_fields(self):
        self.selected_monster = None
        self.monster_select_var.set("")
        self.name_var.set("")
        self.size_var.set("M")
        self.type_var.set("")
        self.cr_var.set(1.0)
        self.ac_var.set("10")
        self.hp_var.set("10 (2d8 + 2)")
        self.speed_var.set("9 m")
        for score in self.score_vars.values():
            score.set(10)
        self.skills_var.set("")
        self.damage_resistances_var.set("")
        self.senses_var.set("")
        self.languages_var.set("")
        self.traits_text.delete("1.0", tk.END)
        self.actions_text.delete("1.0", tk.END)
        self.legendary_text.delete("1.0", tk.END)

    def add_labeled_entry(self, frame, label, var, width=10, side=tk.LEFT, padx=10):
        ttk.Label(frame, text=label).pack(side=side, padx=padx)
        ttk.Entry(frame, textvariable=var, width=width).pack(side=side, padx=padx)

    def add_labeled_spinbox(self, frame, label, var, from_=0, to=30, increment=1, width=5, side=tk.LEFT, padx=10):
        ttk.Label(frame, text=label).pack(side=side, padx=padx)
        ttk.Spinbox(frame, textvariable=var, from_=from_, to=to, increment=increment, width=width).pack(side=side, padx=padx)

    def add_labeled_combobox(self, frame, label, var, values, width=10, side=tk.LEFT, padx=10):
        ttk.Label(frame, text=label).pack(side=side, padx=padx)
        ttk.Combobox(frame, textvariable=var, values=values, width=width).pack(side=side, padx=padx)

    def cr_to_xp(self, cr):
        cr_xp_map = {
            0: 10, 0.125: 25, 0.25: 50, 0.5: 100, 1: 200, 2: 450, 3: 700, 4: 1100,
            5: 1800, 6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900, 11: 7200,
            12: 8400, 13: 10000, 14: 11500, 15: 13000, 16: 15000, 17: 18000,
            18: 20000, 19: 22000, 20: 25000, 21: 33000, 22: 41000, 23: 50000,
            24: 62000, 25: 75000, 30: 155000
        }
        return cr_xp_map.get(cr, 0)

    def normalize_name(self, name):
        name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
        name = name.lower().strip()
        name = re.sub(r'\s+', ' ', name)
        replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'à': 'a', 'â': 'a', 'ä': 'a',
                        'î': 'i', 'ï': 'i', 'ô': 'o', 'ö': 'o', 'û': 'u', 'ü': 'u', 'ç': 'c'}
        for char, replacement in replacements.items():
            name = name.replace(char, replacement)
        return name

    def save_monster(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Erreur", "Le nom du monstre est requis.")
            return
        monster = CustomMonster(
            name=name,
            size=self.size_var.get(),
            type=self.type_var.get().strip() or "Créature",
            cr=self.cr_var.get(),
            xp=self.cr_to_xp(self.cr_var.get()),
            ac=self.ac_var.get().strip(),
            hp=self.hp_var.get().strip(),
            speed=self.speed_var.get().strip(),
            str_score=self.score_vars["Force"].get(),
            dex_score=self.score_vars["Dextérité"].get(),
            con_score=self.score_vars["Constitution"].get(),
            int_score=self.score_vars["Intelligence"].get(),
            wis_score=self.score_vars["Sagesse"].get(),
            cha_score=self.score_vars["Charisme"].get(),
            skills=self.skills_var.get().strip(),
            damage_resistances=self.damage_resistances_var.get().strip(),
            senses=self.senses_var.get().strip(),
            languages=self.languages_var.get().strip() or "—",
            traits=self.traits_text.get("1.0", tk.END).strip(),
            actions=self.actions_text.get("1.0", tk.END).strip(),
            legendary_actions=self.legendary_text.get("1.0", tk.END).strip()
        )
        normalized_name = self.normalize_name(name)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Vérifier si la table monsters existe et obtenir ses colonnes
            cursor.execute("PRAGMA table_info(monsters)")
            columns = {col[1] for col in cursor.fetchall()}

            # Nouvelle structure sans le champ alignment
            new_schema = {'normalized_name', 'name', 'size', 'type', 'cr', 'xp', 'ac', 'hp', 'speed',
                          'str_score', 'dex_score', 'con_score', 'int_score', 'wis_score', 'cha_score',
                          'skills', 'damage_resistances', 'senses', 'languages', 'traits', 'actions', 'legendary_actions'}

            if columns:
                # Si la table existe, vérifier si elle contient la colonne alignment
                if 'alignment' in columns:
                    # Créer une nouvelle table sans la colonne alignment
                    cursor.execute('''CREATE TABLE monsters_new
                                    (normalized_name TEXT PRIMARY KEY, name TEXT, size TEXT, type TEXT, cr REAL, xp INTEGER,
                                     ac TEXT, hp TEXT, speed TEXT, str_score INTEGER, dex_score INTEGER, con_score INTEGER,
                                     int_score INTEGER, wis_score INTEGER, cha_score INTEGER, skills TEXT, damage_resistances TEXT,
                                     senses TEXT, languages TEXT, traits TEXT, actions TEXT, legendary_actions TEXT)''')
                    
                    # Copier les données existantes (sans la colonne alignment)
                    cursor.execute('''INSERT INTO monsters_new
                                    (normalized_name, name, size, type, cr, xp, ac, hp, speed, str_score, dex_score, con_score,
                                     int_score, wis_score, cha_score, skills, damage_resistances, senses, languages, traits, actions, legendary_actions)
                                    SELECT normalized_name, name, size, type, cr, xp, ac, hp, speed, str_score, dex_score, con_score,
                                     int_score, wis_score, cha_score, skills, damage_resistances, senses, languages, traits, actions, legendary_actions
                                    FROM monsters''')
                    
                    # Supprimer l'ancienne table et renommer la nouvelle
                    cursor.execute("DROP TABLE monsters")
                    cursor.execute("ALTER TABLE monsters_new RENAME TO monsters")
            else:
                # Si la table n'existe pas, créer la nouvelle structure sans alignment
                cursor.execute('''CREATE TABLE monsters
                                (normalized_name TEXT PRIMARY KEY, name TEXT, size TEXT, type TEXT, cr REAL, xp INTEGER,
                                 ac TEXT, hp TEXT, speed TEXT, str_score INTEGER, dex_score INTEGER, con_score INTEGER,
                                 int_score INTEGER, wis_score INTEGER, cha_score INTEGER, skills TEXT, damage_resistances TEXT,
                                 senses TEXT, languages TEXT, traits TEXT, actions TEXT, legendary_actions TEXT)''')

            # Insérer ou mettre à jour le monstre
            cursor.execute('''INSERT OR REPLACE INTO monsters 
                            (normalized_name, name, size, type, cr, xp, ac, hp, speed, str_score, dex_score, con_score,
                             int_score, wis_score, cha_score, skills, damage_resistances, senses, languages, traits, actions, legendary_actions)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (normalized_name, monster.name, monster.size, monster.type, monster.cr, monster.xp,
                            monster.ac, monster.hp, monster.speed, monster.str_score, monster.dex_score, monster.con_score,
                            monster.int_score, monster.wis_score, monster.cha_score, monster.skills, monster.damage_resistances,
                            monster.senses, monster.languages, monster.traits, monster.actions, monster.legendary_actions))
            conn.commit()
            conn.close()
            messagebox.showinfo("Succès", f"{monster.name} {'mis à jour' if self.selected_monster else 'enregistré'} avec succès.")
            self.load_monster_list()
            self.selected_monster = None
            self.monster_select_var.set("")
            self.reset_fields()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")

if __name__ == "__main__":
    root = ThemedTk(theme="clam")
    app = MonsterCreatorApp(root)
    root.mainloop()