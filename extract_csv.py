"""
extract_csv.py — C1 : Extraction depuis fichier de données
Source : CSV legacy salariés (export avant migration vers Nexo)
Produit : data/raw/salaries_legacy.csv

Logique :
- Génère un fichier CSV simulant un export RH legacy (avant Nexo)
- Représente des salariés avec des formats hétérogènes (dates, téléphones)
- Ces données seront nettoyées et normalisées dans clean_aggregate.py
- En production : remplacer generate_legacy_csv() par lecture du vrai fichier
"""

import pandas as pd
import logging
from pathlib import Path
from faker import Faker
from datetime import datetime, timedelta
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("fr_FR")
random.seed(42)

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "salaries_legacy.csv"
LEGACY_CSV_INPUT = Path("data/input/salaries_legacy_source.csv")
NB_SALARIES_SIMULES = 50

POSTES = [
    "Agent de nettoyage",
    "Chef d'équipe",
    "Responsable de secteur",
    "Agent polyvalent",
    "Technicien de surface",
]

CONTRATS = ["CDI", "CDD", "Interim", "cdi", "C.D.I", "contrat durée indéterminée"]

TOURNEES = ["Nord", "Sud", "Est", "Ouest", "Centre", "nord", "SUD", ""]


def generate_legacy_csv() -> pd.DataFrame:
    """
    Génère un DataFrame simulant un export RH legacy avec formats hétérogènes.
    Reproduit les problèmes typiques d'un ancien système :
    - Dates dans plusieurs formats (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YY)
    - Téléphones avec/sans espaces, avec/sans indicatif
    - Champs vides ou NULL
    - Doublons intentionnels
    - Casse inconsistante (NOM, Nom, nom)
    """
    rows = []

    for i in range(NB_SALARIES_SIMULES):
        date_embauche = fake.date_between(start_date="-10y", end_date="-1y")

        format_date = random.choice(["fr", "iso", "court"])
        if format_date == "fr":
            date_str = date_embauche.strftime("%d/%m/%Y")
        elif format_date == "iso":
            date_str = date_embauche.strftime("%Y-%m-%d")
        else:
            date_str = date_embauche.strftime("%d-%m-%y")

        telephone = fake.phone_number()
        if random.random() < 0.3:
            telephone = telephone.replace(" ", "")
        if random.random() < 0.2:
            telephone = "+33" + telephone[1:]

        nom = fake.last_name()
        casse = random.choice(["upper", "title", "lower"])
        if casse == "upper":
            nom = nom.upper()
        elif casse == "lower":
            nom = nom.lower()

        contrat = random.choice(CONTRATS)
        tournee = random.choice(TOURNEES)
        poste = random.choice(POSTES)

        if random.random() < 0.1:
            telephone = ""
        if random.random() < 0.05:
            date_str = ""

        rows.append({
            "id_legacy": f"EMP{i+1:04d}",
            "NOM": nom,
            "prenom": fake.first_name(),
            "Email": fake.email(),
            "TELEPHONE": telephone,
            "date_embauche": date_str,
            "Poste": poste,
            "type_contrat": contrat,
            "tournee": tournee,
            "salaire_brut": round(random.uniform(1500, 3500), 2),
        })

    if len(rows) > 5:
        rows.extend(rows[:3])
        logger.info("3 doublons intentionnels ajoutés (simulation legacy)")

    return pd.DataFrame(rows)


def main():
    logger.info("=== Démarrage extraction fichier CSV legacy ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if LEGACY_CSV_INPUT.exists():
        logger.info(f"Lecture du fichier source : {LEGACY_CSV_INPUT}")
        try:
            df = pd.read_csv(LEGACY_CSV_INPUT, encoding="utf-8")
            logger.info(f"{len(df)} lignes lues depuis le fichier source")
        except Exception as e:
            logger.error(f"Erreur lecture fichier : {e}")
            raise
    else:
        logger.info(
            f"Fichier source non trouvé ({LEGACY_CSV_INPUT}) "
            f"— génération de {NB_SALARIES_SIMULES} salariés simulés"
        )
        df = generate_legacy_csv()

    logger.info(f"Colonnes : {list(df.columns)}")
    logger.info(f"Lignes extraites : {len(df)}")
    logger.info(f"Valeurs manquantes :\n{df.isnull().sum()}")

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info(f"Fichier sauvegardé : {OUTPUT_FILE}")
    logger.info("=== Extraction CSV legacy terminée ===")


if __name__ == "__main__":
    main()
