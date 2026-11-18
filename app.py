from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "filtration_app_secret_key"


# CONNEXION A LA BASE DE DONNEES
def get_db_connection():
    conn = sqlite3.connect("filtration.db")
    conn.row_factory = sqlite3.Row
    return conn


# INITIALISATION DE LA BASE DE DONNEES
def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            debit_initial REAL,
            concentration REAL,
            residus REAL,
            debit_filtre REAL,
            matiere_seche REAL,
            date_operation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# PAGE DE CONNEXION
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["username"] = username

            return redirect(url_for("dashboard"))

        flash("Nom d'utilisateur ou mot de passe incorrect.")

    return render_template("login.html")


# CREATION D'UN COMPTE
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()
            flash("Compte créé avec succès ! Connectez-vous.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Ce nom d'utilisateur existe déjà.")

        finally:
            conn.close()

    return render_template("register.html")


# TABLEAU DE BORD
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


# CALCUL DE FILTRATION
@app.route("/calcul", methods=["GET", "POST"])
def calcul():

    if "username" not in session:
        return redirect(url_for("login"))

    resultat = None

    if request.method == "POST":

        try:
            debit = float(request.form["debit"])
            concentration = float(request.form["concentration"])
            residus = float(request.form["residus"])

            if debit <= 0 or residus < 0 or residus > debit or not 0 <= concentration <= 100:

                flash("Veuillez vérifier les données saisies.")

            else:

                debit_filtre = debit - residus
                matiere_seche = debit * concentration / 100

                resultat = {
                    "debit_filtre": round(debit_filtre, 2),
                    "matiere_seche": round(matiere_seche, 2)
                }

                # ENREGISTREMENT DANS L'HISTORIQUE
                conn = get_db_connection()

                conn.execute("""
                    INSERT INTO historique
                    (username, debit_initial, concentration, residus,
                     debit_filtre, matiere_seche)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session["username"],
                    debit,
                    concentration,
                    residus,
                    debit_filtre,
                    matiere_seche
                ))

                conn.commit()
                conn.close()

        except ValueError:
            flash("Veuillez entrer des nombres valides.")

    return render_template("calcul.html", resultat=resultat)


# HISTORIQUE DES OPERATIONS
@app.route("/historique")
def historique():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    operations = conn.execute("""
        SELECT * FROM historique
        WHERE username = ?
        ORDER BY date_operation DESC
    """, (session["username"],)).fetchall()

    conn.close()

    return render_template(
        "historique.html",
        operations=operations
    )


# DECONNEXION
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# LANCEMENT DE L'APPLICATION
if __name__ == "__main__":

    init_db()

    app.run(debug=True)