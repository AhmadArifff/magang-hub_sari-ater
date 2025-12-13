# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import pandas as pd
from io import BytesIO
from datetime import datetime
import re
import calendar

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

# ============================================================
# AUTO-SYNC SHIFT_INFO SETIAP ADA PERUBAHAN informasi_jadwal
# ============================================================

def sync_shift_info():
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        # Ambil semua shift dari informasi_jadwal
        cur.execute("""
            SELECT kode, jam_masuk, jam_pulang
            FROM informasi_jadwal
            WHERE jam_masuk IS NOT NULL AND jam_pulang IS NOT NULL
        """)
        rows = cur.fetchall()

        synced = 0

        for r in rows:
            kode = r["kode"]
            jm = r["jam_masuk"]
            jp = r["jam_pulang"]

            # Deteksi lintas hari otomatis
            lintas = 1 if str(jp) < str(jm) else 0

            # Insert atau update shift_info
            cur.execute("""
                INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    jam_masuk = VALUES(jam_masuk),
                    jam_pulang = VALUES(jam_pulang),
                    lintas_hari = VALUES(lintas_hari)
            """, (kode, jm, jp, lintas))

            synced += 1

        conn.commit()
        cur.close()
        conn.close()

        print(f"[SYNC shift_info] {synced} shift diperbarui")

    except Exception as e:
        print("[SHIFT SYNC ERROR]:", e)
        

def sync_single_shift(kode):
    """Sinkronisasi satu shift berdasarkan kode tertentu"""
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        # Ambil 1 shift saja
        cur.execute("""
            SELECT kode, jam_masuk, jam_pulang
            FROM informasi_jadwal
            WHERE kode = %s
        """, (kode,))
        r = cur.fetchone()

        if not r:
            return  # Tidak ada datanya

        jm = r["jam_masuk"]
        jp = r["jam_pulang"]

        # Deteksi lintas hari
        lintas = 1 if str(jp) < str(jm) else 0

        # Insert/update shift_info
        cur.execute("""
            INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                jam_masuk = VALUES(jam_masuk),
                jam_pulang = VALUES(jam_pulang),
                lintas_hari = VALUES(lintas_hari)
        """, (kode, jm, jp, lintas))

        conn.commit()
        cur.close()
        conn.close()

        print(f"[SYNC] Shift {kode} diperbarui")

    except Exception as e:
        print("[SYNC SINGLE SHIFT ERROR]:", e)


def delete_single_shift(kode):
    """Hapus satu shift dari shift_info"""
    try:
        conn = db()
        cur = conn.cursor()

        cur.execute("DELETE FROM shift_info WHERE kode = %s", (kode,))

        conn.commit()
        cur.close()
        conn.close()

        print(f"[SYNC] Shift {kode} dihapus dari shift_info")

    except Exception as e:
        print("[DELETE SINGLE SHIFT ERROR]:", e)



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
        sync_shift_info()
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
        sync_single_shift(data.get("kode"))
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
        sync_single_shift(kode)
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
        delete_single_shift(kode)
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

        # cursor.execute("""
        # CREATE TABLE IF NOT EXISTS informasi_jadwal (
        #     kode VARCHAR(20) PRIMARY KEY,
        #     lokasi_kerja VARCHAR(50),
        #     nama_shift VARCHAR(100),
        #     jam_masuk TIME,
        #     jam_pulang TIME,
        #     keterangan VARCHAR(100),
        #     `group` VARCHAR(50),
        #     status VARCHAR(50),
        #     kontrol VARCHAR(50)
        # )
        # """)
        
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
        sync_shift_info()
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Upload sukses!"})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


