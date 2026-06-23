"""
extract_scraping.py — C1 : Extraction par scraping web
Source : Site public de fournitures professionnelles de nettoyage
Produit : data/raw/tarifs_scraping.csv

Logique :
- Scrape les tarifs publics d'un site de fournitures pro (robots.txt vérifié)
- Extrait : désignation produit, référence, prix HT, unité
- Ces données alimentent le catalogue articles de Nexo
- Gestion des erreurs : site indisponible, structure HTML modifiée
- Respect du robots.txt et délai entre requêtes (scraping éthique)

Note : En l'absence d'un site cible réel accessible sans authentification,
ce script scrape une page de démonstration publique (books.toscrape.com)
et adapte les données au format catalogue Nexo (produits de nettoyage simulés).
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from pathlib import Path
from urllib.parse import urljoin
import urllib.robotparser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "tarifs_scraping.csv"

TARGET_URL = "https://books.toscrape.com/catalogue/category/books_1/index.html"
BASE_URL = "https://books.toscrape.com"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
DELAY = 1.0
MAX_PAGES = 3

CATEGORIES_NETTOYAGE = [
    "Détergent sol", "Dégraissant multi-surfaces", "Désinfectant",
    "Produit vitres", "Décapant", "Cire sol", "Nettoyant sanitaires",
    "Détartrant", "Produit moquette", "Neutralisant odeurs",
    "Savon mains professionnel", "Gel hydroalcoolique",
    "Balai serpillière", "Raclette vitre", "Chariot de ménage",
    "Sac poubelle 100L", "Gants nitrile", "Microfibre sol",
    "Spray désinfectant", "Bidon 5L",
]


def check_robots_txt(url: str) -> bool:
    """
    Vérifie que le scraping est autorisé par le robots.txt du site.
    Retourne True si autorisé, False sinon.
    """
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
        allowed = rp.can_fetch("*", url)
        logger.info(f"robots.txt — scraping {'autorisé' if allowed else 'interdit'} sur {url}")
        return allowed
    except Exception as e:
        logger.warning(f"Impossible de lire robots.txt : {e} — scraping autorisé par défaut")
        return True


def scrape_page(url: str, session: requests.Session) -> list[dict]:
    """
    Scrape une page de produits et retourne une liste de dicts.
    Adapte les données au format catalogue Nexo (fournitures nettoyage).
    """
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête {url} : {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="product_pod")

    if not articles:
        logger.warning(f"Aucun article trouvé sur {url}")
        return []

    produits = []
    for i, article in enumerate(articles):
        try:
            titre_tag = article.find("h3")
            titre = titre_tag.find("a")["title"] if titre_tag else "Inconnu"

            prix_tag = article.find("p", class_="price_color")
            prix_str = prix_tag.text.strip().replace("£", "").replace("Â", "") if prix_tag else "0"
            try:
                prix_ht = round(float(prix_str) * 1.2, 2)
            except ValueError:
                prix_ht = 0.0

            designation = CATEGORIES_NETTOYAGE[i % len(CATEGORIES_NETTOYAGE)]
            reference = f"NETT-{len(produits)+1:04d}"

            produits.append({
                "reference": reference,
                "designation": designation,
                "description": f"Produit professionnel — {titre[:50]}",
                "type": "produit",
                "unite": "u" if "sac" in designation.lower() or "gants" in designation.lower() else "L",
                "prix_achat_ht": round(prix_ht * 0.7, 2),
                "prix_vente_ht": prix_ht,
                "taux_tva": 20.0,
                "source": "scraping",
            })

        except Exception as e:
            logger.warning(f"Erreur parsing article {i} : {e}")
            continue

    logger.info(f"{len(produits)} produits extraits depuis {url}")
    return produits


def get_next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    """Retourne l'URL de la page suivante ou None si dernière page."""
    next_btn = soup.find("li", class_="next")
    if next_btn:
        next_href = next_btn.find("a")["href"]
        return urljoin(current_url, next_href)
    return None


def main():
    logger.info("=== Démarrage scraping tarifs fournitures ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not check_robots_txt(TARGET_URL):
        logger.error("Scraping interdit par robots.txt — arrêt")
        return

    tous_produits = []
    url_courante = TARGET_URL
    page = 1

    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; NexoPipeline/1.0; educational)"
        })

        while url_courante and page <= MAX_PAGES:
            logger.info(f"Scraping page {page} : {url_courante}")
            produits = scrape_page(url_courante, session)
            tous_produits.extend(produits)

            response = session.get(url_courante, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            url_courante = get_next_page_url(soup, url_courante)
            page += 1

            if url_courante:
                time.sleep(DELAY)

    if not tous_produits:
        logger.error("Aucun produit extrait — vérifier la structure du site cible")
        return

    df = pd.DataFrame(tous_produits)
    df = df.drop_duplicates(subset=["reference"])

    logger.info(f"Total produits extraits : {len(df)}")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info(f"Fichier sauvegardé : {OUTPUT_FILE}")
    logger.info("=== Scraping terminé ===")


if __name__ == "__main__":
    main()
