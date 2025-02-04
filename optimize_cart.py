import json
import pandas as pd
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def load_json(filename="data.json"):
    """Charge un fichier JSON contenant les infos de cartes scrapées."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.error(f"Erreur lors du chargement du JSON : {e}")
        return []

def full_best_price(cards, shipping_cost_per_vendor=8):
    """
    Scénario 1 : Prendre toujours l'offre la moins chère.
    - shipping_cost_per_vendor: frais de port fixe par vendeur unique.
    Retourne : (liste d'offres sélectionnées, coût total cartes, frais de port total, total final, nb vendeurs)
    """
    selected_offers = []
    vendor_totals = defaultdict(float)
    total_cost = 0.0

    for card in cards:
        offers = card.get("Offres", [])
        if not offers:
            # Carte sans offres
            continue

        # Choisir l'offre la moins chère
        best_offer = min(offers, key=lambda x: x["Prix"], default=None)
        if best_offer:
            selected_offers.append({
                "Nom de la carte": card["Nom de la carte"],
                "Extension": card["Extension"],
                "Vendeur": best_offer["Vendeur"],
                "Prix": best_offer["Prix"]
            })
            vendor_totals[best_offer["Vendeur"]] += best_offer["Prix"]
            total_cost += best_offer["Prix"]

    # Frais de port = shipping_cost_per_vendor * nb vendeurs
    num_vendors = len(vendor_totals)
    shipping_cost = shipping_cost_per_vendor * num_vendors
    final_total_cost = total_cost + shipping_cost

    return selected_offers, total_cost, shipping_cost, final_total_cost, num_vendors

def optimize_cart(cards, tolerance=0.10, shipping_cost_per_vendor=8):
    """
    Scénario 2 : Optimisation avancée pour réduire le nombre de vendeurs.
      - tolerance (float) : on peut payer jusqu'à +10% (par défaut) sur le prix minimal
        afin de regrouper les achats chez un même vendeur.
    Retourne : (liste d'offres sélectionnées, coût total cartes, frais de port total, total final, nb vendeurs)
    """
    selected_offers = []
    vendor_items = defaultdict(float)  # total d'achat par vendeur
    total_cost = 0.0

    # Trier les cartes par nombre d'offres disponibles (celles qui ont le moins d'offres en priorité)
    cards_sorted = sorted(cards, key=lambda x: len(x.get("Offres", [])))

    for card in cards_sorted:
        offers = card.get("Offres", [])
        if not offers:
            # Aucune offre pour cette carte
            continue

        # Trier les offres par prix croissant
        sorted_offers = sorted(offers, key=lambda x: x["Prix"])
        cheapest_price = sorted_offers[0]["Prix"]  # prix le moins cher

        best_offer = None
        # 1) Vérifier si on peut rester chez un vendeur déjà sélectionné sans payer trop
        for offer in sorted_offers:
            if offer["Vendeur"] in vendor_items:
                # différence par rapport au moins cher
                if (offer["Prix"] - cheapest_price) <= (shipping_cost_per_vendor / 2):
                    best_offer = offer
                    break

        # 2) Sinon, on accepte un écart jusqu'à tolerance
        if best_offer is None:
            for offer in sorted_offers:
                if offer["Prix"] <= cheapest_price * (1 + tolerance):
                    best_offer = offer
                    break

        # 3) Sinon, on prend tout simplement la moins chère
        if best_offer is None:
            best_offer = sorted_offers[0]

        # Ajouter l'offre retenue
        if best_offer:
            selected_offers.append({
                "Nom de la carte": card["Nom de la carte"],
                "Extension": card["Extension"],
                "Vendeur": best_offer["Vendeur"],
                "Prix": best_offer["Prix"]
            })
            vendor_items[best_offer["Vendeur"]] += best_offer["Prix"]
            total_cost += best_offer["Prix"]

    # Frais de port = shipping_cost_per_vendor * nb vendeurs uniques
    num_unique_vendors = len(vendor_items)
    total_shipping_cost = shipping_cost_per_vendor * num_unique_vendors
    final_total_cost = total_cost + total_shipping_cost

    return selected_offers, total_cost, total_shipping_cost, final_total_cost, num_unique_vendors

def save_to_excel(best_cart, best_vendors, best_cost, best_shipping, best_final,
                  optimized_cart, opt_vendors, opt_cost, opt_shipping, opt_final,
                  filename="optimized_cart.xlsx"):
    """
    Sauvegarde des deux scénarios dans un même Excel, avec un récapitulatif.
    """
    df_best = pd.DataFrame(best_cart)
    df_best["Scénario"] = "Full Best Price"

    df_opt = pd.DataFrame(optimized_cart)
    df_opt["Scénario"] = "Optimisé"

    # Résumé
    summary_data = pd.DataFrame({
        "Nom de la carte": ["TOTAL", "TOTAL"],
        "Extension": ["", ""],
        "Vendeur": [
            f"~ {best_vendors} vendeurs (Full Best Price)",
            f"~ {opt_vendors} vendeurs (Optimisé)"
        ],
        "Prix": [
            f"Cartes: ~{round(best_cost, 2)}€ | FDP: ~{round(best_shipping, 2)}€ | TOTAL: ~{round(best_final, 2)}€",
            f"Cartes: ~{round(opt_cost, 2)}€ | FDP: ~{round(opt_shipping, 2)}€ | TOTAL: ~{round(opt_final, 2)}€"
        ],
        "Scénario": ["", ""]
    })

    # Concaténer
    df_final = pd.concat([df_best, df_opt, summary_data], ignore_index=True)

    try:
        df_final.to_excel(filename, index=False, engine='openpyxl')
        logging.info(f"Résultats sauvegardés dans {filename}")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde Excel {filename} : {e}")


# Exemple d'exécution autonome
if __name__ == "__main__":
    data = load_json("data.json")

    if not data:
        logging.warning("Aucune donnée à optimiser. Vérifiez le fichier data.json.")
    else:
        # Scénario 1
        best_cart, best_cost, best_shipping, best_final, best_vendors = full_best_price(
            data,
            shipping_cost_per_vendor=8
        )

        # Scénario 2
        optimized_cart, opt_cost, opt_shipping, opt_final, opt_vendors = optimize_cart(
            data,
            tolerance=0.10,
            shipping_cost_per_vendor=8
        )

        logging.info("\n=== Scénario 1 : Full Best Price ===")
        logging.info(f"Vendeurs: {best_vendors}, "
                     f"Coût cartes: {best_cost:.2f}€, "
                     f"FDP: {best_shipping:.2f}€, "
                     f"Total: {best_final:.2f}€")

        logging.info("\n=== Scénario 2 : Optimisé ===")
        logging.info(f"Vendeurs: {opt_vendors}, "
                     f"Coût cartes: {opt_cost:.2f}€, "
                     f"FDP: {opt_shipping:.2f}€, "
                     f"Total: {opt_final:.2f}€")

        # Comparaison
        if opt_final < best_final:
            logging.info("La version optimisée est plus intéressante.")
        else:
            logging.info("Pas d'optimisation significative.")

        # Sauvegarde en Excel
        save_to_excel(
            best_cart, best_vendors, best_cost, best_shipping, best_final,
            optimized_cart, opt_vendors, opt_cost, opt_shipping, opt_final,
            filename="optimized_cart.xlsx"
        )