# =========================
# Data KARYAWAN
# =========================
# =================== LIST Karyawan ===================
@app.route("/api/karyawan/list", methods=["GET"])
def get_karyawan():
    try:
        search = request.args.get("search", "")
        page = int(request.args.get("page", 1))
        limit = 10
        offset = (page - 1) * limit

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT COUNT(*) as total FROM karyawan
            WHERE nama LIKE %s OR nik LIKE %s
        """, (f"%{search}%", f"%{search}%"))
        total = cur.fetchone()["total"]

        cur.execute("""
            SELECT nik, nama, jabatan, dept FROM karyawan
            WHERE nama LIKE %s OR nik LIKE %s
            ORDER BY nama ASC
            LIMIT %s OFFSET %s
        """, (f"%{search}%", f"%{search}%", limit, offset))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify({"data": rows, "total": total}), 200
    except Exception as e:
        print("ERROR GET KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500


# =================== UPLOAD EXCEL ===================
@app.route("/api/karyawan/upload", methods=["POST"])
def upload_karyawan():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "File tidak ditemukan"}), 400

        raw = file.read()
        if len(raw) == 0:
            return jsonify({"error": "File excel kosong"}), 400

        df = pd.read_excel(BytesIO(raw))
        df.columns = [c.strip().upper() for c in df.columns]
        required = {"NAMA", "NIK", "JABATAN", "DEPT"}
        if not required.issubset(set(df.columns)):
            return jsonify({"error": f"Format kolom tidak sesuai template. Harus ada: {required}"}), 400

        df = df.dropna(subset=["NIK"])

        conn = get_db_connection()
        cur = conn.cursor()

        insert_count = 0
        update_count = 0
        duplicate_list = []   # daftar update detail

        for _, row in df.iterrows():
            nik = str(row["NIK"])
            nama = row["NAMA"]
            jabatan = row["JABATAN"]
            dept = row["DEPT"]

            # 🔍 cek duplicate by pair nik + nama
            cur.execute("""
                SELECT id_karyawan FROM karyawan 
                WHERE nik=%s AND nama=%s
            """, (nik, nama))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE karyawan SET jabatan=%s, dept=%s
                    WHERE id_karyawan=%s
                """, (jabatan, dept, existing[0]))
                update_count += 1
                duplicate_list.append({
                    "nik": nik,
                    "nama": nama,
                    "jabatan": jabatan,
                    "dept": dept
                })
            else:
                cur.execute("""
                    INSERT INTO karyawan (nik, nama, jabatan, dept)
                    VALUES (%s, %s, %s, %s)
                """, (nik, nama, jabatan, dept))
                insert_count += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Upload sukses! Insert: {insert_count}, Update: {update_count}",
            "updated_data": duplicate_list[:10],  
            "updated_total": update_count
        }), 200

    except Exception as e:
        print("ERROR UPLOAD KARYAWAN:", e)
        return jsonify({"error": "Kesalahan Server, cek log"}), 500




