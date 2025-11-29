# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import pandas as pd
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

# -----------------------
# DATABASE CONNECTION
# -----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # ganti sesuai setting-mu
        database="croscek_absen"  # ganti sesuai nama DB
    )

def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="croscek_absen"
    )

# -----------------------
# GET ALL informasi jadwal
# -----------------------
@app.route("/api/list", methods=["GET"])
def get_jadwal():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT kode, lokasi_kerja, nama_shift, jam_masuk, jam_pulang,
                   keterangan, `group`, status, kontrol
            FROM informasi_jadwal
            ORDER BY kode ASC
        """)
        rows = cursor.fetchall()
        
        # Convert timedelta objects to strings for JSON serialization
        for row in rows:
            if row['jam_masuk'] is not None:
                row['jam_masuk'] = str(row['jam_masuk'])  # e.g., "08:30:00"
            if row['jam_pulang'] is not None:
                row['jam_pulang'] = str(row['jam_pulang'])  # e.g., "17:00:00"
        
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        print("ERROR GET LIST:", e)
        return jsonify({"error": str(e)}), 500


# -----------------------
# CREATE informasi jadwal
# -----------------------
@app.route("/api/create", methods=["POST"])
def create_jadwal():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO informasi_jadwal 
            (kode, lokasi_kerja, nama_shift, jam_masuk, jam_pulang, keterangan, `group`, status, kontrol)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get("kode"),
            data.get("lokasi_kerja"),
            data.get("nama_shift"),
            data.get("jam_masuk"),
            data.get("jam_pulang"),
            data.get("keterangan"),
            data.get("group"),
            data.get("status", "non-active"),
            data.get("kontrol", "")
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data berhasil ditambahkan"}), 201
    except Exception as e:
        print("ERROR CREATE:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# UPDATE informasi jadwal (PERBAIKAN)
# -----------------------
@app.route("/api/update/<kode>", methods=["PUT"])
def update_jadwal(kode):
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body"}), 400

        # Ambil dan normalisasi field yang diharapkan
        lokasi_kerja = data.get("lokasi_kerja") or ""
        nama_shift = data.get("nama_shift") or ""
        jam_masuk = data.get("jam_masuk")
        jam_pulang = data.get("jam_pulang")
        keterangan = data.get("keterangan") or ""
        group = data.get("group") or ""
        status = data.get("status") or "non-active"
        kontrol = data.get("kontrol") or ""

        # Normalisasi jam: kalau format "HH:MM" tambahkan :00
        def normalize_time(t):
            if t is None:
                return None
            t_str = str(t).strip()
            if t_str == "":
                return None
            # jika 'HH:MM' -> tambahkan ':00'
            if len(t_str) == 5 and t_str.count(":") == 1:
                return t_str + ":00"
            # jika mengandung ' ' atau ada milliseconds, ambil bagian jam:menit:detik terdepan
            if ":" in t_str:
                parts = t_str.split(":")
                # ensure at least 3 parts
                if len(parts) == 2:
                    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
            return None

        jam_masuk_db = normalize_time(jam_masuk)
        jam_pulang_db = normalize_time(jam_pulang)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Pastikan kode ada di DB (opsional, tapi membantu debugging)
        cursor.execute("SELECT COUNT(*) FROM informasi_jadwal WHERE kode=%s", (kode,))
        exists = cursor.fetchone()[0]
        if exists == 0:
            # Jika tidak ada, bisa pilih meng-insert atau return error. Kita return 404
            cursor.close()
            conn.close()
            return jsonify({"error": "Kode tidak ditemukan"}), 404

        cursor.execute("""
            UPDATE informasi_jadwal
            SET lokasi_kerja=%s, nama_shift=%s, jam_masuk=%s, jam_pulang=%s,
                keterangan=%s, `group`=%s, status=%s, kontrol=%s
            WHERE kode=%s
        """, (
            lokasi_kerja,
            nama_shift,
            jam_masuk_db,
            jam_pulang_db,
            keterangan,
            group,
            status,
            kontrol,
            kode
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data berhasil diupdate"})
    except Exception as e:
        print("ERROR UPDATE:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# DELETE informasi jadwal
# -----------------------
@app.route("/api/delete/<kode>", methods=["DELETE"])
def delete_jadwal(kode):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM informasi_jadwal WHERE kode=%s", (kode,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data berhasil dihapus"})
    except Exception as e:
        print("ERROR DELETE:", e)
        return jsonify({"error": str(e)}), 500

# ============================================================
# UPLOAD EXCEL OTOMATIS MASUK Tabel DATABASE informasi jadwal  — FULL FIX
# ============================================================

from flask import request, jsonify
import pandas as pd
from io import BytesIO

@app.route("/api/upload", methods=["POST"])
def upload_excel():
    try:
        file = request.files.get("file")
        if file is None:
            return jsonify({"error": "File tidak ada"}), 400

        raw = file.read()
        if len(raw) == 0:
            return jsonify({"error": "File kosong"}), 400

        # =====================================================
        # 1. BACA EXCEL DENGAN HEADER 2 BARIS (WAJIB!) 
        #    AGAR JAM MASUK & PULANG TERDETEKSI
        # =====================================================
        df = pd.read_excel(BytesIO(raw), header=[0, 1])

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

        return jsonify({"message": "Upload sukses!"})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500





# =========================================================
# ==================  JADWAL KARYAWAN  ====================
# =========================================================

# ============================================================
# CREATE TABLES JIKA BELUM ADA
# ============================================================

def init_tables():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password=''
    )
    cur = conn.cursor()

    cur.execute("CREATE DATABASE IF NOT EXISTS croscek_absen")
    cur.execute("USE croscek_absen")

    # JADWAL
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jadwal_karyawan (
            id_absen VARCHAR(20),
            nama VARCHAR(100),
            tanggal DATE,
            kode_shift VARCHAR(10)
        )
    """)

    # KEHADIRAN
    cur.execute("""
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

    conn.commit()
    cur.close()
    conn.close()


init_tables()


# ============================================================
# HELPERS
# ============================================================

def parse_month_year(month_year_str):
    """
    Convert “November 2025” → (2025, 11)
    """
    dt = datetime.strptime(month_year_str, '%B %Y')
    return dt.year, dt.month

# ============================================================
# CRUD JADWAL KARYAWAN (DISESUAIKAN DENGAN KOLOM BARU: id_absen, nama, tanggal, kode_shift)
# ============================================================

# -----------------------
# GET ALL jadwal_karyawan
# -----------------------
@app.route("/api/jadwal-karyawan/list", methods=["GET"])
def get_jadwal_karyawan():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_absen, nama, tanggal, kode_shift
            FROM jadwal_karyawan
            ORDER BY id_absen ASC
        """)
        rows = cursor.fetchall()
        
        # Convert to strings if needed
        for row in rows:
            if row['tanggal'] is not None:
                row['tanggal'] = str(row['tanggal'])
        
        cursor.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        print("ERROR GET JADWAL KARYAWAN LIST:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# CREATE jadwal_karyawan (DARI FORM)
# -----------------------
@app.route("/api/jadwal-karyawan/create", methods=["POST"])
def create_jadwal_karyawan():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jadwal_karyawan 
            (id_absen, nama, tanggal, kode_shift)
            VALUES (%s, %s, %s, %s)
        """, (
            data.get("id_absen"),
            data.get("nama"),
            data.get("tanggal"),
            data.get("kode_shift")
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data jadwal karyawan berhasil ditambahkan"}), 201
    except Exception as e:
        print("ERROR CREATE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# UPDATE jadwal_karyawan (ACTION UPDATE)
# -----------------------
@app.route("/api/jadwal-karyawan/update/<id_absen>", methods=["PUT"])
def update_jadwal_karyawan(id_absen):
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body"}), 400

        nama = data.get("nama") or ""
        tanggal = data.get("tanggal")
        kode_shift = data.get("kode_shift") or ""

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM jadwal_karyawan WHERE id_absen=%s", (id_absen,))
        exists = cursor.fetchone()[0]
        if exists == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "ID Absen tidak ditemukan"}), 404

        cursor.execute("""
            UPDATE jadwal_karyawan
            SET nama=%s, tanggal=%s, kode_shift=%s
            WHERE id_absen=%s
        """, (
            nama,
            tanggal,
            kode_shift,
            id_absen
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data jadwal karyawan berhasil diupdate"})
    except Exception as e:
        print("ERROR UPDATE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# DELETE jadwal_karyawan (ACTION DELETE)
# -----------------------
@app.route("/api/jadwal-karyawan/delete/<id_absen>", methods=["DELETE"])
def delete_jadwal_karyawan(id_absen):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jadwal_karyawan WHERE id_absen=%s", (id_absen,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data jadwal karyawan berhasil dihapus"})
    except Exception as e:
        print("ERROR DELETE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500


# ============================================================
# API — IMPORT JADWAL KARYAWAN
# ============================================================

@app.route("/api/import-jadwal-karyawan", methods=["POST"])
def import_jadwal():
    if "file" not in request.files:
        return jsonify({"error": "File tidak ditemukan"}), 400

    file = request.files["file"]

    df = pd.read_excel(file, header=None)

    # --- Ambil bulan & tahun ---
    month_year_str = df.iloc[1, 0]
    year, month = parse_month_year(str(month_year_str))

    # Data mulai baris ke-6
    data = df.iloc[5:, :]

    conn = db()
    cur = conn.cursor()

    for _, row in data.iterrows():
        id_absen = str(row[1]).strip()
        nama = str(row[2]).strip()

        for col_idx in range(3, len(row)):
            kode_shift = row[col_idx]

            if pd.notna(kode_shift):
                day = col_idx - 2  # kolom 3 = tanggal 1
                try:
                    tanggal = datetime(year, month, day).date()
                except:
                    continue

                cur.execute("""
                    INSERT INTO jadwal_karyawan (id_absen, nama, tanggal, kode_shift)
                    VALUES (%s, %s, %s, %s)
                """, (id_absen, nama, str(tanggal), str(kode_shift)))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Import jadwal selesai!"})


# ============================================================
# API — IMPORT KEHADIRAN
# ============================================================

@app.route("/api/import-kehadiran", methods=["POST"])
def import_kehadiran():
    if "file" not in request.files:
        return jsonify({"error": "File tidak ditemukan"}), 400

    file = request.files["file"]

    # HEADER ADA DI BARIS 2 → header=1
    df = pd.read_excel(file, header=1)
    df = df.fillna("")

    # DATA MULAI BARIS 3 → drop baris pertama setelah header
    if len(df) > 0:
        df = df.iloc[1:]

    required = [
        "Tanggal scan", "Tanggal", "Jam", "Nama",
        "PIN", "NIP", "Jabatan", "Departemen", "Kantor",
        "Verifikasi", "I/O", "Workcode", "SN", "Mesin"
    ]

    # VALIDASI HEADER
    for col in required:
        if col not in df.columns:
            return jsonify({"error": f"Kolom '{col}' tidak ditemukan di Excel"}), 400

    conn = db()
    cur = conn.cursor()

    for _, row in df.iterrows():

        # SKIP DATA KOSONG
        if str(row["Tanggal scan"]).strip() == "" or str(row["Tanggal"]).strip() == "":
            continue

        # ---------------------------------------------
        # FIX — PARSE TANGGAL SCAN (dd-mm-yyyy HH:MM:SS)
        # ---------------------------------------------
        try:
            tanggal_scan = datetime.strptime(str(row["Tanggal scan"]), "%d-%m-%Y %H:%M:%S")
        except:
            # Coba auto-convert jika Excel menyimpan sebagai datetime
            try:
                tanggal_scan = pd.to_datetime(row["Tanggal scan"])
            except:
                tanggal_scan = None

        # ---------------------------------------------
        # FIX — PARSE TANGGAL (dd-mm-yyyy)
        # ---------------------------------------------
        try:
            tanggal_only = datetime.strptime(str(row["Tanggal"]), "%d-%m-%Y").date()
        except:
            try:
                tanggal_only = pd.to_datetime(row["Tanggal"]).date()
            except:
                tanggal_only = None

        # ---------------------------------------------
        # FIX — PARSE JAM (HH:MM:SS)
        # ---------------------------------------------
        try:
            jam_only = datetime.strptime(str(row["Jam"]), "%H:%M:%S").time()
        except:
            try:
                jam_only = pd.to_datetime(row["Jam"]).time()
            except:
                jam_only = None

        verifikasi = int(row["Verifikasi"]) if row["Verifikasi"] != "" else None
        io = int(row["I/O"]) if row["I/O"] != "" else None

        cur.execute("""
            INSERT INTO kehadiran_karyawan (
                tanggal_scan, tanggal, jam,
                pin, nip, nama, jabatan, departemen, kantor,
                verifikasi, io, workcode, sn, mesin
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            tanggal_scan, tanggal_only, jam_only,
            row["PIN"], row["NIP"], row["Nama"],
            row["Jabatan"], row["Departemen"], row["Kantor"],
            verifikasi, io, row["Workcode"], row["SN"], row["Mesin"]
        ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Import kehadiran selesai!"})




# ===========================================================
# CROSCEK (QUERY LENGKAP SESUAI PERMINTAAN)
# ===========================================================
@app.route("/api/croscek", methods=["GET"])
def proses_croscek():
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        # Query logika croscek sesuai permintaan
        query = """
        SELECT
            *,
            
            -- STATUS KEHADIRAN (PERBAIKAN)
            CASE
                WHEN Actual_Masuk IS NULL AND Actual_Pulang IS NULL THEN 'Tidak Hadir'
                WHEN Actual_Masuk IS NOT NULL OR Actual_Pulang IS NOT NULL THEN 'Hadir'
            END AS Status_Kehadiran,

            -- STATUS MASUK
            CASE
                WHEN Actual_Masuk IS NULL THEN 'Tidak scan masuk'
                WHEN Actual_Masuk <= Jadwal_Masuk THEN 'Masuk Tepat Waktu'
                ELSE 'Masuk Telat'
            END AS Status_Masuk,

            -- STATUS PULANG
            CASE
                WHEN Actual_Pulang IS NULL THEN 'Tidak scan pulang'
                WHEN Actual_Pulang >= Jadwal_Pulang THEN 'Pulang Tepat Waktu'
                ELSE 'Pulang Terlalu Cepat'
            END AS Status_Pulang

        FROM (
            SELECT
                jk.nama AS Nama,
                jk.tanggal AS Tanggal,
                jk.kode_shift AS Kode_Shift,
                ij.jam_masuk AS Jadwal_Masuk,
                ij.jam_pulang AS Jadwal_Pulang,

                -- Actual Masuk valid
                MIN(
                    CASE 
                        WHEN kj.jam <= ADDTIME(ij.jam_masuk, '04:00:00')
                        THEN kj.jam
                    END
                ) AS Actual_Masuk,

                -- Actual Pulang valid
                MAX(
                    CASE 
                        WHEN kj.jam >= SUBTIME(ij.jam_pulang, '06:00:00')
                        THEN kj.jam
                    END
                ) AS Actual_Pulang

            FROM jadwal_karyawan jk
            LEFT JOIN informasi_jadwal ij
                ON jk.kode_shift = ij.kode
            LEFT JOIN kehadiran_karyawan kj
                ON jk.nama = kj.nama 
                AND jk.tanggal = kj.tanggal

            GROUP BY
                jk.nama,
                jk.tanggal,
                jk.kode_shift,
                ij.jam_masuk,
                ij.jam_pulang
        ) AS base
        ORDER BY Nama, Tanggal;


        """

        cur.execute(query)
        rows = cur.fetchall()

        # Convert TIME fields to strings for JSON serialization
        for row in rows:
            if row['Jadwal_Masuk'] is not None:
                row['Jadwal_Masuk'] = str(row['Jadwal_Masuk'])
            if row['Jadwal_Pulang'] is not None:
                row['Jadwal_Pulang'] = str(row['Jadwal_Pulang'])
            if row['Actual_Masuk'] is not None:
                row['Actual_Masuk'] = str(row['Actual_Masuk'])
            if row['Actual_Pulang'] is not None:
                row['Actual_Pulang'] = str(row['Actual_Pulang'])

        cur.close()
        conn.close()

        return jsonify({"data": rows})
    except Exception as e:
        print("ERROR CROSCEK:", e)
        return jsonify({"error": str(e)}), 500

# Helper function
def parse_month_year(month_year_str):
    dt = datetime.strptime(month_year_str, '%B %Y')
    return dt.year, dt.month

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
