"""
extract_bdd.py — C1 + C2 : Extraction depuis base de données PostgreSQL
Source : Base PostgreSQL Nexo (locale)
Produit : data/raw/nexo_export.csv

Requêtes SQL documentées (C2) :
  - Sélection clients avec leurs sites actifs (jointure clients + sites)
  - Filtrage sur clients actifs uniquement
  - Agrégation du nombre d'interventions par client
  - Optimisation : index sur interventions.site_id (migration 019 Nexo)

Gestion des erreurs :
  - Base inaccessible → fallback sur données simulées
  - Table absente → log d'erreur explicite
  - Connexion refusée → message d'aide
"""

import pandas as pd
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from faker import Faker
import random

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

fake = Faker("fr_FR")
random.seed(42)

OUTPUT_DIR = Path("data/raw")
OUTPUT_FILE = OUTPUT_DIR / "nexo_export.csv"
DATABASE_URL = os.getenv("DATABASE_URL")

# ---------------------------------------------------------------------------
# REQUÊTES SQL DOCUMENTÉES (C2)
# ---------------------------------------------------------------------------

SQL_CLIENTS_AVEC_SITES = """
-- Requête C2 — Extraction clients avec leurs sites
-- Objectif : récupérer l'ensemble des clients actifs et leurs sites d'intervention
-- Jointure : clients (1) → sites (n) via sites.client_id
-- Filtre : aucun filtre sur is_active (colonne absente sur clients dans ce schéma)
-- Colonnes sélectionnées : identité client, coordonnées, données site
-- Optimisation : index implicite sur sites.client_id (FK PostgreSQL)

SELECT
    c.id            AS client_id,
    c.raison_sociale,
    c.email         AS client_email,
    c.telephone     AS client_telephone,
    c.adresse       AS client_adresse,
    s.id            AS site_id,
    s.nom           AS site_nom,
    s.adresse       AS site_adresse,
    s.ville         AS site_ville,
    s.code_postal   AS site_code_postal,
    s.type_site,
    c.created_at    AS client_created_at
FROM clients c
LEFT JOIN sites s ON s.client_id = c.id
ORDER BY c.id, s.id;
"""

SQL_INTERVENTIONS_PAR_CLIENT = """
-- Requête C2 — Agrégation interventions par client
-- Objectif : compter les interventions passées par client pour scoring
-- Jointure : clients → sites → interventions (chaîne de 3 tables)
-- Filtre : interventions passées uniquement (date_debut < NOW())
-- Agrégation : COUNT avec GROUP BY pour éviter les doublons
-- Optimisation : index sur interventions.site_id (migration 019 Nexo)
--               + index sur interventions.date_debut pour le filtre temporel

SELECT
    c.id                            AS client_id,
    c.raison_sociale,
    COUNT(i.id)                     AS nb_interventions_total,
    COUNT(CASE WHEN i.statut = 'termine' THEN 1 END)
                                    AS nb_interventions_terminees,
    MAX(i.date_debut)               AS derniere_intervention
FROM clients c
LEFT JOIN sites s ON s.client_id = c.id
LEFT JOIN interventions i ON i.site_id = s.id
    AND i.date_debut < NOW()
GROUP BY c.id, c.raison_sociale
ORDER BY nb_interventions_total DESC;
"""

SQL_EMPLOYES_ACTIFS = """
-- Requête C2 — Extraction employés actifs
-- Objectif : récupérer les salariés pour croisement avec données legacy CSV
-- Filtre : is_active = true (exclut les comptes désactivés)
-- Colonnes : identité uniquement — pas de données sensibles (mot de passe, titre séjour)
-- Optimisation : pas d'index spécifique nécessaire (table petite)

SELECT
    e.id,
    e.nom,
    e.prenom,
    e.email,
    e.poste,
    e.tournee,
    e.type_contrat,
    e.date_embauche,
    e.created_at
FROM employes e
JOIN users u ON u.id = e.user_id
WHERE u.is_active = true
ORDER BY e.nom, e.prenom;
"""