# =================== CREATE ===================
@app.route("/api/karyawan/create", methods=["POST"])
def create_karyawan():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO karyawan (nik, nama, jabatan, dept)
            VALUES (%s, %s, %s, %s)
        """, (
            data.get("nik"),
            data.get("nama"),
            data.get("jabatan"),
            data.get("dept")
        ))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Karyawan berhasil ditambahkan"}), 201
    except Exception as e:
        print("ERROR CREATE KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500


# =================== UPDATE ===================
@app.route("/api/karyawan/update/<nik>", methods=["PUT"])
def update_karyawan(nik):
    try:
        data = request.get_json(force=True)
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE karyawan
            SET nama=%s, jabatan=%s, dept=%s
            WHERE nik=%s
        """, (
            data.get("nama"),
            data.get("jabatan"),
            data.get("dept"),
            nik
        ))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data karyawan diperbarui"})
    except Exception as e:
        print("ERROR UPDATE KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500

# =================== DELETE ===================
@app.route("/api/karyawan/delete/<nik>", methods=["DELETE"])
def delete_karyawan(nik):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM karyawan WHERE nik=%s", (nik,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data karyawan dihapus"})
    except Exception as e:
        print("ERROR DELETE KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500
    

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": "Server bermasalah, cek log backend"}), 500



# =========================================================
# ==================  JADWAL KARYAWAN  ====================
# =========================================================

# ============================================================
# CREATE TABLES JIKA BELUM ADA
# ============================================================

def init_tables():
    conn = db()
    cur = conn.cursor()

    # ============================================
    # 0. TABEL KARYAWAN (BARU)
    # ============================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS karyawan (
            id_karyawan INT AUTO_INCREMENT PRIMARY KEY,
            nik VARCHAR(30),
            nama VARCHAR(100) NOT NULL,
            jabatan VARCHAR(50),
            dept VARCHAR(50),
            UNIQUE KEY uk_nik_nama (nik, nama)  -- jika mau kombinasi unik (opsional)
        );
    """)


    # ============================================
    # 1. TABEL INFORMASI JADWAL (PARENT)
    # ============================================
    cur.execute("""
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

    # ============================================
    # 2. TABEL SHIFT_INFO (CHILD 1)
    # ============================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_info (
            kode VARCHAR(20),
            jam_masuk TIME NOT NULL,
            jam_pulang TIME NOT NULL,
            lintas_hari TINYINT(1) NOT NULL,
            PRIMARY KEY (kode),
            CONSTRAINT fk_shiftinfo_kode 
                FOREIGN KEY (kode) REFERENCES informasi_jadwal(kode)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """)

    # ============================================
    # 3. TABEL JADWAL KARYAWAN (CHILD 2)
    # ============================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jadwal_karyawan (
            no INT AUTO_INCREMENT PRIMARY KEY,
            id_karyawan INT NULL,
            nama VARCHAR(100),
            tanggal DATE,
            kode_shift VARCHAR(20),

            CONSTRAINT fk_jadwal_kode
                FOREIGN KEY (kode_shift) REFERENCES informasi_jadwal(kode)
                ON DELETE CASCADE
                ON UPDATE CASCADE,

            CONSTRAINT fk_jadwal_nik
                FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan)
                ON DELETE SET NULL
                ON UPDATE CASCADE
        )
    """)

    # ============================================
    # 4. TABEL KEHADIRAN KARYAWAN (CHILD 3)
    # ============================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kehadiran_karyawan (
            tanggal_scan DATETIME NOT NULL,
            tanggal DATE NOT NULL,
            jam TIME NOT NULL,
            pin VARCHAR(20),
            id_karyawan INT NULL,
            nip VARCHAR(20),
            nama VARCHAR(100) NOT NULL,
            jabatan VARCHAR(50),
            departemen VARCHAR(50),
            kantor VARCHAR(50),
            verifikasi INT,
            io INT,
            workcode VARCHAR(20),
            sn VARCHAR(50),
            mesin VARCHAR(50),
            kode VARCHAR(20),

            CONSTRAINT fk_kehadiran_kode
                FOREIGN KEY (kode) REFERENCES informasi_jadwal(kode)
                ON DELETE SET NULL
                ON UPDATE CASCADE,

            CONSTRAINT fk_kehadiran_nik
                FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan)
                ON DELETE SET NULL
                ON UPDATE CASCADE
        )
    """)


    # ============================================
    # 5. TAMBAHKAN INDEX AGAR QUERY CEPAT (AMAN)
    # ============================================
    try:
        cur.execute("""
            ALTER TABLE kehadiran_karyawan 
                ADD INDEX idx_khd_nama_tanggal (nama, tanggal_scan),
                ADD INDEX idx_khd_nama_tgl (nama, tanggal)
        """)
    except:
        pass

    try:
        cur.execute("""
            ALTER TABLE jadwal_karyawan 
                ADD INDEX idx_jk_nama_tanggal (nama, tanggal)
        """)
    except:
        pass
    
    try:
        cur.execute("""
            ALTER TABLE kehadiran_karyawan 
                ADD INDEX idx_khd_nik_tanggal (nik, tanggal),
                ADD INDEX idx_khd_nama_tanggal (nama, tanggal_scan)
        """)
    except:
        pass

    try:
        cur.execute("""
            ALTER TABLE jadwal_karyawan 
                ADD INDEX idx_jk_nik_tanggal (nik, tanggal),
                ADD INDEX idx_jk_nama_tanggal (nama, tanggal)
        """)
    except:
        pass

    conn.commit()
    cur.close()
    conn.close()


init_tables()


# ============================================================
# HELPERS
# ============================================================
from calendar import monthrange
from datetime import datetime

def parse_month_year(month_year_str):
    """
    Convert “Desember 2025” → (2025, 12)
    Handles Indonesian month names and uses year from file.
    """
    # Mapping Indonesian month names to numbers
    bulan_indonesia = {
        "Januari": 1, "Februari": 2, "Maret": 3, "April": 4, "Mei": 5, "Juni": 6,
        "Juli": 7, "Agustus": 8, "September": 9, "Oktober": 10, "November": 11, "Desember": 12
    }
    
    # Strip whitespace and normalize
    month_year_str = month_year_str.strip()
    print(f"Raw month_year_str: '{repr(month_year_str)}'")  # Debug: lihat karakter tersembunyi
    
    # Split the string (assuming format "Bulan Tahun")
    parts = month_year_str.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid month_year format: {month_year_str}")
    
    bulan_str, tahun_str = parts
    bulan_str = bulan_str.capitalize()  # Normalize case (misalnya, "desember" -> "Desember")
    if bulan_str not in bulan_indonesia:
        raise ValueError(f"Unknown month: {bulan_str}")
    
    month = bulan_indonesia[bulan_str]
    try:
        year = int(tahun_str)
    except ValueError:
        raise ValueError(f"Invalid year: {tahun_str}")
    
    return year, month


# ============================================================
# CRUD JADWAL KARYAWAN (DISESUAIKAN DENGAN KOLOM BARU: nik, nama, tanggal, kode_shift)
# ============================================================


# Tambahkan Helper: Ambil NIK & ID dari Nama (Case-insensitive, trim)
def get_karyawan_by_nama(cursor, nama):
    if not nama:
        return None, None

    cursor.execute("""
        SELECT id_karyawan, nik
        FROM karyawan
        WHERE TRIM(LOWER(nama)) = TRIM(LOWER(%s))
        LIMIT 1
    """, (nama,))
    
    res = cursor.fetchone()
    if not res:
        return None, None

    # dictionary-safe
    if isinstance(res, dict):
        return res.get("id_karyawan"), res.get("nik")
    return res[0], res[1]



# -----------------------
# GET ALL jadwal_karyawan
# -----------------------
@app.route("/api/jadwal-karyawan/list", methods=["GET"])
def get_jadwal_karyawan():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                jk.*,                -- tampilkan semua kolom jadwal_karyawan
                k.nik,
                k.jabatan,
                k.dept
            FROM jadwal_karyawan jk
            LEFT JOIN karyawan k ON jk.nama = k.nama    -- sesuai permintaan join by name
            ORDER BY jk.no ASC
        """)
        rows = cursor.fetchall()

        # Convert tanggal ke string agar JSON aman
        for row in rows:
            if row["tanggal"]:
                row["tanggal"] = str(row["tanggal"])

        cursor.close()
        conn.close()
        return jsonify({
            "columns": ["no", "nik", "nama", "tanggal", "kode_shift"],
            "data": rows
        })

    except Exception as e:
        print("ERROR GET JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500



# -----------------------
# CREATE jadwal_karyawan
# -----------------------
@app.route("/api/jadwal-karyawan/create", methods=["POST"])
def create_jadwal_karyawan():
    try:
        data = request.json
        nama = data.get("nama")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        
        # 🔍 Ambil id_karyawan & nik berdasarkan nama
        cursor.execute("""
            SELECT id_karyawan, nik FROM karyawan WHERE nama=%s
        """, (nama,))
        emp = cursor.fetchone()

        if not emp:
            return jsonify({"error": f"Nama '{nama}' tidak ditemukan di tabel karyawan!"}), 400

        id_karyawan = emp["id_karyawan"]
        nik = emp["nik"]

        cursor.execute("""
            INSERT INTO jadwal_karyawan (id_karyawan,nama, tanggal, kode_shift)
            VALUES (%s,%s, %s, %s)
        """, (
            id_karyawan,
            nama,
            data.get("tanggal"),
            data.get("kode_shift")
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Jadwal berhasil dibuat"})

    except Exception as e:
        print("ERROR CREATE:", e)
        return jsonify({"error": str(e)}), 500





# -----------------------
# UPDATE jadwal_karyawan
# -----------------------
@app.route("/api/jadwal-karyawan/update/<int:no>", methods=["PUT"])
def update_jadwal_karyawan(no):
    try:
        data = request.get_json(force=True)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE jadwal_karyawan SET
                nama=%s,
                tanggal=%s,
                kode_shift=%s
            WHERE no=%s
        """, (
            data.get("nama"),
            data.get("tanggal"),
            data.get("kode_shift"),
            no
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Data jadwal karyawan berhasil diupdate"})

    except Exception as e:
        print("ERROR UPDATE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500




# -----------------------
# DELETE jadwal_karyawan
# -----------------------
@app.route("/api/jadwal-karyawan/delete/<int:no>", methods=["DELETE"])
def delete_jadwal_karyawan(no):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM jadwal_karyawan WHERE no=%s", (no,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Data jadwal karyawan berhasil dihapus"})

    except Exception as e:
        print("ERROR DELETE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500

# -----------------------
# CLEAR ALL jadwal_karyawan 
# -----------------------
@app.route("/api/jadwal-karyawan/clear", methods=["POST"])
def clear_jadwal_karyawan():
    print(">>> ROUTE CLEAR JADWAL DIPANGGIL <<<")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM jadwal_karyawan")
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "Semua jadwal berhasil dihapus", "status": "success"}), 200

    except Exception as e:
        print("ERROR CLEAR JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e), "status": "failed"}), 500



# ============================================================
# IMPORT JADWAL KARYAWAN — AUTO INCREMENT READY
# ============================================================
@app.route("/api/import-jadwal-karyawan", methods=["POST"])
def import_jadwal():
    if "file" not in request.files:
        return jsonify({"error": "File tidak ditemukan"}), 400

    file = request.files["file"]

    # Baca Excel
    try:
        df = pd.read_excel(file, header=None)
    except Exception as e:
        return jsonify({
            "error": f"Gagal membaca file Excel: {str(e)}"
        }), 500

    # Ambil bulan dan tahun
    try:
        month_year_str = str(df.iloc[1, 0]).strip()
        year, month = parse_month_year(month_year_str)
    except Exception as e:
        return jsonify({
            "error": f"Gagal parsing bulan/tahun: {str(e)}"
        }), 400

    days_in_month = monthrange(year, month)[1]

    # Data dimulai baris 6
    data = df.iloc[5:, :]

    conn = db()
    cur = conn.cursor()

    # 🔥 Ambil semua kode valid dari tabel informasi_jadwal
    cur.execute("SELECT kode FROM informasi_jadwal")
    valid_kode_shift = {row[0].strip() for row in cur.fetchall()}

    # Hapus jadwal lama bulan ini
    cur.execute("""
        DELETE FROM jadwal_karyawan
        WHERE YEAR(tanggal)=%s AND MONTH(tanggal)=%s
    """, (year, month))

    inserted_count = 0
    invalid_codes = []  # untuk menyimpan error kode tidak dikenali

    for idx, row in data.iterrows():
        nik = str(row[1]).strip() if pd.notna(row[1]) else ""
        nama = str(row[2]).strip() if pd.notna(row[2]) else ""

        if not nik or not nama:
            continue

        for col_idx in range(3, 3 + days_in_month):
            if col_idx >= len(row):
                break

            raw_kode = row[col_idx]

            if pd.isna(raw_kode):
                continue

            kode_shift = str(raw_kode).strip()

            if not kode_shift:
                continue

            # 🔥 CEK RELASI: apakah kode_shift ada di table informasi_jadwal?
            if kode_shift not in valid_kode_shift:
                invalid_codes.append({
                    "nik": nik,
                    "nama": nama,
                    "tanggal": f"{year}-{month}-{col_idx-2}",
                    "kode_shift": kode_shift
                })
                continue  # JANGAN INSERT

            # Tanggal
            day = col_idx - 2
            tanggal = datetime(year, month, day).date()

            # Insert data valid
            cur.execute("""
                INSERT INTO jadwal_karyawan (nik, nama, tanggal, kode_shift)
                VALUES (%s, %s, %s, %s)
            """, (nik, nama, tanggal, kode_shift))

            inserted_count += 1

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": f"Import selesai! {inserted_count} data berhasil disimpan.",
        "invalid_codes": invalid_codes  # tampilkan data yg gagal
    })



@app.route("/api/import-kehadiran", methods=["POST"])
def import_kehadiran():
    try:
        if "file" not in request.files:
            return jsonify({"error": "File tidak ditemukan"}), 400

        file = request.files["file"]

        df = pd.read_excel(file, header=1)
        df = df.fillna("")

        if len(df) > 0:
            df = df.iloc[1:]

        required = [
            "Tanggal scan", "Tanggal", "Jam", "Nama",
            "PIN", "NIP", "Jabatan", "Departemen", "Kantor",
            "Verifikasi", "I/O", "Workcode", "SN", "Mesin"
        ]

        for col in required:
            if col not in df.columns:
                return jsonify({"error": f"Kolom '{col}' tidak ditemukan di Excel"}), 400

        conn = db()
        cur = conn.cursor(dictionary=True)

        inserted_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            if str(row["Tanggal scan"]).strip() == "" or str(row["Tanggal"]).strip() == "":
                skipped_count += 1
                continue

            # ===============================
            # FIX FORMAT dd-mm-yyyy
            # ===============================
            try:
                tanggal_scan = pd.to_datetime(row["Tanggal scan"], dayfirst=True)
            except:
                return jsonify({"error": f"Format tanggal scan tidak valid (dd-mm-yyyy expected): {row['Tanggal scan']}"}), 400

            try:
                tanggal_only = pd.to_datetime(row["Tanggal"], dayfirst=True).date()
            except:
                return jsonify({"error": f"Format tanggal tidak valid (dd-mm-yyyy expected): {row['Tanggal']}"}), 400

            try:
                jam_only = pd.to_datetime(row["Jam"], dayfirst=True).time()
            except:
                return jsonify({"error": f"Format jam tidak valid: {row['Jam']}"}), 400

            verifikasi = int(row["Verifikasi"]) if row["Verifikasi"] != "" else None
            io = int(row["I/O"]) if row["I/O"] != "" else None

            # ===============================
            # COCOKKAN SHIFT
            # ===============================
            cur.execute("""
                SELECT kode_shift 
                FROM jadwal_karyawan
                WHERE nama = %s AND tanggal = %s
                LIMIT 1
            """, (row["Nama"], tanggal_only))

            result = cur.fetchone()
            kode_shift = result["kode_shift"] if result else None

            # ===============================
            # INSERT DATA
            # ===============================
            try:
                cur.execute("""
                    INSERT INTO kehadiran_karyawan (
                        tanggal_scan, tanggal, jam,
                        pin, nip, nama, jabatan, departemen, kantor,
                        verifikasi, io, workcode, sn, mesin, kode
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    tanggal_scan, tanggal_only, jam_only,
                    row["PIN"], row["NIP"], row["Nama"],
                    row["Jabatan"], row["Departemen"], row["Kantor"],
                    verifikasi, io, row["Workcode"], row["SN"], row["Mesin"],
                    kode_shift
                ))
            except Exception as e:
                conn.rollback()
                print("INSERT ERROR:", e)
                return jsonify({"error": f"Gagal insert data: {str(e)}"}), 400

            inserted_count += 1

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Import kehadiran selesai! {inserted_count} data disimpan, {skipped_count} dilewati."
        })

    except Exception as e:
        print("IMPORT ERROR:", e)
        return jsonify({"error": str(e)}), 500





