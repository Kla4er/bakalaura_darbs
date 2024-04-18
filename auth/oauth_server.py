from flask import Flask, request, jsonify, g
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from datetime import timedelta
import sqlite3

app_oauth = Flask("oauth_server")
app_oauth.config["SECRET_KEY"] = "oauth_server_secret_key"
DATABASE = "library.db"

jwt = JWTManager(app_oauth)


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app_oauth.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app_oauth.route("/auth", methods=["POST"])
def authenticate_user():
    credentials = request.json
    username = credentials.get("username")
    password = credentials.get("password")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and check_password_hash(user[1], password):
        access_token = create_access_token(identity=user[0], expires_delta=timedelta(minutes=15))
        return jsonify(access_token=access_token), 200

    return jsonify({"message": "Credentials are not correct"}), 401


@app_oauth.route("/verify_token", methods=["GET"])
@jwt_required()
def verify_token():
    return jsonify({"valid": True, "user_id": get_jwt_identity()}), 200


if __name__ == "__main__":
    app_oauth.run(port=5001, debug=True)