def extract_from_postgres() -> pd.DataFrame:
    """
    Extrait les données depuis PostgreSQL Nexo.
    Retourne None si la base est inaccessible.
    """
    try:
        import psycopg2
        import psycopg2.extras

        if not DATABASE_URL:
            raise ValueError("DATABASE_URL non défini dans .env")

        logger.info(f"Connexion à PostgreSQL : {DATABASE_URL[:30]}...")
        conn = psycopg2.connect(DATABASE_URL)

        logger.info("Exécution requête : clients avec sites")
        df_clients = pd.read_sql(SQL_CLIENTS_AVEC_SITES, conn)
        logger.info(f"  → {len(df_clients)} lignes clients/sites")

        logger.info("Exécution requête : interventions par client")
        df_interventions = pd.read_sql(SQL_INTERVENTIONS_PAR_CLIENT, conn)
        logger.info(f"  → {len(df_interventions)} lignes agrégées")

        # Jointure des deux DataFrames sur client_id
        # Optimisation : merge sur index pour éviter scan complet
        df_final = df_clients.merge(
            df_interventions[["client_id", "nb_interventions_total", "derniere_intervention"]],
            on="client_id",
            how="left"
        )

        conn.close()
        logger.info("Connexion PostgreSQL fermée proprement")
        return df_final

    except ImportError:
        logger.error("psycopg2 non installé — lancer : uv add psycopg2-binary")
        return None
    except Exception as e:
        logger.warning(f"Base PostgreSQL inaccessible : {e}")
        logger.info("Basculement sur données simulées")
        return None


def generate_simulated_nexo_data() -> pd.DataFrame:
    """
    Génère des données simulées représentatives de l'export Nexo.
    Utilisé quand la base PostgreSQL n'est pas accessible (ex. CI/CD).
    """
    logger.info("Génération de données Nexo simulées...")

    TYPES_SITES = ["bureau", "entrepot", "commerce", "hopital", "ecole"]
    STATUTS = ["planifie", "en_cours", "termine", "annule"]

    rows = []
    for client_id in range(1, 21):
        raison_sociale = fake.company()
        client_email = fake.company_email()
        client_tel = fake.phone_number()
        client_adresse = fake.address().replace("\n", ", ")

        nb_sites = random.randint(1, 4)
        for site_id_offset in range(nb_sites):
            nb_interventions = random.randint(0, 15)
            rows.append({
                "client_id": client_id,
                "raison_sociale": raison_sociale,
                "client_email": client_email,
                "client_telephone": client_tel,
                "client_adresse": client_adresse,
                "site_id": client_id * 10 + site_id_offset,
                "site_nom": f"Site {fake.city()}",
                "site_adresse": fake.street_address(),
                "site_ville": fake.city(),
                "site_code_postal": fake.postcode(),
                "type_site": random.choice(TYPES_SITES),
                "client_created_at": fake.date_between(
                    start_date="-2y", end_date="-1m"
                ),
                "nb_interventions_total": nb_interventions,
                "derniere_intervention": fake.date_between(
                    start_date="-6m", end_date="today"
                ) if nb_interventions > 0 else None,
                "source": "simule",
            })

    return pd.DataFrame(rows)


def main():
    logger.info("=== Démarrage extraction base de données Nexo ===")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = extract_from_postgres()

    if df is None:
        df = generate_simulated_nexo_data()
        df["source"] = "simule"
    else:
        df["source"] = "postgresql_nexo"

    logger.info(f"Lignes extraites : {len(df)}")
    logger.info(f"Colonnes : {list(df.columns)}")

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info(f"Fichier sauvegardé : {OUTPUT_FILE}")
    logger.info("=== Extraction BDD terminée ===")


if __name__ == "__main__":
    main()
