import pandas as pd
import mysql.connector

# Koneksi ke MySQL (sesuaikan dengan konfigurasi XAMPP Anda)
conn = mysql.connector.connect(
    host='localhost',
    user='root',  # default user XAMPP
    password=''   # default password XAMPP (kosong)
)
cursor = conn.cursor()

# Buat database jika belum ada
database_name = 'croscek_absen'
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
cursor.execute(f"USE {database_name}")

# Buat tabel jika belum ada (kolom wajib: tanggal_scan, tanggal, jam, nama - set NOT NULL)
cursor.execute("""
CREATE TABLE IF NOT EXISTS kehadiran_karyawan (
    tanggal_scan DATETIME NOT NULL,
    tanggal DATE NOT NULL,
    jam TIME NOT NULL,
    pin VARCHAR(20),
    nip VARCHAR(20),
    nama VARCHAR(100) NOT NULL,
    jabatan VARCHAR(50),
    departemen VARCHAR(50),
    kantor VARCHAR(50),
    verifikasi INT,
    io INT,
    workcode VARCHAR(20),
    sn VARCHAR(50),
    mesin VARCHAR(50)
)
""")

# Baca file Excel (ganti 'kehadiran.xlsx' dengan nama file Anda)
df = pd.read_excel('data 25 nov.xlsx')

# Loop melalui setiap baris data dan insert ke database
for index, row in df.iterrows():
    # Ganti NaN dengan string kosong untuk kolom string, dan None untuk kolom INT jika kosong
    row = row.fillna('')
    
    # Handle kolom INT khusus (Verifikasi dan I/O): jika kosong, set ke None
    verifikasi = int(row['Verifikasi']) if row['Verifikasi'] != '' else None
    io = int(row['I/O']) if row['I/O'] != '' else None
    
    # Pastikan kolom wajib tidak kosong: Tanggal scan, Tanggal, Jam, Nama
    if (row['Tanggal scan'] != '' and row['Tanggal'] != '' and row['Jam'] != '' and row['Nama'] != ''):
        cursor.execute("""
        INSERT INTO kehadiran_karyawan (
            tanggal_scan, tanggal, jam, pin, nip, nama, jabatan, departemen, kantor, verifikasi, io, workcode, sn, mesin
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['Tanggal scan'],  # DATETIME (sebagai string, MySQL akan parse)
            row['Tanggal'],       # DATE (sebagai string)
            row['Jam'],           # TIME (sebagai string)
            row['PIN'],           # VARCHAR
            row['NIP'],           # VARCHAR
            row['Nama'],          # VARCHAR
            row['Jabatan'],       # VARCHAR
            row['Departemen'],    # VARCHAR
            row['Kantor'],        # VARCHAR
            verifikasi,           # INT (atau None)
            io,                   # INT (atau None)
            row['Workcode'],      # VARCHAR
            row['SN'],            # VARCHAR
            row['Mesin']          # VARCHAR
        ))

# Commit dan tutup koneksi
conn.commit()
cursor.close()
conn.close()

print("Import data kehadiran karyawan selesai!")
