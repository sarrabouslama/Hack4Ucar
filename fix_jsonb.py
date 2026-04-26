import os

directories_to_search = [
    r"c:\Hack4Ucar\app\modules",
    r"c:\Hack4Ucar\app\core"
]

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False
    
    if 'from sqlalchemy.dialects.postgresql import JSONB' in content:
        content = content.replace(
            "from sqlalchemy.dialects.postgresql import JSONB",
            "from sqlalchemy import JSON as JSONB"
        )
        changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed JSONB in {filepath}")

for d in directories_to_search:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.py'):
                process_file(os.path.join(root, file))

print("Done fixing JSONB.")
