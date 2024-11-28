import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('restaurantmenu.db')
cursor = conn.cursor()

# Execute a query to retrieve data from a table
cursor.execute("SELECT * FROM user;")
rows = cursor.fetchall()

# Print the results
for row in rows:
    print(row)

# Close the connection
conn.close()
