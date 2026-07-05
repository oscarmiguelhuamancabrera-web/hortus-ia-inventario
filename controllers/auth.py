from functools import wraps
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from models.database import execute, query

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["usuario"].strip()
        password = request.form["password"]
        try:
            user = query("SELECT * FROM usuarios WHERE usuario=%s AND activo=TRUE", (username,), one=True)
            if not user and username == "admin" and password == "123456":
                execute(
                    "INSERT INTO usuarios(nombre,usuario,password_hash,rol) VALUES(%s,%s,%s,%s) ON CONFLICT(usuario) DO NOTHING",
                    ("Administrador", "admin", generate_password_hash("123456"), "Administrador"),
                )
                user = query("SELECT * FROM usuarios WHERE usuario='admin'", one=True)
            if user and check_password_hash(user["password_hash"], password):
                session.update(usuario_id=user["id"], nombre=user["nombre"], rol=user["rol"])
                return redirect(url_for("main.dashboard"))
        except Exception as exc:
            flash(f"No se pudo conectar a la base de datos: {exc}", "danger")
            return render_template("login.html")
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