# TAMBAHAN: ENDPOINT UNTUK MENDAPATKAN PERIODE BULAN-TAHUN UNIK DARI KEHADIRAN
@app.route("/api/kehadiran/available-periods", methods=["GET"])
def get_available_periods():
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)
        
        # Query untuk mendapatkan bulan dan tahun unik dari tabel kehadiran_karyawan
        query = """
        SELECT DISTINCT 
            MONTH(tanggal) AS bulan, 
            YEAR(tanggal) AS tahun
        FROM kehadiran_karyawan
        ORDER BY tahun DESC, bulan DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Format data sebagai list objek {bulan: int, tahun: int}
        periods = [{"bulan": row["bulan"], "tahun": row["tahun"]} for row in rows]
        
        return jsonify({"periods": periods})
    except Exception as e:
        print("ERROR GET PERIODS:", e)
        return jsonify({"error": str(e)}), 500

# TAMBAHAN: ENDPOINT UNTUK HAPUS DATA KEHADIRAN BERDASARKAN PERIODE BULAN-TAHUN
@app.route("/api/kehadiran/delete-period", methods=["DELETE"])
def delete_kehadiran_period():
    try:
        data = request.get_json()
        bulan = data.get("bulan")
        tahun = data.get("tahun")
        
        if not bulan or not tahun:
            return jsonify({"error": "Bulan dan tahun diperlukan"}), 400
        
        conn = db()
        cur = conn.cursor()
        
        # Query hapus berdasarkan bulan dan tahun
        query = "DELETE FROM kehadiran_karyawan WHERE MONTH(tanggal) = %s AND YEAR(tanggal) = %s"
        cur.execute(query, (bulan, tahun))
        conn.commit()
        
        deleted_count = cur.rowcount
        
        cur.close()
        conn.close()
        
        return jsonify({"message": f"Berhasil hapus {deleted_count} data kehadiran untuk periode {bulan}/{tahun}"})
    except Exception as e:
        print("ERROR DELETE PERIOD:", e)
        return jsonify({"error": str(e)}), 500



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
            base.Nama,
            base.Tanggal,
            base.Kode_Shift,
            base.Jabatan,
            base.Departemen,
            base.Jadwal_Masuk,
            base.Jadwal_Pulang,
            base.Actual_Masuk,
            base.Actual_Pulang,

            CASE
                WHEN base.Kode_Shift IN ('CT','CTT','EO','OF1','CTB','X')
                    THEN ij.keterangan
                WHEN base.Actual_Masuk IS NULL AND base.Actual_Pulang IS NULL
                    THEN 'Tidak Hadir'
                ELSE 'Hadir'
            END AS Status_Kehadiran,

            CASE
                WHEN base.Actual_Masuk IS NULL THEN 'Tidak scan masuk'
                WHEN base.Actual_Masuk <= base.Scheduled_Start THEN 'Masuk Tepat Waktu'
                ELSE 'Masuk Telat'
            END AS Status_Masuk,

            CASE
                WHEN base.Actual_Pulang IS NULL THEN 'Tidak scan pulang'
                WHEN base.Actual_Pulang >= base.Scheduled_End THEN 'Pulang Tepat Waktu'
                ELSE 'Pulang Terlalu Cepat'
            END AS Status_Pulang

        FROM (

            SELECT
                jk.nama AS Nama,
                jk.tanggal AS Tanggal,
                jk.kode_shift AS Kode_Shift,
                si.jam_masuk AS Jadwal_Masuk,
                si.jam_pulang AS Jadwal_Pulang,

                CASE WHEN si.jam_pulang < si.jam_masuk THEN 1 ELSE 0 END AS lintas_hari,

                -- Jabatan & Departemen terbaru hari itu
                (
                    SELECT k1.jabatan FROM kehadiran_karyawan k1
                    WHERE k1.nama = jk.nama AND k1.tanggal = jk.tanggal
                    ORDER BY k1.tanggal_scan ASC LIMIT 1
                ) AS Jabatan,

                (
                    SELECT k2.departemen FROM kehadiran_karyawan k2
                    WHERE k2.nama = jk.nama AND k2.tanggal = jk.tanggal
                    ORDER BY k2.tanggal_scan ASC LIMIT 1
                ) AS Departemen,

                CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) AS Scheduled_Start,

                CASE
                    WHEN si.jam_pulang < si.jam_masuk
                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                END AS Scheduled_End,

                (CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 4 HOUR) AS Range_Masuk_Start,
                (CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR) AS Range_Masuk_End,

                (CASE WHEN si.jam_pulang < si.jam_masuk
                    THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                END - INTERVAL 6 HOUR) AS Range_Pulang_Start,

                (CASE WHEN si.jam_pulang < si.jam_masuk
                    THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                END + INTERVAL 6 HOUR) AS Range_Pulang_End,

                -- FIRST SCAN MASUK (bukan MAX lagi)
                (
                    SELECT MIN(k3.tanggal_scan)
                    FROM kehadiran_karyawan k3
                    WHERE k3.nama = jk.nama
                    AND k3.tanggal_scan BETWEEN
                        (CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 4 HOUR)
                        AND (CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR)
                ) AS Actual_Masuk,

                -- FIRST SCAN PULANG (bukan MAX lagi)
                (
                    SELECT MIN(k4.tanggal_scan)
                    FROM kehadiran_karyawan k4
                    WHERE k4.nama = jk.nama
                    AND k4.tanggal_scan BETWEEN
                        (
                            CASE WHEN si.jam_pulang < si.jam_masuk
                                THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                            END - INTERVAL 6 HOUR
                        )
                        AND
                        (
                            CASE WHEN si.jam_pulang < si.jam_masuk
                                THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                            END + INTERVAL 6 HOUR
                        )
                ) AS Actual_Pulang

            FROM jadwal_karyawan jk
            LEFT JOIN shift_info si ON jk.kode_shift = si.kode

            GROUP BY
                jk.nama, jk.tanggal, jk.kode_shift,
                si.jam_masuk, si.jam_pulang

        ) AS base
        LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
        ORDER BY base.Nama, base.Tanggal;

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

# # Helper function yang bikin error
# def parse_month_year(month_year_str):
#     dt = datetime.strptime(month_year_str, '%B %Y')
#     return dt.year, dt.month

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)