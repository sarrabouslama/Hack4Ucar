import os
import re

directories_to_search = [
    r"c:\Hack4Ucar\app\modules",
    r"c:\Hack4Ucar\app\core"
]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # If the file contains the postgresql UUID import
    if 'from sqlalchemy.dialects.postgresql import UUID' in content or 'UUID, JSONB' in content or 'JSONB, UUID' in content:
        # Replacement 1: `from sqlalchemy.dialects.postgresql import UUID, JSONB` -> `from sqlalchemy.dialects.postgresql import JSONB\nfrom sqlalchemy import Uuid as UUID`
        content = content.replace(
            "from sqlalchemy.dialects.postgresql import UUID, JSONB",
            "from sqlalchemy.dialects.postgresql import JSONB\nfrom sqlalchemy import Uuid as UUID"
        )
        content = content.replace(
            "from sqlalchemy.dialects.postgresql import JSONB, UUID",
            "from sqlalchemy.dialects.postgresql import JSONB\nfrom sqlalchemy import Uuid as UUID"
        )
        content = content.replace(
            "from sqlalchemy.dialects.postgresql import UUID",
            "from sqlalchemy import Uuid as UUID"
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")

for d in directories_to_search:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.py'):
                process_file(os.path.join(root, file))

print("Done fixing UUIDs.")
