import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from decimal import Decimal, InvalidOperation
from werkzeug.security import generate_password_hash
from datetime import date
import models
from database import get_connection

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-only-key")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    sql = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            nama VARCHAR(100) NOT NULL
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS pelanggan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nama VARCHAR(100) NOT NULL,
            no_hp VARCHAR(25),
            email VARCHAR(120),
            alamat TEXT,
            dibuat_pada TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS layanan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nama_layanan VARCHAR(100) NOT NULL,
            harga_per_kg DECIMAL(12,2) NOT NULL,
            estimasi_hari INT DEFAULT 3,
            keterangan VARCHAR(255)
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS transaksi (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pelanggan_id INT NOT NULL,
            layanan_id INT NOT NULL,
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
            berat_kg DECIMAL(10,2) NOT NULL,
            harga_per_kg DECIMAL(12,2) NOT NULL,
            total_harga DECIMAL(12,2) NOT NULL,
            status ENUM(
                'Menunggu',
                'Diproses',
                'Selesai',
                'Diambil'
            ) DEFAULT 'Menunggu',
            catatan TEXT,
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan(id),
            FOREIGN KEY (layanan_id) REFERENCES layanan(id)
        ) ENGINE=InnoDB"""
    ]

    try:
        for statement in sql:
            cur.execute(statement)
        conn.commit()
    finally:
        cur.close()
        conn.close()

    if not models.one_row(
        "SELECT id FROM users WHERE username=%s",
        ("admin",)
    ):
        models.run(
            "INSERT INTO users(username,password_hash,nama) VALUES(%s,%s,%s)",
            ("admin", generate_password_hash("admin123"), "Administrator")
        )

    if not models.one_row("SELECT id FROM layanan LIMIT 1"):
        for item in [
            ("Reguler", 5000, 3, "Cuci dan setrika reguler"),
            ("Express", 8000, 1, "Layanan cepat"),
            ("Setrika", 4000, 2, "Setrika saja")
        ]:
            models.run(
                """INSERT INTO layanan
                (nama_layanan,harga_per_kg,estimasi_hari,keterangan)
                VALUES(%s,%s,%s,%s)""",
                item
            )


@app.context_processor
def inject_date():
    return {"today": date.today()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = models.login_user(
            request.form.get("username", "").strip(),
            request.form.get("password", "")
        )

        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["nama"] = user["nama"]
            return redirect(url_for("dashboard"))

        flash("Username atau password salah.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template(
        "index.html",
        data=models.dashboard()
    )


@app.route("/pelanggan", methods=["GET", "POST"])
@login_required
def pelanggan():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()

        if not nama:
            flash("Nama wajib diisi.", "danger")
        else:
            models.run(
                """INSERT INTO pelanggan
                (nama,no_hp,email,alamat)
                VALUES(%s,%s,%s,%s)""",
                (
                    nama,
                    request.form.get("no_hp", ""),
                    request.form.get("email", ""),
                    request.form.get("alamat", "")
                )
            )
            flash("Pelanggan ditambahkan.", "success")

        return redirect(url_for("pelanggan"))

    return render_template(
        "pelanggan.html",
        pelanggan=models.pelanggan_list()
    )


@app.route("/pelanggan/hapus/<int:id>", methods=["POST"])
@login_required
def hapus_pelanggan(id):
    try:
        models.run(
            "DELETE FROM pelanggan WHERE id=%s",
            (id,)
        )
        flash("Pelanggan dihapus.", "success")
    except Exception:
        flash(
            "Pelanggan sudah memiliki transaksi sehingga tidak dapat dihapus.",
            "danger"
        )

    return redirect(url_for("pelanggan"))


@app.route("/layanan", methods=["GET", "POST"])
@login_required
def layanan():
    if request.method == "POST":
        try:
            nama = request.form["nama_layanan"].strip()
            harga = Decimal(request.form["harga_per_kg"])
            hari = int(request.form["estimasi_hari"])

            if not nama or harga <= 0 or hari < 1:
                raise ValueError()

            models.run(
                """INSERT INTO layanan
                (nama_layanan,harga_per_kg,estimasi_hari,keterangan)
                VALUES(%s,%s,%s,%s)""",
                (
                    nama,
                    harga,
                    hari,
                    request.form.get("keterangan", "")
                )
            )

            flash("Layanan ditambahkan.", "success")

        except (ValueError, InvalidOperation, KeyError):
            flash("Data layanan tidak valid.", "danger")

        return redirect(url_for("layanan"))

    return render_template(
        "layanan.html",
        layanan=models.layanan_list()
    )


@app.route("/layanan/hapus/<int:id>", methods=["POST"])
@login_required
def hapus_layanan(id):
    try:
        models.run("DELETE FROM layanan WHERE id=%s", (id,))
        flash("Layanan dihapus.", "success")
    except Exception:
        flash("Layanan sudah dipakai transaksi sehingga tidak dapat dihapus.", "danger")
    return redirect(url_for("layanan"))


# HALAMAN TRANSAKSI
@app.route("/transaksi", methods=["GET", "POST"])
@login_required
def transaksi():
    if request.method == "POST":
        try:
            pid = int(request.form["pelanggan_id"])
            lid = int(request.form["layanan_id"])
            berat = Decimal(request.form["berat_kg"])

            service = models.one_row(
                "SELECT * FROM layanan WHERE id=%s", (lid,)
            )

            if not service or berat <= 0:
                raise ValueError()

            harga = Decimal(str(service["harga_per_kg"]))

            models.run("""
                INSERT INTO transaksi
                (pelanggan_id, layanan_id, berat_kg,
                 harga_per_kg, total_harga, status, catatan)
                VALUES (%s, %s, %s, %s, %s, 'Menunggu', %s)
            """, (
                pid, lid, berat, harga, berat * harga,
                request.form.get("catatan", "")
            ))

            flash("Transaksi berhasil disimpan.", "success")

        except (ValueError, InvalidOperation, KeyError):
            flash("Data transaksi tidak valid.", "danger")

        return redirect(url_for("transaksi"))

    return render_template(
        "transaksi.html",
        transaksi=models.transaksi_list(),
        pelanggan=models.pelanggan_list(),
        layanan=models.layanan_list()
    )


# CETAK NOTA
@app.route("/transaksi/nota/<int:id>")
@login_required
def cetak_nota(id):
    nota = models.one_row("""
        SELECT
            t.id,
            t.tanggal,
            t.berat_kg,
            t.harga_per_kg,
            t.total_harga,
            t.status,
            t.catatan,
            p.nama AS nama_pelanggan,
            p.no_hp,
            p.alamat,
            l.nama_layanan
        FROM transaksi t
        JOIN pelanggan p ON p.id = t.pelanggan_id
        JOIN layanan l ON l.id = t.layanan_id
        WHERE t.id = %s
    """, (id,))

    if not nota:
        flash("Transaksi tidak ditemukan.", "danger")
        return redirect(url_for("transaksi"))

    return render_template("nota.html", nota=nota)


# UPDATE STATUS TRANSAKSI
@app.route("/transaksi/status/<int:id>", methods=["POST"])
@login_required
def status_transaksi(id):
    status = request.form.get("status")

    if status not in ["Menunggu", "Diproses", "Selesai", "Diambil"]:
        flash("Status tidak valid.", "danger")
    else:
        models.run(
            "UPDATE transaksi SET status=%s WHERE id=%s",
            (status, id)
        )
        flash("Status transaksi diperbarui.", "success")

    return redirect(url_for("transaksi"))


@app.route("/laporan")
@login_required
def laporan():
    mulai = request.args.get("mulai") or None
    akhir = request.args.get("akhir") or None

    rows, total = models.laporan_data(mulai, akhir)

    return render_template(
        "laporan.html",
        laporan=rows,
        total=total,
        mulai=mulai or "",
        akhir=akhir or ""
    )


if __name__ == "__main__":
    try:
        init_db()

        print("Database berhasil diperiksa.")
        print("Login awal: admin / admin123")
        print("Aplikasi berjalan di http://127.0.0.1:5000")

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True,
            use_reloader=False
        )

    except Exception as e:
        print("ERROR APLIKASI:", repr(e))
        raise

