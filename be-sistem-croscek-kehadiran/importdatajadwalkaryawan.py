import pandas as pd
import mysql.connector
from datetime import datetime

# Fungsi untuk parse bulan dan tahun
def parse_month_year(month_year_str):
    dt = datetime.strptime(month_year_str, '%B %Y')
    return dt.year, dt.month

# Koneksi ke database MySQL
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='croscek_absen'
)
cursor = conn.cursor()

# Pastikan tabel sudah ada
cursor.execute("""
CREATE TABLE IF NOT EXISTS jadwal_karyawan (
    id_absen VARCHAR(20),
    nama VARCHAR(100),
    tanggal DATE,
    kode_shift VARCHAR(10)
)
""")

# Baca Excel tanpa header karena ada header custom
df = pd.read_excel('Roster - November 2025.xls', header=None)

# Ambil bulan dan tahun
month_year_str = df.iloc[1, 0]
year, month = parse_month_year(month_year_str)

# Ambil data mulai baris ke-6 (index 5)
data_rows = df.iloc[5:, :]

# Loop setiap baris
for _, row in data_rows.iterrows():
    id_absen = str(row[1]).strip()  # Kolom B
    nama = str(row[2]).strip()      # Kolom C

    for col_idx in range(3, len(row)):
        kode_shift = row[col_idx]
        
        # Masukkan semua kode_shift termasuk 'X', string khusus, dll
        if pd.notna(kode_shift):
            day = col_idx - 2  # kolom 3 = tanggal 1
            try:
                tanggal = datetime(year, month, day).date()
            except ValueError:
                # jika tanggal tidak valid (misal Feb 30), skip
                continue

            cursor.execute("""
            INSERT INTO jadwal_karyawan (id_absen, nama, tanggal, kode_shift)
            VALUES (%s, %s, %s, %s)
            """, (id_absen, nama, str(tanggal), str(kode_shift)))

# Commit dan tutup koneksi
conn.commit()
cursor.close()
conn.close()

print("Import data selesai tanpa mengubah isi!")
