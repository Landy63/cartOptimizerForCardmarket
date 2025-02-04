import json
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def extract_card_data(url, retries=3):
    """ Scrape les infos d'une carte et ses 10 meilleures offres, avec 3 tentatives max """

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")

    service = Service(ChromeDriverManager().install())

    attempt = 0
    while attempt < retries:
        attempt += 1
        driver = webdriver.Chrome(service=service, options=options)

        try:
            print(f"🔄 Tentative {attempt}/{retries} pour {url} ...")
            driver.get(url)
            wait = WebDriverWait(driver, 20)

            # 📌 Extraction du nom de la carte
            try:
                title_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.page-title-container h1')))
                card_name = title_container.text.split('(')[0].strip()
            except Exception:
                card_name = "Nom inconnu"

            # 📌 Extraction du nom de l'extension
            try:
                breadcrumb = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'nav[aria-label="breadcrumb"] span[property="name"]')))
                extension = breadcrumb[3].text if len(breadcrumb) > 3 else "Extension inconnue"
            except Exception:
                extension = "Extension inconnue"

            # 📌 Extraction des offres (10 max maintenant)
            offers = []
            try:
                offer_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.article-row")))

                for row in offer_rows[:10]:  # Prendre max 10 offres
                    try:
                        # 🔹 Vendeur
                        seller_name = row.find_element(By.CSS_SELECTOR, ".seller-name a").text.strip()

                        # 🔹 Prix avec correction du format
                        price_text = row.find_element(By.CSS_SELECTOR, ".price-container span.color-primary").text.strip()
                        price_text = re.sub(r"[^\d,.-]", "", price_text)
                        price_text = price_text.replace(",", ".")
                        price_text = re.sub(r"\.(?=\d{3})", "", price_text)

                        try:
                            price = float(price_text)
                        except ValueError:
                            print(f"⚠️ Problème de conversion pour le prix : {price_text}")
                            price = None

                        offers.append({
                            "Vendeur": seller_name,
                            "Prix": price
                        })
                    except Exception as e:
                        print(f"⚠️ Erreur en récupérant une offre : {e}")

            except Exception:
                print("⚠️ Impossible de récupérer les offres")
                offers = []

            driver.quit()
            return {
                "Nom de la carte": card_name,
                "Extension": extension,
                "Offres": offers
            }

        except Exception as e:
            print(f"❌ Erreur lors de la tentative {attempt} : {e}")
            driver.quit()
            if attempt < retries:
                print(f"⏳ Nouvelle tentative dans 2 secondes...")
                time.sleep(2)  # Réduction du temps d'attente

def save_to_json(data, filename="data.json"):
    """ Enregistre les données scrapées dans un fichier JSON """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✅ Données sauvegardées dans {filename}")

# 📌 Charger les URLs depuis un fichier texte
def load_urls_from_file(file_path):
    """ Lit un fichier contenant des URLs et retourne une liste """
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# 📌 Exportation en Excel
def save_to_excel(data, filename="scraped_data.xlsx"):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"✅ Données exportées dans {filename}")

# 📌 Scraper plusieurs cartes et stocker en JSON & Excel
def main():
    urls = load_urls_from_file("urls.txt")  # Assure-toi que ce fichier contient tes liens
    all_data = []

    for url in urls:
        print(f"🔍 Scraping de {url} ...")
        data = extract_card_data(url)
        if data:
            all_data.append(data)

    save_to_json(all_data)
    save_to_excel(all_data)  # Exporter aussi en Excel

if __name__ == "__main__":
    main()

def scrape_urls(url_list):
    """Scrape toutes les URLs de la liste et retourne les données sous forme de JSON."""
    all_data = []
    for url in url_list:
        data = extract_card_data(url)
        if data:
            all_data.append(data)
    return all_data

# Exécuter uniquement si ce fichier est lancé directement
if __name__ == "__main__":
    sample_urls = ["https://example.com/card1", "https://example.com/card2"]
    results = scrape_urls(sample_urls)
    print(json.dumps(results, indent=4, ensure_ascii=False))
