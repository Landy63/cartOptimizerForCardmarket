import customtkinter as ctk
import tkinter as tk  # Pour tk.Label, etc.
from tkinter import filedialog, messagebox
import threading
import json
import pandas as pd
import os
import logging
import random
import time
from docx import Document
from collections import defaultdict
from PIL import Image, ImageTk, ImageSequence  # Pour gérer les images et GIF animés

# Import de vos scripts (inchangé)
from main import scrape_urls, save_to_excel
from optimize_cart import full_best_price, optimize_cart

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

class ScrapOptimizerApp:
    def __init__(self, root):
        # ----- Configuration de customtkinter -----
        ctk.set_appearance_mode("System")  # "Light" / "Dark" / "System"
        ctk.set_default_color_theme("blue")

        # ----- Fenêtre principale -----
        self.root = root
        self.root.title("Scrap & Optimisation")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)  # Taille minimale pour éviter que les widgets ne soient cachés

        # Variables d'état (cache)
        self.advanced_mode = False
        self.urls = []
        self.scraped_data = []
        self.optimized_data = []
        self.file_path = ""
        self.search_filter = ""  # Filtre de recherche à appliquer (contenant le '?')
        self.filter_overlay = None  # Overlay pour la saisie du filtre

        # Création de l'interface graphique principale
        self.create_widgets()

    def create_widgets(self):
        """
        Création de l'interface principale.
        Les boutons et autres éléments sont centrés et gardent leur taille d'origine,
        tandis que la zone de log s'adapte pour occuper l'espace disponible.
        """
        # ---------------------- Bouton Mode Avancé ---------------------- #
        self.mode_button = ctk.CTkButton(
            self.root, 
            text="🔄 Mode Avancé", 
            command=self.toggle_mode
        )
        self.mode_button.pack(pady=(30, 5), padx=20, anchor="center")

        # ---------------------- Bouton Ajouter un filtre de recherche ---------------------- #
        self.filter_button = ctk.CTkButton(
            self.root,
            text="🔎 Ajouter un filtre de recherche (Avant l'import du fichier .txt)",
            command=self.add_search_filter  # Ouvre l'overlay pour le filtre
        )
        self.filter_button.pack(pady=(10, 5), padx=20, anchor="center")

        # ---------------------- Bouton Importer un fichier de liens ---------------------- #
        self.import_button = ctk.CTkButton(
            self.root,
            text="📂 Importer un fichier de liens (.txt/.docx)",
            command=self.import_file
        )
        self.import_button.pack(pady=(10, 5), padx=20, anchor="center")

        # ---------------------- Bouton Charger un fichier JSON (mode avancé) ---------------------- #
        self.import_json_button = ctk.CTkButton(
            self.root,
            text="📂 Charger un fichier JSON existant",
            command=self.import_json
        )
        # Ce bouton sera affiché uniquement en mode avancé (voir toggle_mode)

        # ---------------------- Barre de progression ---------------------- #
        self.progress = ctk.CTkProgressBar(self.root, width=400)
        self.progress.set(0)
        self.progress.pack(pady=(15, 5), padx=20, fill="x")
        
        self.progress_label = ctk.CTkLabel(self.root, text="Progression : 0%")
        self.progress_label.pack(pady=5, padx=20, anchor="center")

        # ---------------------- Frame pour les boutons de scénario ---------------------- #
        self.scenario_frame = ctk.CTkFrame(self.root)
        self.scenario_frame.pack(pady=(10, 5), padx=20)

        self.optimize_button = ctk.CTkButton(
            self.scenario_frame,
            text="⚙️ Optimiser (Mode Classique)",
            command=self.start_optimization,
            state="disabled"
        )
        self.optimize_button.pack(pady=5, padx=10, anchor="center")

        self.scrape_button = ctk.CTkButton(
            self.scenario_frame,
            text="🔍 Lancer le scraping (Mode Avancé)",
            command=self.start_scraping
        )
        # Ce bouton sera affiché en mode avancé uniquement

        self.optimize_manual_button = ctk.CTkButton(
            self.scenario_frame,
            text="⚙️ Optimiser (Mode Avancé)",
            command=self.start_manual_optimization,
            state="disabled"
        )
        # Ce bouton sera affiché en mode avancé uniquement

        # ---------------------- Bouton Exporter (Excel) ---------------------- #
        self.export_button = ctk.CTkButton(
            self.root,
            text="📊 Exporter les résultats (Excel)",
            command=self.export_results,
            state="disabled"
        )
        # Ce bouton sera affiché à la fin du processus (centré)
        
        # ---------------------- Bouton Nettoyer le terminal (et Cache) ---------------------- #
        self.clear_button = ctk.CTkButton(
            self.root,
            text="🧹 Nettoyer le terminal",
            command=self.clear_logs
        )
        self.clear_button.pack(pady=5, padx=20, anchor="center")

        # ---------------------- Zone de texte (logs) ---------------------- #
        self.log_text = ctk.CTkTextbox(self.root, width=900, height=350)
        self.log_text.pack(pady=(15, 5), padx=20, fill="both", expand=True)

        # ---------------------- Label de résultat ---------------------- #
        self.result_label = ctk.CTkLabel(
            self.root,
            text="",
            text_color="blue",
            font=("Arial", 10, "bold")
        )
        self.result_label.pack(pady=5, padx=20, anchor="center")

    def log(self, message):
        """Ajoute un message dans la zone de texte et dans le logger standard."""
        logging.info(message)
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def clear_logs(self):
        """
        Vide la zone de log et réinitialise le cache (URLs, données scrapées, etc.).
        """
        # Vider la zone de log
        self.log_text.delete("1.0", "end")
        logging.info("Terminal vidé.")
        # Réinitialiser les variables internes
        self.urls = []
        self.scraped_data = []
        self.optimized_data = []
        self.file_path = ""
        self.search_filter = ""
        logging.info("Cache vidé.")

    def toggle_mode(self):
        """Active / désactive le mode avancé."""
        self.advanced_mode = not self.advanced_mode
        if self.advanced_mode:
            self.mode_button.configure(text="🔄 Mode Classique")
            self.import_json_button.pack(pady=5, padx=20, anchor="center")
            self.optimize_button.pack_forget()
            self.scrape_button.pack(pady=5, padx=20, anchor="center")
            self.optimize_manual_button.pack(pady=5, padx=20, anchor="center")
        else:
            self.mode_button.configure(text="🔄 Mode Avancé")
            self.import_json_button.pack_forget()
            self.scrape_button.pack_forget()
            self.optimize_manual_button.pack_forget()
            self.optimize_button.pack(pady=5, padx=20, anchor="center")

    def add_search_filter(self):
        """
        Affiche un overlay couvrant toute la fenêtre principale pour saisir le filtre.
        L'utilisateur fournit un lien d'exemple contenant le filtre (la partie commençant par '?'),
        qui est détecté automatiquement. Une croix en haut à droite permet de fermer l'overlay.
        """
        # Si l'overlay existe déjà, le ramener au premier plan
        if self.filter_overlay is not None:
            self.filter_overlay.lift()
            return

        # Créer un overlay qui occupe toute la fenêtre
        self.filter_overlay = ctk.CTkFrame(self.root)
        self.filter_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Bouton de fermeture (croix) positionné en haut à droite
        close_button = ctk.CTkButton(self.filter_overlay,
                                     text="X",
                                     command=self.hide_filter_overlay,
                                     width=30,
                                     height=30,
                                     fg_color="red",
                                     text_color="white")
        close_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        # Créer un conteneur pour centrer le contenu
        content_frame = ctk.CTkFrame(self.filter_overlay, fg_color="transparent")
        content_frame.pack(expand=True)

        instructions = (
            "Mettez un lien d'exemple contenant le filtre.\n"
            "L'application détectera automatiquement la partie de l'URL qui commence par '?' "
            "et l'appliquera à toutes vos URLs.\n\n"
            "Par exemple :\n"
            "https://www.cardmarket.com/fr/Pokemon/Products/Singles/Expansion-Pack/Bulbasaur?language=2&minCondition=2"
        )
        instr_label = ctk.CTkLabel(content_frame, text=instructions, wraplength=700)
        instr_label.pack(pady=20)

        # Affichage du GIF animé via un widget tk.Label (taille fixe)
        gif_label = tk.Label(content_frame)
        gif_label.pack(pady=20)
        try:
            pil_image = Image.open("filter_tutorial.gif")
            frames = [ImageTk.PhotoImage(frame.copy().convert("RGBA")) for frame in ImageSequence.Iterator(pil_image)]
            def update(ind):
                frame = frames[ind]
                gif_label.configure(image=frame)
                gif_label.image = frame  # Conserver la référence
                ind = (ind + 1) % len(frames)
                self.filter_overlay.after(100, update, ind)
            update(0)
        except Exception as e:
            self.log(f"⚠️ Le GIF tutoriel n'a pas pu être chargé : {e}")

        # Zone de saisie pour le lien d'exemple (taille fixe)
        self.filter_entry = ctk.CTkEntry(content_frame, width=500)
        self.filter_entry.pack(pady=20)

        # Bouton pour appliquer le filtre
        save_button = ctk.CTkButton(content_frame, text="Appliquer le filtre", command=self.save_filter)
        save_button.pack(pady=20)

    def save_filter(self):
        """
        Extrait le filtre du lien saisi en conservant le '?' (par exemple '?language=2&minCondition=2')
        et le stocke dans self.search_filter. Puis ferme l'overlay.
        """
        input_text = self.filter_entry.get().strip()
        index = input_text.find("?")
        if index != -1:
            # Conserver la partie à partir du '?' (incluant le '?')
            filter_detected = input_text[index:]
            self.search_filter = filter_detected
            self.log(f"Filtre de recherche détecté : {self.search_filter}")
            self.hide_filter_overlay()
        else:
            self.log("⚠️ Aucun filtre détecté. Veuillez fournir un lien contenant '?'")

    def hide_filter_overlay(self):
        """Ferme et supprime l'overlay de filtre."""
        if self.filter_overlay is not None:
            self.filter_overlay.destroy()
            self.filter_overlay = None

    def apply_filter(self, url, filter_str):
        """
        Applique le filtre à l'URL en supprimant l'ancien paramétrage (si présent)
        et en ajoutant le nouveau.
        """
        if "?" in url:
            base = url.split("?", 1)[0]
        else:
            base = url
        return f"{base}{filter_str}"

    def import_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Word files", "*.docx")]
        )
        if file_path:
            self.file_path = file_path
            self.urls = self.read_file(file_path)
            # Appliquer le filtre si défini
            if self.search_filter:
                self.urls = [self.apply_filter(url, self.search_filter) for url in self.urls]
                self.log("🔄 Filtre de recherche appliqué à toutes les URLs.")
                # Pour debug, afficher chaque URL modifiée
                for url in self.urls:
                    self.log(f"URL appliquée: {url}")
            self.log(f"📂 {len(self.urls)} liens importés depuis {file_path}.")
            self.update_progress(0)
            self.progress_label.configure(text="Progression : 0%")
            if not self.advanced_mode:
                self.optimize_button.configure(state="normal")

    def import_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            self.file_path = file_path
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.scraped_data = json.load(f)
                self.log(f"✅ Fichier JSON chargé : {len(self.scraped_data)} cartes trouvées.")
                self.optimize_manual_button.configure(state="normal")
            except Exception as e:
                self.log(f"❌ Erreur lors du chargement du JSON : {e}")
                messagebox.showerror("Erreur JSON", f"Impossible de charger : {e}")

    def read_file(self, file_path):
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            return [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        else:
            messagebox.showerror("Erreur", "Format de fichier non supporté (seulement .txt et .docx)")
            return []

    def update_progress(self, value):
        """Met à jour la barre de progression (valeur 0..100) et le label associé."""
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
        self.progress.set(value / 100.0)
        self.progress_label.configure(text=f"Progression : {int(value)}%")
        self.root.update_idletasks()

    def start_scraping(self):
        if not self.urls:
            messagebox.showwarning("Aucun lien", "Veuillez importer un fichier de liens avant de scraper.")
            return
        self.update_progress(0)
        threading.Thread(target=self.scrape_task).start()

    def scrape_task(self):
        self.scraped_data = []
        total_urls = len(self.urls)
        percent_per_link = 100 / total_urls if total_urls else 100

        for i, url in enumerate(self.urls):
            data = scrape_urls([url])
            if data:
                self.scraped_data.extend(data)
            self.update_progress((i + 1) * percent_per_link)
            time.sleep(random.uniform(1, 2))

        self.log(f"✅ {len(self.scraped_data)} cartes scrapées.")
        self.optimize_manual_button.configure(state="normal")

    def start_optimization(self):
        if not self.urls:
            messagebox.showwarning("Aucun lien", "Veuillez importer un fichier de liens avant de scraper.")
            return
        self.update_progress(0)
        threading.Thread(target=self.optimize_task, args=(True,)).start()

    def start_manual_optimization(self):
        if not self.scraped_data:
            messagebox.showwarning("Aucune donnée", "Veuillez d'abord scraper ou importer un JSON.")
            return
        threading.Thread(target=self.optimize_task, args=(False,)).start()

    def optimize_task(self, do_scraping):
        try:
            if do_scraping:
                self.scrape_task()

            self.log("⚙️ Optimisation en cours...")

            best_cart, best_cost, best_shipping, best_final, best_vendors = full_best_price(
                self.scraped_data,
                shipping_cost_per_vendor=8
            )
            optimized_cart, opt_cost, opt_shipping, opt_final, opt_vendors = optimize_cart(
                self.scraped_data,
                tolerance=0.10,
                shipping_cost_per_vendor=8
            )
            self.optimized_data = optimized_cart
            self.update_progress(100)

            # Arrondir les coûts finaux :
            # - Scénario 1 : arrondi à l'entier
            # - Scénario 2 : arrondi à 2 décimales
            comparison_text = (
                f"\n🔹 Comparaison des scénarios 🔹\n"
                f"--------------------------------------------------\n"
                f"   📌 Scénario 1️⃣ : On prend le meilleur prix à chaque fois\n"
                f"   👨‍💼 Nombre de vendeurs uniques : {best_vendors}\n"
                f"   💰 Coût total des cartes : {round(best_cost, 2)}€\n"
                f"   🚚 Frais de port estimés à environ : {round(best_shipping, 2)}€\n"
                f"   💳 Coût total final estimé à environ : {round(best_final)}€\n"
                f"--------------------------------------------------\n"
                f"   📌 Scénario 2️⃣ : On optimise le panier\n"
                f"   👨‍💼 Nombre de vendeurs uniques : {opt_vendors}\n"
                f"   💰 Coût total des cartes : {round(opt_cost, 2)}€\n"
                f"   🚚 Frais de port estimés à environ : {round(opt_shipping, 2)}€\n"
                f"   💳 Coût total final estimé à environ : {round(opt_final, 2)}€\n"
                f"--------------------------------------------------\n"
            )
            self.log(comparison_text)

            if opt_final < best_final:
                self.log("✅ La version optimisée est plus intéressante ! 🎯")
            else:
                self.log("🔴 Pas d'optimisation significative. Le scénario 1 est préférable.")

            # Affichage du bouton Export (centré)
            self.export_button.configure(state="normal")
            self.export_button.pack(pady=5, padx=20, anchor="center")

        except Exception as e:
            self.log(f"❌ Erreur lors de l'optimisation : {e}")
            messagebox.showerror("Erreur Optimisation", str(e))

    def export_results(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if file_path:
            try:
                df = pd.DataFrame(self.optimized_data)
                df.to_excel(file_path, index=False)
                self.log(f"📊 Fichier Excel enregistré : {file_path}")
                messagebox.showinfo("Export réussi", f"Fichier enregistré : {os.path.basename(file_path)}")
            except Exception as e:
                self.log(f"❌ Erreur lors de l'export : {e}")
                messagebox.showerror("Erreur Export", str(e))

# --- Point d'entrée ---
if __name__ == "__main__":
    app_root = ctk.CTk()
    app = ScrapOptimizerApp(app_root)
    app_root.mainloop()