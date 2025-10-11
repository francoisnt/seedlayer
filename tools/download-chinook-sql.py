import logging
import os
import re
from pathlib import Path

import requests

from .utils import get_repo_absolute_path

"""

This script download the chinook sql scripts for mssql, mysql, oracle, postgres and sqlite.

It strips the insert statements to only keep schema definition statements and create empty databases

It relies on the fact that each sql file contains a 'Populate Tables' section at the end with all 
the insert statements and it truncates each file at that point. 

"""

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


# Chinook release tag (update this to change the version)
CHINOOK_RELEASE_TAG = "v1.4.5"
# Base URL for Chinook SQL files
BASE_URL = f"https://github.com/lerocha/chinook-database/releases/download/{CHINOOK_RELEASE_TAG}/"
# Mapping of database types to their Chinook SQL files
CHINOOK_FILES = {
    "sqlite": "Chinook_Sqlite.sql",
    "postgres": "Chinook_PostgreSql.sql",
    "mysql": "Chinook_MySql.sql",
    "mssql": "Chinook_SqlServer.sql",
    "oracle": "Chinook_Oracle.sql",
}

repo_path = get_repo_absolute_path()
logger = logging.getLogger(__name__)


def download_sql_file(db_type: str, filename: str) -> str | None:
    """Download a Chinook SQL file and truncate at 'Populate Tables' comment.

    Args:
        db_type: Database type (e.g., 'sqlite', 'postgres')
        filename: Name of the SQL file (e.g., 'Chinook_Sqlite.sql')

    Returns:
        Path to the downloaded file or None if download fails
    """
    url = f"{BASE_URL}/{filename}"
    output_dir = Path(repo_path / "tests" / "integration" / "chinook-ddl-scripts")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{db_type}.sql")

    # Regex to match the 'Populate Tables' comment block
    stop_comment_pattern = re.compile(r"/\*+\s*Populate\s+Tables\s*\*+/", re.MULTILINE)

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        full_content = response.text
        if not full_content:
            logger.error(f"No content downloaded for {filename}")
            return None

        # Find the start index of the stop comment
        match = stop_comment_pattern.search(full_content)
        if match:
            # Truncate the content right before the comment starts
            truncated_content = full_content[: match.start()]
            logger.info(f"Truncated {filename} at 'Populate Tables' comment")
        else:
            truncated_content = full_content
            logger.warning(
                f"'Populate Tables' comment not found in {filename}; saving full content"
            )

        # Write the (truncated) content to the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(truncated_content)

        logger.info(f"Downloaded and processed {filename} to {output_path}")
        return output_path

    except requests.RequestException as e:
        logger.error(f"Failed to download {filename}: {e}")
        return None


def main() -> None:
    """Download Chinook SQL files and create schema-only versions."""
    for db_type, filename in CHINOOK_FILES.items():
        logger.info(f"Processing {db_type} SQL file: {filename}")
        result = download_sql_file(db_type, filename)
        if result:
            logger.info(f"Successfully processed {filename}")
        else:
            logger.error(f"Failed to process {filename}")


if __name__ == "__main__":
    main()
