import sqlite3
import os

# Use the correct path depending on environment
if os.environ.get("RENDER") == "true":
    DB_NAME = "/tmp/attendance.db"  # Render deployment path
else:
    DB_NAME = "attendance.db"       # Local path

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Replace these with the actual usernames
advisers = ["your_username", "friend_username", "teacher_username"]

cursor.execute(
    "UPDATE users SET role='adviser' WHERE username IN ({})".format(
        ",".join("?"*len(advisers))
    ),
    advisers
)

conn.commit()
conn.close()
print("Roles updated successfully!")