from flask import Flask, request, jsonify, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
import secrets

'''
Koda realizēšanā tika izmantota Flask un SQLite3 dokumentācija:

https://flask.palletsprojects.com/en/2.3.x/patterns/sqlite3/
https://docs.python.org/3/library/sqlite3.html
'''

app = Flask(__name__)
DATABASE = "library.db"

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth(scheme='Bearer')

tokens = {}


@basic_auth.verify_password
def verify_password(username, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and check_password_hash(user[1], password):
        g.user_id = user[0]
        return True
    return False


@token_auth.verify_token
def verify_token(token):
    g.user_id = tokens.get(token)
    return g.user_id is not None


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    required_fields = ["username", "email", "password"]
    db = get_db()
    cursor = db.cursor()

    try:
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Incorrect data format"}), 400

        username = data["username"]
        email = data["email"]
        hashed_password = generate_password_hash(data["password"])

        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?",
                       (username, email))
        if cursor.fetchone():
            return jsonify({"message": "Username or email already registered"}), 409

        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, hashed_password))
        db.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify({"message": "User successfully created", "user_id": user_id}), 200


@app.route("/get_token", methods=["GET"])
@basic_auth.login_required
def get_token():
    token = secrets.token_hex(16)
    tokens[token] = g.user_id
    return jsonify({"token": token})


@app.route("/books", methods=["GET"])
@token_auth.login_required
def get_books():
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        books_list = [
            {"id": book[0], "title": book[1], "author": book[2], "year": book[3]}
            for book in books
        ]
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify(books_list), 200


@app.route("/books", methods=["POST"])
@token_auth.login_required
def create_book():
    data = request.get_json()
    required_fields = ["title", "author", "year"]
    db = get_db()
    cursor = db.cursor()

    try:
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing data"}), 400

        title = data["title"]
        author = data["author"]
        year_published = data["year"]

        cursor.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)",
                       (title, author, year_published))
        db.commit()
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify({"message": "Book successfully created"}), 200


@app.route("/user/<int:user_id>/books", methods=["GET"])
@token_auth.login_required
def user_books(user_id):
    if g.user_id != user_id:
        return jsonify({"message": "Access denied: You can access only your own data"}), 403

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            return jsonify({"message": "User not found"}), 404

        cursor.execute("""
        SELECT b.id, b.title, b.author, b.year, t.checkout_date, t.return_date
        FROM books b, transactions t
        WHERE t.book_id = b.id AND t.user_id = ? AND t.return_date IS NULL
        """, (user_id,))

        books_borrowed = cursor.fetchall()

        books_list = [
            {
                "book_id": book[0],
                "title": book[1],
                "author": book[2],
                "year": book[3],
                "checkout_date": book[4],
                "return_date":  "Not returned"
            }
            for book in books_borrowed
        ]
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify(books_list), 200


@app.route("/user/<int:user_id>/books/<int:book_id>", methods=["POST"])
@token_auth.login_required
def borrow_book(user_id, book_id):
    if g.user_id != user_id:
        return jsonify({"message": "Access denied: You can access only your own data"}), 403

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            return jsonify({"message": "User not found"}), 404

        cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        if not book:
            return jsonify({"message": "Book not found"}), 404

        cursor.execute("SELECT id FROM transactions WHERE book_id = ? AND return_date IS NULL",
                       (book_id,))
        if cursor.fetchone():
            return jsonify({"message": "Book is already taken"}), 400

        checkout_date = datetime.now().strftime("%Y-%M-%D %H:%M:%S")
        cursor.execute("INSERT INTO transactions (user_id, book_id, checkout_date) VALUES (?, ?, ?)",
                       (user_id, book_id, checkout_date))
        db.commit()
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify({"message": "Book is successfully taken"}), 200


@app.route("/user/<int:user_id>/books/<int:book_id>/return", methods=["POST"])
@token_auth.login_required
def return_book(user_id, book_id):
    if g.user_id != user_id:
        return jsonify({"message": "Access denied: You can access only your own data"}), 403

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT t.id
            FROM transactions t
            WHERE t.user_id = ? AND t.book_id = ? AND t.return_date IS NULL
            """, (user_id, book_id))
        transaction = cursor.fetchone()

        if transaction is None:
            return jsonify({"message": "Such book taken by such user is not found"}), 404

        return_date = datetime.now().strftime('%Y-%M-%D %H:%M:%S')
        cursor.execute("UPDATE transactions SET return_date = ? WHERE id = ?",
                       (return_date, transaction[0]))
        db.commit()
    except Exception as e:
        return jsonify({"error": True, "message": e.args[0]}), 500

    return jsonify({"message": "Book is successfully returned"}), 200


if __name__ == "__main__":
    app.run(debug=True)
