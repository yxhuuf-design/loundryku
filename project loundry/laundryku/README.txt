PANDUAN MENJALANKAN LAUNDRYKU

1. Jalankan Laragon, klik Start All (pastikan MySQL aktif).
2. Buka MySQL dan jalankan isi schema.sql jika database laundryku belum ada.
3. Salin .env.example menjadi .env. Jika password MySQL kosong, biarkan DB_PASSWORD=.
4. Buka folder laundryku di VS Code.
5. Di terminal VS Code jalankan:
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
6. Buka http://127.0.0.1:5000

LOGIN AWAL: admin
PASSWORD: admin123

app.py akan membuat tabel users, pelanggan, layanan, transaksi dan layanan contoh
secara otomatis. Backup database sebelum memakai aplikasi pada database yang berisi
data penting. Jika tabel lama memiliki struktur berbeda, jangan hapus atau timpa
database lama; gunakan database baru atau sesuaikan skema terlebih dahulu.
Ganti app.secret_key sebelum aplikasi dipublikasikan.
