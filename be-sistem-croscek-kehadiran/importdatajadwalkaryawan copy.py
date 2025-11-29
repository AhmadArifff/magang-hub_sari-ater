import pandas as pd
import mysql.connector
from datetime import datetime

# Fungsi untuk parse bulan dan tahun
def parse_month_year(month_year_str):
    dt = datetime.strptime(month_year_str, '%B %Y')
    return dt.year, dt.month

# Koneksi ke database MySQL (sesuaikan dengan konfigurasi XAMPP Anda)
conn = mysql.connector.connect(
    host='localhost',
    user='root',  # default user XAMPP
    password='',  # default password XAMPP (kosong)
    database='croscek_absen'  # ganti dengan nama database Anda, misal 'jadwal_db'
)
cursor = conn.cursor()

# Pastikan tabel sudah ada, jika belum buat
cursor.execute("""
CREATE TABLE IF NOT EXISTS jadwal_karyawan (
    id_absen VARCHAR(20),
    nama VARCHAR(100),
    tanggal DATE,
    kode_shift VARCHAR(10)
)
""")

# Baca file Excel (ganti 'schedule.xlsx' dengan nama file Anda)
df = pd.read_excel('Roster - November 2025.xls', header=None)

# Ekstrak bulan dan tahun dari baris 2 (index 1)
month_year_str = df.iloc[1, 0]
year, month = parse_month_year(month_year_str)

# Data karyawan mulai dari baris 6 (index 5)
data_rows = df.iloc[5:, :]

# Loop melalui setiap baris data karyawan
for index, row in data_rows.iterrows():
    id_absen = row[1]  # Kolom B: ID ABSEN
    nama = row[2]      # Kolom C: NAMA
    
    # Loop melalui kolom shift (kolom D sampai AH, index 3 sampai 32)
    for col_idx in range(3, 33):  # 3 sampai 32 (30 kolom)
        kode_shift = row[col_idx]
        
        # Jika kode_shift tidak kosong dan bukan 'X' (asumsikan 'X' berarti off)
        if pd.notna(kode_shift) and kode_shift != 'X':
            day = col_idx - 2  # Kolom 3 = hari 1, kolom 4 = hari 2, ..., kolom 32 = hari 30
            tanggal = f"{year}-{month:02d}-{day:02d}"
            
            # Insert ke database
            cursor.execute("""
            INSERT INTO jadwal_karyawan (id_absen, nama, tanggal, kode_shift)
            VALUES (%s, %s, %s, %s)
            """, (id_absen, nama, tanggal, kode_shift))

# Commit dan tutup koneksi
conn.commit()
cursor.close()
conn.close()

print("Import data selesai!")
