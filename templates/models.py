
from database import get_connection
from werkzeug.security import check_password_hash


def all_rows(sql, params=()):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def one_row(sql, params=()):
    rows = all_rows(sql, params)
    return rows[0] if rows else None


def run(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def login_user(username, password):
    user = one_row(
        "SELECT * FROM users WHERE username=%s",
        (username,)
    )

    if user and check_password_hash(user["password_hash"], password):
        return user

    return None


def dashboard():
    return {
        "pelanggan": one_row(
            "SELECT COUNT(*) AS n FROM pelanggan"
        )["n"],

        "transaksi": one_row(
            "SELECT COUNT(*) AS n FROM transaksi"
        )["n"],

        "proses": one_row(
            "SELECT COUNT(*) AS n FROM transaksi "
            "WHERE status IN ('Menunggu','Diproses')"
        )["n"],

        "pendapatan": one_row(
            "SELECT COALESCE(SUM(total_harga),0) AS n "
            "FROM transaksi "
            "WHERE status IN ('Selesai','Diambil')"
        )["n"],

        "terbaru": all_rows("""
            SELECT
                t.id,
                t.id AS id_transaksi,
                t.tanggal,
                t.berat_kg,
                t.total_harga,
                t.total_harga AS total,
                t.status,
                p.nama AS nama_pelanggan,
                l.nama_layanan AS nama_layanan
            FROM transaksi t
            JOIN pelanggan p ON p.id = t.pelanggan_id
            JOIN layanan l ON l.id = t.layanan_id
            ORDER BY t.id DESC
            LIMIT 8
        """)
    }


def pelanggan_list():
    return all_rows("""
        SELECT id, nama, no_hp, email, alamat
        FROM pelanggan
        ORDER BY id DESC
    """)


def layanan_list():
    return all_rows("""
        SELECT id, nama_layanan, harga_per_kg,
               estimasi_hari, keterangan
        FROM layanan
        ORDER BY id DESC
    """)


def transaksi_list():
    return all_rows("""
        SELECT
            t.id,
            t.id AS id_transaksi,
            t.tanggal,
            t.berat_kg,
            t.harga_per_kg,
            t.total_harga,
            t.total_harga AS total,
            t.status,
            t.catatan,
            p.nama AS nama_pelanggan,
            l.nama_layanan AS nama_layanan
        FROM transaksi t
        JOIN pelanggan p ON p.id = t.pelanggan_id
        JOIN layanan l ON l.id = t.layanan_id
        ORDER BY t.id DESC
    """)


def laporan_data(mulai=None, akhir=None):
    sql = """
        SELECT
            t.id,
            t.id AS id_transaksi,
            t.tanggal,
            t.berat_kg,
            t.total_harga,
            t.total_harga AS total,
            t.status,
            p.nama AS nama_pelanggan,
            l.nama_layanan AS nama_layanan
        FROM transaksi t
        JOIN pelanggan p ON p.id = t.pelanggan_id
        JOIN layanan l ON l.id = t.layanan_id
        WHERE t.status IN ('Selesai','Diambil')
    """

    params = []

    if mulai:
        sql += " AND DATE(t.tanggal) >= %s"
        params.append(mulai)

    if akhir:
        sql += " AND DATE(t.tanggal) <= %s"
        params.append(akhir)

    sql += " ORDER BY t.tanggal DESC"

    rows = all_rows(sql, tuple(params))

    total_pendapatan = sum(
        (r["total_harga"] or 0 for r in rows),
        0
    )

    return rows, total_pendapatan
