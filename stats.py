import sqlite3

conn = sqlite3.connect("joblens.db")
cur = conn.cursor()

def count(table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]

print("===== JOBLENS DATABASE STATS =====")
print(f"Total Users: {count('users')}")
print(f"Total Uploads: {count('uploads')}")
print(f"Total Searches: {count('searches')}")
