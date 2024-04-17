import sqlite3

# Norādiet datu bāzes faila nosaukumu
database = 'library.db'

# SQL komandas tabulu izveidošanai
create_table_queries = [
    '''DROP TABLE IF EXISTS users;''',
    '''DROP TABLE IF EXISTS books;''',
    '''DROP TABLE IF EXISTS transactions;''',
    '''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    );''',
    '''CREATE TABLE books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL
    );''',
    '''CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        checkout_date TEXT NOT NULL,
        return_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    );'''
]

# Izveido savienojumu ar datu bāzi un izpilda SQL komandas
with sqlite3.connect(database) as conn:
    cursor = conn.cursor()
    for query in create_table_queries:
        cursor.execute(query)
    conn.commit()

print(f"The database '{database}' and all required tables have been created successfully.")
