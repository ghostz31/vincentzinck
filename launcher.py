import tkinter as tk
from tkinter import ttk, messagebox
from ttkthemes import ThemedTk
import subprocess
import sys
import os

class MainLauncher:
    def __init__(self, root):
        print("Initialisation du launcher...")
        self.root = root
        self.root.title("D&D 5e Tools Launcher")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", font=("Georgia", 12), foreground="#3C2A1D", background="#F5E8C7")
        style.configure("Title.TLabel", font=("Georgia", 16, "bold"), foreground="#8B4513", background="#F5E8C7")
        style.configure("TButton", font=("Georgia", 12), foreground="#3C2A1D", background="#D4A017", 
                       relief="flat", padding=10, bordercolor="#8B4513")
        style.map("TButton", background=[('active', '#A0522D')], foreground=[('active', '#FFFFFF')])
        style.configure("TFrame", background="#F5E8C7")

        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        ttk.Label(self.main_frame, text="Outils D&D 5e", style="Title.TLabel").pack(pady=(0, 30))
        print("Interface principale créée")

        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(expand=True)

        ttk.Button(btn_frame, text="Créateur de Rencontres", 
                  command=self.launch_encounter_builder).pack(pady=15, fill="x")
        ttk.Button(btn_frame, text="Créateur de Monstres", 
                  command=self.launch_monster_creator).pack(pady=15, fill="x")
        ttk.Button(self.main_frame, text="Quitter", 
                  command=self.root.quit).pack(pady=(30, 0))
        print("Boutons configurés")

    def launch_encounter_builder(self):
        print("Tentative de lancement de Encounter Builder...")
        try:
            if os.path.exists("encounter_builder_gui.py"):  # Nom modifié ici
                print("Fichier encounter_builder_gui.py trouvé")
                subprocess.Popen([sys.executable, "encounter_builder_gui.py"])  # Nom modifié ici
                print("Encounter Builder lancé")
            else:
                print("Fichier encounter_builder_gui.py non trouvé")
                messagebox.showerror("Erreur", "Le fichier encounter_builder_gui.py n'a pas été trouvé.")
        except Exception as e:
            print(f"Erreur rencontrée : {e}")
            messagebox.showerror("Erreur", f"Erreur lors du lancement du Créateur de Rencontres : {e}")

    def launch_monster_creator(self):
        print("Tentative de lancement de Monster Creator...")
        try:
            if os.path.exists("monster_creator.py"):
                print("Fichier monster_creator.py trouvé")
                subprocess.Popen([sys.executable, "monster_creator.py"])
                print("Monster Creator lancé")
            else:
                print("Fichier monster_creator.py non trouvé")
                messagebox.showerror("Erreur", "Le fichier monster_creator.py n'a pas été trouvé.")
        except Exception as e:
            print(f"Erreur rencontrée : {e}")
            messagebox.showerror("Erreur", f"Erreur lors du lancement du Créateur de Monstres : {e}")

if __name__ == "__main__":
    print("Démarrage du programme...")
    root = ThemedTk(theme="clam")
    print("Fenêtre Tkinter créée")
    app = MainLauncher(root)
    print("Application lancée, entrée dans la boucle principale")
    root.mainloop()