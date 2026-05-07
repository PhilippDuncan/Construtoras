import sqlite3
conn = sqlite3.connect("construtoras.db")
count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()
print(f"Companies in database: {count[0]}")
row = conn.execute("SELECT company, capital_note, growth_story FROM companies LIMIT 1").fetchone()
print(f"First row: {row}")
conn.close()