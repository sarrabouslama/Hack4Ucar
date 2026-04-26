import sqlite3

try:
    conn = sqlite3.connect('hack4ucar.db', timeout=2)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM institutions")
    row = cursor.fetchone()
    print("Institutions count:", row[0])
    conn.close()
    print("DB is NOT locked!")
except Exception as e:
    print("ERROR:", e)
