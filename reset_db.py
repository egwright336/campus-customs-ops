"""Reset the working shop database to the original state.

    python reset_db.py

Copies data/campus_customs.db over data/campus_customs_new.db. The original is never written.
"""

import shutil

from config import DB_PATH, ORIGINAL_DB

if __name__ == "__main__":
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    DB_PATH.chmod(0o644)
    print(f"Reset {DB_PATH.name} from {ORIGINAL_DB.name}")
