import sqlite3

conn = sqlite3.connect('smart_aiot.db')
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
# Check users table structure
if ('users',) in tables:
    columns = cursor.execute("PRAGMA table_info(users)").fetchall()
    print("\nUsers table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
        
conn.close()
