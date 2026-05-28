from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "A user with that username or email already exists."}), 400

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session.permanent = True

    return jsonify({"message": "Account created.", "user": serialize_user(user)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Username/email and password are required."}), 400

    user = User.query.filter((User.username == identifier) | (User.email == identifier.lower())).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username/email or password."}), 401

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session.permanent = True

    return jsonify({"message": "Logged in.", "user": serialize_user(user)}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None}), 200

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return jsonify({"user": None}), 200

    return jsonify({"user": serialize_user(user)}), 200
