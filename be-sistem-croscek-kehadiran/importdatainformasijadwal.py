import pandas as pd
import mysql.connector

# =========================
# KONFIGURASI KONEKSI MYSQL
# =========================
conn = mysql.connector.connect(
    host='localhost',
    user='root',      # default user XAMPP
    password=''       # default password XAMPP (kosong)
)
cursor = conn.cursor()

# =========================
# BUAT DATABASE DAN TABEL
# =========================
database_name = 'croscek_absen'
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
cursor.execute(f"USE {database_name}")

cursor.execute("""
CREATE TABLE IF NOT EXISTS informasi_jadwal (
    kode VARCHAR(20) PRIMARY KEY,
    lokasi_kerja VARCHAR(50),
    nama_shift VARCHAR(100),
    jam_masuk TIME,
    jam_pulang TIME,
    keterangan VARCHAR(100),
    `group` VARCHAR(50),
    status VARCHAR(50),
    kontrol VARCHAR(50)
)
""")

# =========================
# BACA FILE EXCEL
# =========================
# Gunakan header=[0,1] karena file Excel memiliki merged cells untuk "Jam Masuk/Pulang"
df = pd.read_excel('template_jadwal.xlsx', header=[0, 1])

# =========================
# RENAME COLUMNS SUPAYA MUDAH DIPAKAI
# =========================
df.columns = [
    'No', 'Lokasi_Kerja', 'Nama', 'Kode', 'Jam_Masuk', 'Jam_Pulang',
    'Keterangan', 'Group', 'Status', 'Kontrol'
]

# =========================
# LOOP DAN INSERT KE DATABASE
# =========================
for index, row in df.iterrows():
    # Ganti NaN dengan string kosong
    row = row.fillna('')

    # Pastikan kode tidak kosong (PRIMARY KEY)
    if row['Kode'] != '':
        cursor.execute("""
        INSERT INTO informasi_jadwal (
            kode, lokasi_kerja, nama_shift, jam_masuk, jam_pulang, keterangan, `group`, status, kontrol
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            lokasi_kerja = VALUES(lokasi_kerja),
            nama_shift = VALUES(nama_shift),
            jam_masuk = VALUES(jam_masuk),
            jam_pulang = VALUES(jam_pulang),
            keterangan = VALUES(keterangan),
            `group` = VALUES(`group`),
            status = VALUES(status),
            kontrol = VALUES(kontrol)
        """, (
            row['Kode'],
            row['Lokasi_Kerja'],
            row['Nama'],
            row['Jam_Masuk'],
            row['Jam_Pulang'],
            row['Keterangan'],
            row['Group'],
            row['Status'],
            row['Kontrol']
        ))

# =========================
# COMMIT DAN TUTUP KONEKSI
# =========================
conn.commit()
cursor.close()
conn.close()

print("Import data informasi jadwal selesai!")
