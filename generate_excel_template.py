"""
generate_excel_template.py — Générateur de template Excel pour l'import Nexo

Produit : data/output/template_import_nexo.xlsx
Onglets : Clients (7 colonnes) + Salaries (8 colonnes), 3 lignes d'exemple chacun.

Usage :
    python generate_excel_template.py

Foxabrille remplit ce fichier avec ses vraies données puis l'importe via
l'interface Nexo (Admin → Import Excel).
"""

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/output")
OUTPUT_FILE = OUTPUT_DIR / "template_import_nexo.xlsx"


CLIENTS_COLUMNS = [
    "raison_sociale",
    "email",
    "telephone",
    "adresse",
    "ville",
    "code_postal",
    "siret",
]

CLIENTS_EXEMPLES = [
    {
        "raison_sociale": "Société Exemple SAS",
        "email": "contact@exemple.fr",
        "telephone": "01 23 45 67 89",
        "adresse": "12 rue de la Paix",
        "ville": "Paris",
        "code_postal": "75001",
        "siret": "12345678900012",
    },
    {
        "raison_sociale": "Copropriété Les Lilas",
        "email": "syndic@leslilas.fr",
        "telephone": "04 56 78 90 12",
        "adresse": "8 avenue des Fleurs",
        "ville": "Lyon",
        "code_postal": "69003",
        "siret": "",
    },
    {
        "raison_sociale": "Mairie de Villejuif",
        "email": "accueil@villejuif.fr",
        "telephone": "01 49 58 60 00",
        "adresse": "Place de la République",
        "ville": "Villejuif",
        "code_postal": "94800",
        "siret": "21940081600014",
    },
]

SALARIES_COLUMNS = [
    "nom",
    "prenom",
    "email",
    "telephone",
    "poste",
    "type_contrat",
    "date_embauche",
    "tournee",
]

SALARIES_EXEMPLES = [
    {
        "nom": "DUPONT",
        "prenom": "Marie",
        "email": "marie.dupont@foxabrille.fr",
        "telephone": "06 12 34 56 78",
        "poste": "Agent de nettoyage",
        "type_contrat": "CDI",
        "date_embauche": "15/03/2022",
        "tournee": "Nord",
    },
    {
        "nom": "MARTIN",
        "prenom": "Thomas",
        "email": "thomas.martin@foxabrille.fr",
        "telephone": "06 98 76 54 32",
        "poste": "Chef d'équipe",
        "type_contrat": "CDI",
        "date_embauche": "01/09/2020",
        "tournee": "Sud",
    },
    {
        "nom": "BENALI",
        "prenom": "Fatima",
        "email": "fatima.benali@foxabrille.fr",
        "telephone": "07 11 22 33 44",
        "poste": "Agent polyvalent",
        "type_contrat": "CDD",
        "date_embauche": "01/01/2024",
        "tournee": "Centre",
    },
]


def main() -> None:
    logger.info("=== Génération du template Excel Nexo ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df_clients = pd.DataFrame(CLIENTS_EXEMPLES, columns=CLIENTS_COLUMNS)
    df_salaries = pd.DataFrame(SALARIES_EXEMPLES, columns=SALARIES_COLUMNS)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df_clients.to_excel(writer, sheet_name="Clients", index=False)
        df_salaries.to_excel(writer, sheet_name="Salaries", index=False)

    logger.info(f"Template généré : {OUTPUT_FILE}")
    logger.info(f"  Onglet Clients  : {len(df_clients)} lignes d'exemple")
    logger.info(f"  Onglet Salaries : {len(df_salaries)} lignes d'exemple")
    logger.info("Remplissez ce fichier avec vos vraies données et importez-le via Nexo.")
    logger.info("=== Terminé ===")


if __name__ == "__main__":
    main()
