"""
purge_audit_logs.py — C4 : Procédure de tri RGPD
Cible : table audit_logs de PostgreSQL Nexo
Fréquence : mensuelle (voir registre des traitements RGPD — T16)

Logique :
  - Supprime les entrées audit_logs dont created_at < NOW() - 1 an
  - Affiche le nombre de lignes supprimées
  - Log la purge dans un fichier local (hors audit_logs pour éviter récursion)
  - Vérification préalable avant suppression (SELECT COUNT)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "purge_audit.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
RETENTION_INTERVAL = "1 year"

SQL_COUNT = """
SELECT COUNT(*) FROM audit_logs
WHERE created_at < NOW() - INTERVAL %s;
"""

SQL_PURGE = """
DELETE FROM audit_logs
WHERE created_at < NOW() - INTERVAL %s
RETURNING id;
"""


def main():
    logger.info("=== Démarrage purge RGPD audit_logs ===")
    logger.info(f"Règle de rétention : {RETENTION_INTERVAL}")
    logger.info(f"Date d'exécution : {datetime.now().isoformat()}")

    try:
        import psycopg2

        if not DATABASE_URL:
            raise ValueError("DATABASE_URL non défini dans .env")

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute(SQL_COUNT, (RETENTION_INTERVAL,))
        nb_a_supprimer = cursor.fetchone()[0]
        logger.info(f"Lignes éligibles à la purge : {nb_a_supprimer}")

        if nb_a_supprimer == 0:
            logger.info("Aucune ligne à purger — base conforme RGPD")
            cursor.close()
            conn.close()
            return

        logger.info(f"Suppression de {nb_a_supprimer} entrées...")
        cursor.execute(SQL_PURGE, (RETENTION_INTERVAL,))
        ids_supprimes = cursor.fetchall()
        conn.commit()

        logger.info(f"Purge effectuée : {len(ids_supprimes)} entrées supprimées")
        cursor.close()
        conn.close()

    except ImportError:
        logger.error("psycopg2 non installé — lancer : uv add psycopg2-binary")
    except Exception as e:
        logger.error(f"Erreur lors de la purge : {e}")
        raise

    logger.info("=== Purge RGPD terminée ===")


if __name__ == "__main__":
    main()
