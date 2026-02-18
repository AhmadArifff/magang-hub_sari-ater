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

from datetime import time
# ============================
# DETEKSI LINTAS HARI (AMAN)
# ============================
# def detect_lintas_hari(jam_masuk, jam_pulang):
#     if not jam_masuk or not jam_pulang:
#         return 0

#     # Normalisasi TIME (anti MySQL driver aneh)
#     if not isinstance(jam_masuk, time):
#         jam_masuk = time.fromisoformat(str(jam_masuk))

#     if not isinstance(jam_pulang, time):
#         jam_pulang = time.fromisoformat(str(jam_pulang))

#     # Pulang <= Masuk → lintas hari (termasuk 24 jam)
#     return 1 if jam_pulang <= jam_masuk else 0
from datetime import time
# yang tidak terbaca untuk kode 3a dari 00:00 - 08:00
# def detect_lintas_hari(jam_masuk, jam_pulang):
#     if jam_masuk is None or jam_pulang is None:
#         return 0
#     return 1 if jam_pulang <= jam_masuk else 0

def detect_lintas_hari(kode, jam_masuk, jam_pulang):
    if jam_masuk is None or jam_pulang is None:
        return 0

    # RULE KHUSUS SHIFT MALAM
    if kode.upper() == '3A':
        return 1

    # RULE UMUM
    return 1 if jam_pulang <= jam_masuk else 0




# ============================================================
# AUTO-SYNC SHIFT_INFO SETIAP ADA PERUBAHAN informasi_jadwal
# ============================================================
# tidak jalan
# def sync_shift_info():
#     try:
#         conn = db()
#         cur = conn.cursor(dictionary=True)

#         cur.execute("""
#             SELECT kode, jam_masuk, jam_pulang
#             FROM informasi_jadwal
#             WHERE jam_masuk IS NOT NULL
#               AND jam_pulang IS NOT NULL
#         """)
#         rows = cur.fetchall()

#         SHIFT_LIBUR = ("CT", "CTT", "CTB", "EO", "OF1", "X")

#         synced = 0

#         for r in rows:
#             kode = r["kode"]
#             jm = r["jam_masuk"]
#             jp = r["jam_pulang"]

#             # Shift libur → TIDAK lintas hari
#             if kode in SHIFT_LIBUR:
#                 lintas = 0
#             else:
#                 lintas = detect_lintas_hari(jm, jp)

#             cur.execute("""
#                 INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
#                 VALUES (%s, %s, %s, %s)
#                 ON DUPLICATE KEY UPDATE
#                     jam_masuk = VALUES(jam_masuk),
#                     jam_pulang = VALUES(jam_pulang),
#                     lintas_hari = VALUES(lintas_hari)
#             """, (kode, jm, jp, lintas))

#             synced += 1

#         conn.commit()
#         cur.close()
#         conn.close()

#         print(f"[SYNC shift_info] selesai & valid ({synced} shift)")

#     except Exception as e:
#         print("[SHIFT SYNC ERROR]:", e)

def sync_shift_info():
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT kode, jam_masuk, jam_pulang
            FROM informasi_jadwal
            WHERE jam_masuk IS NOT NULL
              AND jam_pulang IS NOT NULL
        """)
        rows = cur.fetchall()

        for r in rows:
            kode = r["kode"]
            jm = r["jam_masuk"]
            jp = r["jam_pulang"]

            # lintas = detect_lintas_hari(jm, jp)
            lintas = lintas = detect_lintas_hari(kode, jm, jp)

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

        print("[SYNC shift_info] selesai & valid")

    except Exception as e:
        print("[SHIFT SYNC ERROR]:", e)


# jalan dedahult
# def sync_shift_info():
#     try:
#         conn = db()
#         cur = conn.cursor(dictionary=True)

#         # Ambil semua shift dari informasi_jadwal
#         cur.execute("""
#             SELECT kode, jam_masuk, jam_pulang
#             FROM informasi_jadwal
#             WHERE jam_masuk IS NOT NULL AND jam_pulang IS NOT NULL
#         """)
#         rows = cur.fetchall()

#         synced = 0

#         for r in rows:
#             kode = r["kode"]
#             jm = r["jam_masuk"]
#             jp = r["jam_pulang"]

#             # Deteksi lintas hari otomatis
#             lintas = 1 if str(jp) < str(jm) else 0

#             # Insert atau update shift_info
#             cur.execute("""
#                 INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
#                 VALUES (%s, %s, %s, %s)
#                 ON DUPLICATE KEY UPDATE
#                     jam_masuk = VALUES(jam_masuk),
#                     jam_pulang = VALUES(jam_pulang),
#                     lintas_hari = VALUES(lintas_hari)
#             """, (kode, jm, jp, lintas))

#             synced += 1

#         conn.commit()
#         cur.close()
#         conn.close()

#         print(f"[SYNC shift_info] {synced} shift diperbarui")

#     except Exception as e:
#         print("[SHIFT SYNC ERROR]:", e)
        
# tidak jalan
# def sync_single_shift(kode):
#     """Sinkronisasi satu shift berdasarkan kode tertentu (VERSI VALID)"""
#     try:
#         conn = db()
#         cur = conn.cursor(dictionary=True)

#         cur.execute("""
#             SELECT kode, jam_masuk, jam_pulang
#             FROM informasi_jadwal
#             WHERE kode = %s
#         """, (kode,))
#         r = cur.fetchone()

#         if not r:
#             return

#         jm = r["jam_masuk"]
#         jp = r["jam_pulang"]

#         SHIFT_LIBUR = ("CT", "CTT", "CTB", "EO", "OF1", "X")

#         # Shift libur → tidak lintas hari
#         if kode in SHIFT_LIBUR:
#             lintas = 0
#         else:
#             lintas = detect_lintas_hari(jm, jp)

#         cur.execute("""
#             INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
#             VALUES (%s, %s, %s, %s)
#             ON DUPLICATE KEY UPDATE
#                 jam_masuk = VALUES(jam_masuk),
#                 jam_pulang = VALUES(jam_pulang),
#                 lintas_hari = VALUES(lintas_hari)
#         """, (kode, jm, jp, lintas))

#         conn.commit()
#         cur.close()
#         conn.close()

#         print(f"[SYNC SINGLE] Shift {kode} valid & diperbarui")

#     except Exception as e:
#         print("[SYNC SINGLE SHIFT ERROR]:", e)

def sync_single_shift(kode):
    """Sinkronisasi satu shift berdasarkan kode tertentu"""
    try:
        conn = db()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT kode, jam_masuk, jam_pulang
            FROM informasi_jadwal
            WHERE kode = %s
        """, (kode,))
        r = cur.fetchone()

        if not r:
            return

        jm = r["jam_masuk"]
        jp = r["jam_pulang"]

        # lintas = detect_lintas_hari(jm, jp)
        lintas = detect_lintas_hari(kode, jm, jp)

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

        print(f"[SYNC SINGLE] Shift {kode} valid")

    except Exception as e:
        print("[SYNC SINGLE SHIFT ERROR]:", e)


# jalan dedahult
# def sync_single_shift(kode):
#     """Sinkronisasi satu shift berdasarkan kode tertentu"""
#     try:
#         conn = db()
#         cur = conn.cursor(dictionary=True)

#         # Ambil 1 shift saja
#         cur.execute("""
#             SELECT kode, jam_masuk, jam_pulang
#             FROM informasi_jadwal
#             WHERE kode = %s
#         """, (kode,))
#         r = cur.fetchone()

#         if not r:
#             return  # Tidak ada datanya

#         jm = r["jam_masuk"]
#         jp = r["jam_pulang"]

#         # Deteksi lintas hari
#         lintas = 1 if str(jp) < str(jm) else 0

#         # Insert/update shift_info
#         cur.execute("""
#             INSERT INTO shift_info (kode, jam_masuk, jam_pulang, lintas_hari)
#             VALUES (%s, %s, %s, %s)
#             ON DUPLICATE KEY UPDATE
#                 jam_masuk = VALUES(jam_masuk),
#                 jam_pulang = VALUES(jam_pulang),
#                 lintas_hari = VALUES(lintas_hari)
#         """, (kode, jm, jp, lintas))

#         conn.commit()
#         cur.close()
#         conn.close()

#         print(f"[SYNC] Shift {kode} diperbarui")

#     except Exception as e:
#         print("[SYNC SINGLE SHIFT ERROR]:", e)


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
        conn.commit()
        sync_single_shift(data.get("kode"))
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
        get_jadwal()
        sync_single_shift(kode)
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
        get_jadwal()
        conn.commit()
        delete_single_shift(kode)
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
        conn.commit()
        sync_shift_info()
        cursor.close()
        conn.close()

        return jsonify({"message": "Upload sukses!"})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"error": str(e)}), 500


# =========================
# Data KARYAWAN
# =========================


@app.route("/api/karyawan/list/nama", methods=["GET"])
def get_karyawan_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id_karyawan, nik, nama , jabatan, dept, id_absen
            FROM karyawan
            ORDER BY nama ASC
        """)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()
        # Debug: print jumlah data
        print(f"Total karyawan yang diambil: {len(rows)}")
        return jsonify(rows)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
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
            SELECT nik, nama, jabatan, dept, id_absen FROM karyawan
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
            id_absen = row["ID ABSEN"]

            # 🔍 cek duplicate by pair nik + nama
            cur.execute("""
                SELECT id_karyawan FROM karyawan 
                WHERE nik=%s AND nama=%s
            """, (nik, nama))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE karyawan SET jabatan=%s, dept=%s , id_absen=%s
                    WHERE id_karyawan=%s
                """, (jabatan, dept, id_absen, existing[0]))
                update_count += 1
                duplicate_list.append({
                    "nik": nik,
                    "nama": nama,
                    "jabatan": jabatan,
                    "dept": dept,
                    "id_absen": id_absen
                })
            else:
                cur.execute("""
                    INSERT INTO karyawan (nik, nama, jabatan, dept, id_absen)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nik, nama, jabatan, dept, id_absen))
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
            INSERT INTO karyawan (nik, nama, jabatan, dept, id_absen)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data.get("nik"),
            data.get("nama"),
            data.get("jabatan"),
            data.get("dept"),
            data.get("id_absen")
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
            SET nama=%s, jabatan=%s, dept=%s, id_absen=%s
            WHERE nik=%s
        """, (
            data.get("nama"),
            data.get("jabatan"),
            data.get("dept"),
            data.get("id_absen"),
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
def db_server():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=""
    )
    
def init_tables():
    
    # ==============================
    # STEP 1: CONNECT KE MYSQL SERVER
    # ==============================
    conn_server = db_server()
    cur_server = conn_server.cursor()

    cur_server.execute("""
        CREATE DATABASE IF NOT EXISTS croscek_absen
        CHARACTER SET utf8mb4
        COLLATE utf8mb4_unicode_ci;
    """)

    cur_server.close()
    conn_server.close()

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
            id_absen VARCHAR(50),
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
            shift_window_start DATETIME,
            shift_window_end DATETIME,

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
    # 4.1. TABEL Croscek (Hasil Proses Croscek)
    # ============================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS croscek (
            id_croscek INT AUTO_INCREMENT PRIMARY KEY,
            Nama VARCHAR(150) NOT NULL,
            Tanggal DATE NOT NULL,
            Kode_Shift VARCHAR(10),
            Jabatan VARCHAR(100),
            Departemen VARCHAR(100),
            id_karyawan INT NOT NULL,
            NIK VARCHAR(50) NOT NULL,
            Jadwal_Masuk TIME,
            Jadwal_Pulang TIME,
            Actual_Masuk DATETIME NULL,
            Actual_Pulang DATETIME NULL,
            Prediksi_Shift VARCHAR(50) DEFAULT NULL,
            Prediksi_Actual_Masuk DATETIME DEFAULT NULL,
            Prediksi_Actual_Pulang DATETIME DEFAULT NULL,
            Probabilitas_Prediksi VARCHAR(50),
            Confidence_Score VARCHAR(50),
            Frekuensi_Shift_Historis VARCHAR(50),
            Status_Kehadiran VARCHAR(50),
            Status_Masuk VARCHAR(50),
            Status_Pulang VARCHAR(50)
            # UNIQUE KEY uniq_karyawan_tanggal (id_karyawan, Tanggal)
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

    try:
        cur.execute("""
            ALTER TABLE croscek
                ADD UNIQUE KEY uq_croscek (id_karyawan, Tanggal, Kode_Shift);
        """)
    except:
        pass
    
    # Prediksi kode shift
    try:
        cur.execute("""
            ALTER TABLE kehadiran_karyawan
                ADD INDEX idx_khd_id_tanggal_scan (id_karyawan, tanggal_scan);
        """)
    except:
        pass
    try:
        cur.execute("""
            ALTER TABLE jadwal_karyawan
                ADD INDEX idx_jk_id_tanggal (id_karyawan, tanggal);
        """)
    except:
        pass
    try:
        cur.execute("""
            ALTER TABLE croscek
                ADD UNIQUE INDEX uq_croscek_id_tanggal_shift (id_karyawan, Tanggal, Kode_Shift);
        """)
    except:
        pass
    try:
        cur.execute("""
            ALTER TABLE kehadiran_karyawan
                ADD INDEX idx_khd_id_tanggal (id_karyawan, tanggal);
        """)
    except:
        pass
    try:
        cur.execute("""
            ALTER TABLE jadwal_karyawan
                ADD INDEX idx_jk_id_shift_tanggal (id_karyawan, kode_shift, tanggal);
        """)
    except:
        pass
    
    
    
    
    
    
    conn.commit()
    cur.close()
    conn.close()


init_tables()


# # ============================================================
# # HELPERS
# # ============================================================
# from calendar import monthrange
# from datetime import datetime

# def parse_month_year(month_year_str):
#     """
#     Convert “Desember 2025” → (2025, 12)
#     Handles Indonesian month names and uses year from file.
#     """
#     # Mapping Indonesian month names to numbers
#     bulan_indonesia = {
#         "Januari": 1, "Februari": 2, "Maret": 3, "April": 4, "Mei": 5, "Juni": 6,
#         "Juli": 7, "Agustus": 8, "September": 9, "Oktober": 10, "November": 11, "Desember": 12
#     }
    
#     # Strip whitespace and normalize
#     month_year_str = month_year_str.strip()
#     print(f"Raw month_year_str: '{repr(month_year_str)}'")  # Debug: lihat karakter tersembunyi
    
#     # Split the string (assuming format "Bulan Tahun")
#     parts = month_year_str.split()
#     if len(parts) != 2:
#         raise ValueError(f"Invalid month_year format: {month_year_str}")
    
#     bulan_str, tahun_str = parts
#     bulan_str = bulan_str.capitalize()  # Normalize case (misalnya, "desember" -> "Desember")
#     if bulan_str not in bulan_indonesia:
#         raise ValueError(f"Unknown month: {bulan_str}")
    
#     month = bulan_indonesia[bulan_str]
#     try:
#         year = int(tahun_str)
#     except ValueError:
#         raise ValueError(f"Invalid year: {tahun_str}")
    
#     return year, month

# ============================================================
# HELPERS
# ============================================================
from calendar import monthrange
from datetime import datetime
import re


def parse_month_year(raw_value):
    """
    Parse bulan dan tahun dari berbagai format input.
    
    Supported formats:
    - 'November 2025'
    - '11/11/2025' (ambil bulan dan tahun, abaikan tanggal)
    - '2025-11-01' atau '2025-11-01 00:00:00'
    - pandas.Timestamp object
    
    Returns:
        tuple: (year, month) as integers
    
    Raises:
        ValueError: jika format tidak dikenali
    """
    import pandas as pd
    
    # Handle pandas Timestamp
    if isinstance(raw_value, pd.Timestamp):
        return raw_value.year, raw_value.month
    
    # Convert to string and clean
    value_str = str(raw_value).strip()
    
    # Remove extra quotes (single or double)
    value_str = value_str.strip("'\"")
    
    print(f"🔍 Parsing: '{value_str}'")
    
    # Format 1: "November 2025" atau "november 2025"
    # Match: <bulan_nama> <tahun>
    month_names = {
        'januari': 1, 'january': 1,
        'februari': 2, 'february': 2,
        'maret': 3, 'march': 3,
        'april': 4,
        'mei': 5, 'may': 5,
        'juni': 6, 'june': 6,
        'juli': 7, 'july': 7,
        'agustus': 8, 'august': 8,
        'september': 9,
        'oktober': 10, 'october': 10,
        'november': 11,
        'desember': 12, 'december': 12
    }
    
    for month_name, month_num in month_names.items():
        if month_name in value_str.lower():
            # Extract year (4 digits)
            year_match = re.search(r'\b(20\d{2})\b', value_str)
            if year_match:
                year = int(year_match.group(1))
                print(f"✅ Parsed as '{month_name.title()} {year}' -> ({year}, {month_num})")
                return year, month_num
    
    # Format 2: "DD/MM/YYYY" atau "MM/DD/YYYY"
    # Kita asumsikan MM/DD/YYYY atau DD/MM/YYYY
    slash_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', value_str)
    if slash_match:
        part1, part2, year = slash_match.groups()
        part1, part2, year = int(part1), int(part2), int(year)
        
        # Detect format: jika part1 > 12, maka format DD/MM/YYYY
        if part1 > 12:
            day, month = part1, part2
        # Jika part2 > 12, maka format MM/DD/YYYY
        elif part2 > 12:
            month, day = part1, part2
        # Jika keduanya <= 12, asumsikan DD/MM/YYYY (format Indonesia)
        else:
            day, month = part1, part2
        
        print(f"✅ Parsed as date '{value_str}' -> ({year}, {month}) [day={day} ignored]")
        return year, month
    
    # Format 3: "YYYY-MM-DD" atau "YYYY-MM-DD HH:MM:SS"
    iso_match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})', value_str)
    if iso_match:
        year, month, day = iso_match.groups()
        year, month = int(year), int(month)
        print(f"✅ Parsed as ISO date '{value_str}' -> ({year}, {month}) [day ignored]")
        return year, month
    
    # Format 4: Try datetime parsing as fallback
    try:
        dt = datetime.strptime(value_str.split()[0], '%Y-%m-%d')
        print(f"✅ Parsed via datetime -> ({dt.year}, {dt.month})")
        return dt.year, dt.month
    except:
        pass
    
    # If all parsing fails
    raise ValueError(
        f"Format tidak dikenali: '{value_str}'. "
        f"Gunakan format: 'November 2025', '11/11/2025', atau '2025-11-01'"
    )


# ============================================================
# CRUD JADWAL KARYAWAN (DISESUAIKAN DENGAN KOLOM BARU: nik, nama, tanggal, kode_shift)
# ============================================================


@app.route("/api/jadwal-karyawan/list", methods=["GET"])
def get_jadwal_karyawan():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT jk.no, k.nik, k.nama, jk.tanggal, jk.kode_shift
            FROM jadwal_karyawan jk
            LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan
            ORDER BY jk.no ASC
        """)
        rows = cursor.fetchall()

        for row in rows:
            if row["tanggal"]:
                row["tanggal"] = str(row["tanggal"])

        cursor.close()
        conn.close()
        return jsonify(rows)

    except Exception as e:
        print("ERROR GET JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500
    
    
    
@app.route("/api/informasi-jadwal/list", methods=["GET"])
def get_informasi_jadwal():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT kode AS kode_shift, keterangan
            FROM informasi_jadwal
            ORDER BY kode ASC
        """)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(rows)

    except Exception as e:
        print("ERROR GET INFORMASI JADWAL:", e)
        return jsonify({"error": str(e)}), 500



# -----------------------
# CREATE jadwal_karyawan
# -----------------------
# @app.route("/api/jadwal-karyawan/create", methods=["POST"])
# def create_jadwal_karyawan():
#     try:
#         data = request.json
#         nik = data.get("nik")
#         kode_shift = data.get("kode_shift")
#         tanggal = data.get("tanggal")

#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Cari id_karyawan berdasarkan nik
#         cursor.execute("SELECT id_karyawan, nama FROM karyawan WHERE nik=%s", (nik,))
#         karyawan = cursor.fetchone()
#         if not karyawan:
#             return jsonify({"error": f"Karyawan dengan NIK {nik} tidak ditemukan"}), 404

#         id_karyawan = karyawan[0]
#         nama = karyawan[1]

#         # Insert
#         cursor.execute("""
#             INSERT INTO jadwal_karyawan (id_karyawan, nama, tanggal, kode_shift)
#             VALUES (%s, %s, %s, %s)
#         """, (id_karyawan, nama, tanggal, kode_shift))

#         conn.commit()
#         cursor.close()
#         conn.close()

#         return jsonify({"message": "Data jadwal karyawan berhasil ditambahkan"}), 201

#     except Exception as e:
#         print("ERROR CREATE JADWAL KARYAWAN:", e)
#         return jsonify({"error": str(e)}), 500

@app.route("/api/jadwal-karyawan/create", methods=["POST"])
def create_jadwal_karyawan():
    try:
        data = request.json
        nik = data.get("nik")
        kode_shift = data.get("kode_shift")
        tanggal = data.get("tanggal")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id_karyawan, nama FROM karyawan WHERE nik=%s",
            (nik,)
        )
        karyawan = cursor.fetchone()
        if not karyawan:
            return jsonify({"error": f"Karyawan dengan NIK {nik} tidak ditemukan"}), 404

        id_karyawan, nama = karyawan

        # INSERT jadwal
        cursor.execute("""
            INSERT INTO jadwal_karyawan (id_karyawan, nama, tanggal, kode_shift)
            VALUES (%s, %s, %s, %s)
        """, (id_karyawan, nama, tanggal, kode_shift))

        # Ambil no terakhir (row yang baru diinsert)
        no_jadwal = cursor.lastrowid

        # ===============================
        # UPDATE WINDOW START & END
        # ===============================
        cursor.execute("""
            UPDATE jadwal_karyawan jk
            JOIN shift_info si ON jk.kode_shift = si.kode
            SET
                jk.shift_window_start =
                    CASE
                        WHEN jk.kode_shift = '3A'
                            THEN CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00')
                        WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                            THEN NULL
                        WHEN si.lintas_hari = 1 AND si.jam_masuk > si.jam_pulang
                            THEN CONCAT(jk.tanggal, ' ', si.jam_masuk)
                        ELSE CONCAT(jk.tanggal, ' ', si.jam_masuk)
                    END,
                jk.shift_window_end =
                    CASE
                        WHEN jk.kode_shift = '3A'
                            THEN CONCAT(jk.tanggal, ' 11:00:00')
                        WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                            THEN NULL
                        WHEN si.lintas_hari = 1 AND si.jam_masuk > si.jam_pulang
                            THEN CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang)
                        ELSE CONCAT(jk.tanggal, ' ', si.jam_pulang)
                    END
            WHERE jk.no = %s
        """, (no_jadwal,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Data jadwal karyawan berhasil ditambahkan"}), 201

    except Exception as e:
        print("ERROR CREATE JADWAL KARYAWAN:", e)
        return jsonify({"error": str(e)}), 500





# -----------------------
# UPDATE jadwal_karyawan
# -----------------------
# @app.route("/api/jadwal-karyawan/update/<int:no>", methods=["PUT"])
# def update_jadwal_karyawan(no):
#     try:
#         data = request.get_json(force=True)
#         nik = data.get("nik")            # ambil NIK dari frontend
#         kode_shift = data.get("kode_shift")
#         tanggal = data.get("tanggal")

#         if not nik:
#             return jsonify({"error": "NIK harus diisi"}), 400

#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Cek jadwal ada?
#         cursor.execute("SELECT COUNT(*) FROM jadwal_karyawan WHERE no=%s", (no,))
#         if cursor.fetchone()[0] == 0:
#             return jsonify({"error": "Data jadwal tidak ditemukan"}), 404

#         # Cari id_karyawan berdasarkan NIK
#         cursor.execute("SELECT id_karyawan, nama FROM karyawan WHERE nik=%s", (nik,))
#         karyawan = cursor.fetchone()
#         if not karyawan:
#             return jsonify({"error": f"Karyawan dengan NIK {nik} tidak ditemukan"}), 404

#         id_karyawan, nama_db = karyawan

#         # Update jadwal
#         cursor.execute("""
#             UPDATE jadwal_karyawan SET
#                 id_karyawan=%s,
#                 nama=%s,
#                 tanggal=%s,
#                 kode_shift=%s
#             WHERE no=%s
#         """, (id_karyawan, nama_db, tanggal, kode_shift, no))

#         conn.commit()
        
#         # =========================
#         # TRUNCATE croscek
#         # =========================
#         cursor.execute("TRUNCATE TABLE croscek")
#         conn.commit()
#         cursor.close()
#         conn.close()

#         return jsonify({"message": "Data jadwal karyawan berhasil diupdate"})

#     except Exception as e:
#         print("ERROR UPDATE JADWAL KARYAWAN:", e)
#         return jsonify({"error": str(e)}), 500
@app.route("/api/jadwal-karyawan/update/<int:no>", methods=["PUT"])
def update_jadwal_karyawan(no):
    try:
        data = request.get_json(force=True)
        nik = data.get("nik")
        kode_shift = data.get("kode_shift")
        tanggal = data.get("tanggal")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM jadwal_karyawan WHERE no=%s",
            (no,)
        )
        if cursor.fetchone()[0] == 0:
            return jsonify({"error": "Data jadwal tidak ditemukan"}), 404

        cursor.execute(
            "SELECT id_karyawan, nama FROM karyawan WHERE nik=%s",
            (nik,)
        )
        karyawan = cursor.fetchone()
        if not karyawan:
            return jsonify({"error": f"Karyawan dengan NIK {nik} tidak ditemukan"}), 404

        id_karyawan, nama = karyawan

        # UPDATE jadwal utama
        cursor.execute("""
            UPDATE jadwal_karyawan SET
                id_karyawan=%s,
                nama=%s,
                tanggal=%s,
                kode_shift=%s
            WHERE no=%s
        """, (id_karyawan, nama, tanggal, kode_shift, no))

        # ===============================
        # UPDATE WINDOW START & END
        # ===============================
        cursor.execute("""
            UPDATE jadwal_karyawan jk
            JOIN shift_info si ON jk.kode_shift = si.kode
            SET
                jk.shift_window_start =
                    CASE
                        WHEN jk.kode_shift = '3A'
                            THEN CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00')
                        WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                            THEN NULL
                        WHEN si.lintas_hari = 1 AND si.jam_masuk > si.jam_pulang
                            THEN CONCAT(jk.tanggal, ' ', si.jam_masuk)
                        ELSE CONCAT(jk.tanggal, ' ', si.jam_masuk)
                    END,
                jk.shift_window_end =
                    CASE
                        WHEN jk.kode_shift = '3A'
                            THEN CONCAT(jk.tanggal, ' 11:00:00')
                        WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                            THEN NULL
                        WHEN si.lintas_hari = 1 AND si.jam_masuk > si.jam_pulang
                            THEN CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang)
                        ELSE CONCAT(jk.tanggal, ' ', si.jam_pulang)
                    END
            WHERE jk.no = %s
        """, (no,))

        # Reset hasil croscek
        cursor.execute("TRUNCATE TABLE croscek")

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
# @app.route("/api/import-jadwal-karyawan", methods=["POST"])
# def import_jadwal():
#     if "file" not in request.files:
#         return jsonify({"error": "File tidak ditemukan"}), 400

#     file = request.files["file"]

#     # Baca Excel
#     try:
#         df = pd.read_excel(file, header=None)
#     except Exception as e:
#         return jsonify({"error": f"Gagal membaca file Excel: {str(e)}"}), 500

#     # Ambil bulan dan tahun
#     try:
#         month_year_str = str(df.iloc[1, 0]).strip()
#         year, month = parse_month_year(month_year_str)
#     except Exception as e:
#         return jsonify({"error": f"Gagal parsing bulan/tahun: {str(e)}"}), 400

#     days_in_month = monthrange(year, month)[1]
#     data = df.iloc[5:, :]

#     conn = db()
#     cur = conn.cursor()

#     # Ambil semua kode valid
#     cur.execute("SELECT kode FROM informasi_jadwal")
#     valid_kode_shift = {row[0].strip() for row in cur.fetchall()}

#     # Ambil semua id_karyawan dari database sekali saja
#     cur.execute("SELECT id_karyawan, nik, nama FROM karyawan")
#     karyawan_dict = {row[1]: {"id": row[0], "nama": row[2]} for row in cur.fetchall()}

#     # Hapus jadwal lama bulan ini
#     cur.execute("DELETE FROM jadwal_karyawan WHERE YEAR(tanggal)=%s AND MONTH(tanggal)=%s", (year, month))
#     conn.commit()

#     inserted_count = 0
#     invalid_codes = []
#     batch_size = 500  # commit setiap 500 insert
#     batch_counter = 0

#     for idx, row in data.iterrows():
#         nik = str(row[1]).strip() if pd.notna(row[1]) else ""
#         nama_excel = str(row[2]).strip() if pd.notna(row[2]) else ""

#         if not nik or nik not in karyawan_dict:
#             invalid_codes.append({
#                 "nik": nik,
#                 "nama": nama_excel,
#                 "error": "Karyawan tidak ditemukan"
#             })
#             continue

#         id_karyawan = karyawan_dict[nik]["id"]
#         nama = karyawan_dict[nik]["nama"]

#         for col_idx in range(3, 3 + days_in_month):
#             if col_idx >= len(row):
#                 break

#             raw_kode = row[col_idx]
#             if pd.isna(raw_kode):
#                 continue

#             kode_shift = str(raw_kode).strip()
#             if not kode_shift:
#                 continue

#             if kode_shift not in valid_kode_shift:
#                 invalid_codes.append({
#                     "nik": nik,
#                     "nama": nama,
#                     "tanggal": f"{year}-{month}-{col_idx-2}",
#                     "kode_shift": kode_shift
#                 })
#                 continue

#             day = col_idx - 2
#             tanggal = datetime(year, month, day).date()

#             cur.execute("""
#                 INSERT INTO jadwal_karyawan (id_karyawan, nama, tanggal, kode_shift)
#                 VALUES (%s, %s, %s, %s)
#             """, (id_karyawan, nama, tanggal, kode_shift))

#             inserted_count += 1
#             batch_counter += 1

#             if batch_counter >= batch_size:
#                 conn.commit()
#                 batch_counter = 0

#     if batch_counter > 0:
#         conn.commit()

#     cur.close()
#     conn.close()

#     return jsonify({
#         "message": f"Import selesai! {inserted_count} data berhasil disimpan.",
#         "invalid_codes": invalid_codes
#     })



@app.route("/api/import-jadwal-karyawan", methods=["POST"])
def import_jadwal():
    if "file" not in request.files:
        return jsonify({"error": "File tidak ditemukan"}), 400

    file = request.files["file"]

    # Baca Excel
    try:
        df = pd.read_excel(file, header=None)
        print(f"📊 Total baris di Excel: {len(df)}")
        print(f"📊 Total kolom di Excel: {len(df.columns)}")
    except Exception as e:
        return jsonify({"error": f"Gagal membaca file Excel: {str(e)}"}), 500

    # Ambil bulan dan tahun
    try:
        raw_cell = df.iloc[1, 0]
        
        if isinstance(raw_cell, pd.Timestamp):
            year = raw_cell.year
            month = raw_cell.month
            print(f"✓ Detected pandas Timestamp: {year}-{month}")
        else:
            month_year_str = str(raw_cell).strip()
            print(f"Raw month_year_str: {repr(month_year_str)}")
            year, month = parse_month_year(month_year_str)
            
    except Exception as e:
        return jsonify({
            "error": f"Gagal parsing bulan/tahun: {str(e)}",
            "hint": "Format yang didukung: 'November 2025', '11/11/2025', '2025-11-01'"
        }), 400

    days_in_month = monthrange(year, month)[1]
    print(f"📅 Bulan: {month}, Tahun: {year}, Jumlah hari: {days_in_month}")
    
    data = df.iloc[5:, :]
    print(f"📋 Jumlah baris data karyawan: {len(data)}")

    conn = db()
    cur = conn.cursor()

    # Ambil semua kode valid dengan info shift dari shift_info
    cur.execute("""
        SELECT kode, jam_masuk, jam_pulang 
        FROM shift_info
    """)
    shift_info = {}
    valid_kode_shift = set()
    for row in cur.fetchall():
        kode = row[0].strip()
        shift_info[kode] = {
            "jam_masuk": row[1],
            "jam_pulang": row[2]
        }
        valid_kode_shift.add(kode)
    
    # Tambahkan kode dari informasi_jadwal yang mungkin belum ada di shift_info
    cur.execute("SELECT kode FROM informasi_jadwal")
    for row in cur.fetchall():
        valid_kode_shift.add(row[0].strip())
    
    print(f"✅ Kode shift valid: {valid_kode_shift}")

    # Ambil semua id_karyawan dari database
    cur.execute("SELECT id_karyawan, nik, nama FROM karyawan")
    karyawan_rows = cur.fetchall()
    karyawan_dict = {row[1]: {"id": row[0], "nama": row[2]} for row in karyawan_rows}
    print(f"👥 Total karyawan di database: {len(karyawan_dict)}")

    # Hapus jadwal lama bulan ini
    cur.execute("DELETE FROM jadwal_karyawan WHERE YEAR(tanggal)=%s AND MONTH(tanggal)=%s", (year, month))
    deleted_rows = cur.rowcount
    conn.commit()
    print(f"🗑️ Deleted {deleted_rows} jadwal lama")

    inserted_count = 0
    invalid_codes = []
    not_found_employees = []
    batch_size = 5000
    batch_counter = 0

    for idx, row in data.iterrows():
        nik_raw = row[1]
        nik = str(nik_raw).strip() if pd.notna(nik_raw) else ""
        nama_excel = str(row[2]).strip() if pd.notna(row[2]) else ""
        
        if nik:
            # Coba variasi NIK untuk matching
            nik_variations = [
                nik,
                str(int(float(nik))) if nik.replace('.', '').isdigit() else nik,
            ]
            
            found = False
            for nik_variant in nik_variations:
                if nik_variant in karyawan_dict:
                    nik = nik_variant
                    found = True
                    break
            
            if not found:
                not_found_employees.append({
                    "nik": nik,
                    "nama": nama_excel,
                    "error": "Karyawan tidak ditemukan di database"
                })
                continue
        else:
            not_found_employees.append({
                "nik": nik,
                "nama": nama_excel,
                "error": "NIK kosong"
            })
            continue

        id_karyawan = karyawan_dict[nik]["id"]
        nama = karyawan_dict[nik]["nama"]

        for col_idx in range(3, 3 + days_in_month):
            if col_idx >= len(row):
                break

            raw_kode = row[col_idx]
            if pd.isna(raw_kode):
                continue

            kode_shift = str(raw_kode).strip()
            if not kode_shift:
                continue

            day = col_idx - 2

            if kode_shift not in valid_kode_shift:
                invalid_codes.append({
                    "nik": nik,
                    "nama": nama,
                    "tanggal": f"{year}-{month:02d}-{day:02d}",
                    "kode_shift": kode_shift
                })
                continue

            tanggal = datetime(year, month, day).date()

            try:
                cur.execute("""
                    INSERT INTO jadwal_karyawan (id_karyawan, nama, tanggal, kode_shift)
                    VALUES (%s, %s, %s, %s)
                """, (id_karyawan, nama, tanggal, kode_shift))
                
                inserted_count += 1
                batch_counter += 1

                if batch_counter >= batch_size:
                    conn.commit()
                    print(f"💾 Batch commit: {batch_counter} records")
                    batch_counter = 0

            except Exception as e:
                print(f"    ❌ Insert error: {str(e)}")
                continue

    # Final commit untuk sisa data
    if batch_counter > 0:
        conn.commit()
        print(f"💾 Final commit: {batch_counter} records")

    # UPDATE shift_window menggunakan LOGIC EXACT dari query asli
    print("⏳ Menghitung shift window...")
    try:
        cur.execute("""
            UPDATE jadwal_karyawan jk
            JOIN shift_info si 
            ON jk.kode_shift = si.kode
            SET
            jk.shift_window_start =
                CASE
                -- ===============================
                -- SHIFT KHUSUS 3A (PERBAIKAN)
                -- Window: H-1 22:00 s/d H 11:00
                -- ===============================
                WHEN jk.kode_shift = '3A'
                    THEN CONCAT(
                        DATE_SUB(jk.tanggal, INTERVAL 1 DAY),
                        ' 22:00:00'
                    )
                
                -- ===============================
                -- SHIFT LIBUR / CUTI
                -- ===============================
                WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                    THEN NULL

                -- ===============================
                -- LINTAS HARI NORMAL
                -- ===============================
                WHEN si.jam_masuk > si.jam_pulang
                    THEN CONCAT(
                        jk.tanggal,
                        ' ',
                        si.jam_masuk
                        )

                -- ===============================
                -- NON LINTAS HARI
                -- ===============================
                ELSE CONCAT(jk.tanggal, ' ', si.jam_masuk)
                END,

            jk.shift_window_end =
                CASE
                -- ===============================
                -- SHIFT KHUSUS 3A (PERBAIKAN)
                -- ===============================
                WHEN jk.kode_shift = '3A'
                    THEN CONCAT(
                        jk.tanggal,
                        ' 11:00:00'
                    )
                        
                -- ===============================
                -- SHIFT LIBUR / CUTI
                -- ===============================
                WHEN jk.kode_shift IN ('X','CT','CTB','CTT','OF1','EO')
                    THEN NULL

                -- ===============================
                -- LINTAS HARI NORMAL
                -- ===============================
                WHEN si.jam_masuk > si.jam_pulang
                    THEN CONCAT(
                        DATE_ADD(jk.tanggal, INTERVAL 1 DAY),
                        ' ',
                        si.jam_pulang
                        )

                -- ===============================
                -- NON LINTAS HARI
                -- ===============================
                ELSE CONCAT(jk.tanggal, ' ', si.jam_pulang)
                END
            WHERE YEAR(jk.tanggal) = %s
            AND MONTH(jk.tanggal) = %s
        """, (year, month))
        conn.commit()
        print("✅ Shift window berhasil dihitung")
    except Exception as e:
        print(f"❌ Error updating shift window: {str(e)}")

    # Reset hasil croscek
    cur.execute("TRUNCATE TABLE croscek")
    conn.commit()

    cur.close()
    conn.close()

    print(f"\n✅ SUMMARY: {inserted_count} data berhasil disimpan")
    print(f"❌ Karyawan tidak ditemukan: {len(not_found_employees)}")
    print(f"⚠️ Kode shift invalid: {len(invalid_codes)}")

    return jsonify({
        "message": f"Import selesai! {inserted_count} data berhasil disimpan untuk {month}/{year}.",
        "period": f"{month}/{year}",
        "inserted_count": inserted_count,
        "not_found_employees": not_found_employees,
        "invalid_codes": invalid_codes
    })




@app.route("/api/import-kehadiran", methods=["POST"])
def import_kehadiran():
    try:
        if "file" not in request.files:
            return jsonify({"error": "File tidak ditemukan"}), 400

        file = request.files["file"]
        df = pd.read_excel(file, header=1).fillna("")

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
        not_found_name = []   # SIMPAN NAMA YANG GAGAL MATCH

        for _, row in df.iterrows():
            if str(row["Tanggal scan"]).strip() == "" or str(row["Tanggal"]).strip() == "":
                skipped_count += 1
                continue

            # === validasi format tanggal / jam ===
            try:
                tanggal_scan = pd.to_datetime(row["Tanggal scan"], dayfirst=True)
                tanggal_only = pd.to_datetime(row["Tanggal"], dayfirst=True).date()
                jam_only = pd.to_datetime(row["Jam"], dayfirst=True).time()
            except:
                skipped_count += 1
                continue

            verifikasi = int(row["Verifikasi"]) if row["Verifikasi"] != "" else None
            io = int(row["I/O"]) if row["I/O"] != "" else None

            # ==========================================
            # MATCH nama → id_karyawan dari tabel karyawan
            # ==========================================
            cur.execute("""
                SELECT id_karyawan FROM karyawan WHERE nama = %s LIMIT 1
            """, (row["Nama"],))
            data_k = cur.fetchone()

            if not data_k:
                not_found_name.append(row["Nama"])
                skipped_count += 1
                continue

            id_karyawan = data_k["id_karyawan"]

            # ==========================================
            # MATCH shift dari jadwal_karyawan
            # ==========================================
            cur.execute("""
                SELECT kode_shift 
                FROM jadwal_karyawan
                WHERE nama = %s AND tanggal = %s
                LIMIT 1
            """, (row["Nama"], tanggal_only))

            result = cur.fetchone()
            kode_shift = result["kode_shift"] if result else None

            # ==========================================
            # INSERT DATA KEHADIRAN + id_karyawan
            # ==========================================
            cur.execute("""
                INSERT INTO kehadiran_karyawan (
                    id_karyawan, tanggal_scan, tanggal, jam,
                    pin, nip, nama, jabatan, departemen, kantor,
                    verifikasi, io, workcode, sn, mesin, kode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_karyawan, tanggal_scan, tanggal_only, jam_only,
                row["PIN"], row["NIP"], row["Nama"], row["Jabatan"], row["Departemen"], row["Kantor"],
                verifikasi, io, row["Workcode"], row["SN"], row["Mesin"],
                kode_shift
            ))

            inserted_count += 1

        conn.commit()
        cur.close()
        conn.close()

        message = f"{inserted_count} data berhasil disimpan, {skipped_count} dilewati."

        if len(not_found_name) > 0:
            message += f" ❗ Ada nama yang tidak ditemukan: {set(not_found_name)}"

        return jsonify({"message": message})

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
        
        # Query hapus dari kehadiran_karyawan berdasarkan bulan dan tahun
        query_kehadiran = "DELETE FROM kehadiran_karyawan WHERE MONTH(tanggal) = %s AND YEAR(tanggal) = %s"
        cur.execute(query_kehadiran, (bulan, tahun))
        deleted_kehadiran = cur.rowcount
        
        # # Query hapus dari croscek berdasarkan bulan dan tahun
        # query_croscek = "DELETE FROM croscek WHERE MONTH(Tanggal) = %s AND YEAR(Tanggal) = %s"
        # cur.execute(query_croscek, (bulan, tahun))
        # deleted_croscek = cur.rowcount
        # HAPUS TOTAL DATA CROSCEK (FULL REBUILD)
        cur.execute("TRUNCATE TABLE croscek")
        deleted_croscek = -1  # rowcount tidak valid untuk TRUNCATE

        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Berhasil hapus data untuk periode {bulan}/{tahun}",
            "kehadiran_deleted": deleted_kehadiran,
            "croscek_deleted": deleted_croscek,
            "total_deleted": deleted_kehadiran + deleted_croscek
        })
    except Exception as e:
        print("ERROR DELETE PERIOD:", e)
        return jsonify({"error": str(e)}), 500



# ===========================================================
# CROSCEK (QUERY LENGKAP SESUAI PERMINTAAN) - OPTIMIZED
# ===========================================================
@app.route("/api/croscek", methods=["GET", "POST"])
def proses_croscek():
    conn = db()
    cur = conn.cursor(dictionary=True)
    if request.method == "GET":
        try:
            # 🔥 OPTIMIZATION 1: Check if data already exists
            cur.execute("SELECT COUNT(*) as count FROM croscek")
            existing_count = cur.fetchone()["count"]
            
            if existing_count > 0:
                # Data sudah ada, ambil langsung dari tabel croscek (jauh lebih cepat)
                cur.execute("""
                    SELECT
                        Nama,
                        Tanggal,
                        Kode_Shift,
                        Jabatan,
                        Departemen,
                        id_karyawan,
                        NIK,
                        Jadwal_Masuk,
                        Jadwal_Pulang,
                        Actual_Masuk,
                        Actual_Pulang,
                        Prediksi_Shift, Prediksi_Actual_Masuk, Prediksi_Actual_Pulang,
                        Probabilitas_Prediksi, Confidence_Score, Frekuensi_Shift_Historis,
                        Status_Kehadiran,
                        Status_Masuk,
                        Status_Pulang
                    FROM croscek
                    ORDER BY Nama, Tanggal
                """)
                
                result_rows = cur.fetchall()
                
                # Convert TIME/DATE fields to strings for JSON serialization
                for row in result_rows:
                    if row['Jadwal_Masuk'] is not None:
                        row['Jadwal_Masuk'] = str(row['Jadwal_Masuk'])
                    if row['Jadwal_Pulang'] is not None:
                        row['Jadwal_Pulang'] = str(row['Jadwal_Pulang'])
                    if row['Actual_Masuk'] is not None:
                        row['Actual_Masuk'] = str(row['Actual_Masuk'])
                    if row['Actual_Pulang'] is not None:
                        row['Actual_Pulang'] = str(row['Actual_Pulang'])
                    if isinstance(row['Tanggal'], date):
                        row['Tanggal'] = str(row['Tanggal'])
                
                cur.close()
                conn.close()
                
                return jsonify({
                    "data": result_rows,
                    "summary": {
                        "total": len(result_rows),
                        "inserted": 0,
                        "skipped": 0,
                        "from_cache": True
                    }
                })
            
            # Data belum ada, proses dengan query lengkap
            querydefault = """
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
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

                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik,

                    CASE
                        WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
                            THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    END AS Scheduled_Start,
                    
                    # CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) AS Scheduled_Start,

                    CASE
                        WHEN si.lintas_hari = 1
                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    END AS Scheduled_End,


                    /* =====================
                    ACTUAL MASUK (AMAN)
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        ELSE (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            AND k3.tanggal_scan BETWEEN
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
                                END
                            )
                            AND
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR  -- DIUBAH DARI 4 HOUR KE 24 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
                                END
                            )
                        )
                    END AS Actual_Masuk,

                    /* =====================
                    ACTUAL PULANG (FIX UTAMA)
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        ELSE (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            AND k4.tanggal_scan BETWEEN
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                    END
                                )
                                AND
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
                                    END
                                )
                            AND DATE(k4.tanggal_scan) IN (
                                DATE(jk.tanggal),
                                DATE(
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                    END
                                )
                            )
                            AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR  -- FILTER BARU: SCAN PULANG HARUS SETELAH MASUK +1 JAM
                            AND k4.tanggal_scan >=
                            (
                                CASE
                                    WHEN si.lintas_hari = 1
                                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                END
                            )
                        )
                    END AS Actual_Pulang


                FROM jadwal_karyawan jk
                LEFT JOIN shift_info si ON jk.kode_shift = si.kode
                LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

                GROUP BY
                    jk.nama, jk.tanggal, jk.kode_shift,
                    si.jam_masuk, si.jam_pulang,
                    k.jabatan, k.dept, k.id_karyawan, k.nik

            ) AS base

            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            ORDER BY base.Nama, base.Tanggal;
            """
            
            querysolving_3a_ditanggal_1_tapi_masih_curi_state_actual = """
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
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

                -- ===== STATUS PULANG (FIXED) =====
                CASE
                    WHEN base.Actual_Pulang IS NULL 
                        THEN 'Tidak scan pulang'
                    -- Pulang terlalu cepat (lebih dari 15 menit sebelum jadwal)
                    WHEN base.Actual_Pulang < DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
                        THEN 'Pulang Terlalu Cepat'
                    -- Pulang tepat waktu (dalam rentang -15 menit s/d +15 menit dari jadwal)
                    WHEN base.Actual_Pulang BETWEEN 
                            DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE) 
                            AND DATE_ADD(base.Scheduled_End, INTERVAL 15 MINUTE)
                        THEN 'Pulang Tepat Waktu'
                    -- Pulang telat (lebih dari 15 menit setelah jadwal)
                    ELSE 'Pulang Tepat Waktu'
                END AS Status_Pulang

            FROM (

                SELECT
                    jk.nama AS Nama,
                    jk.tanggal AS Tanggal,
                    jk.kode_shift AS Kode_Shift,
                    si.jam_masuk AS Jadwal_Masuk,
                    si.jam_pulang AS Jadwal_Pulang,

                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik,

                    CASE
                        WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
                            THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    END AS Scheduled_Start,

                    CASE
                        WHEN si.lintas_hari = 1
                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    END AS Scheduled_End,


                    /* =====================
                    ACTUAL MASUK - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift IN ('3','3A') AND si.lintas_hari = 1 THEN (
                            SELECT MIN(k.tanggal_scan)
                            FROM kehadiran_karyawan k
                            WHERE k.nama = jk.nama
                            AND k.tanggal_scan BETWEEN
                                    CAST(CONCAT(jk.tanggal, ' 23:00:00') AS DATETIME)
                                AND CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 03:00:00') AS DATETIME)
                        )

                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            AND k3.tanggal_scan BETWEEN
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
                                END
                            )
                            AND
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
                                END
                            )
                        )
                    END AS Actual_Masuk,

                    /* =====================
                    ACTUAL PULANG - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift IN ('3','3A') AND si.lintas_hari = 1 THEN (
                            SELECT MAX(k.tanggal_scan)
                            FROM kehadiran_karyawan k
                            WHERE k.nama = jk.nama
                            AND k.tanggal_scan BETWEEN
                                    CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 03:00:00') AS DATETIME)
                                AND CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 12:00:00') AS DATETIME)
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            AND k4.tanggal_scan BETWEEN
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                    END
                                )
                                AND
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
                                    END
                                )
                            AND DATE(k4.tanggal_scan) IN (
                                DATE(jk.tanggal),
                                DATE(
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                    END
                                )
                            )
                            AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR
                            AND k4.tanggal_scan >=
                            (
                                CASE
                                    WHEN si.lintas_hari = 1
                                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                END
                            )
                        )
                    END AS Actual_Pulang


                FROM jadwal_karyawan jk
                LEFT JOIN shift_info si ON jk.kode_shift = si.kode
                LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

                GROUP BY
                    jk.nama, jk.tanggal, jk.kode_shift,
                    si.jam_masuk, si.jam_pulang,
                    k.jabatan, k.dept, k.id_karyawan, k.nik

            ) AS base

            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            ORDER BY base.Nama, base.Tanggal;
            """



            query = """
            /* ===============================================
            🚀 OPTIMIZED QUERY - DURATION-BASED STATUS
            =============================================== */

            WITH 
            used_scan_pulang_malam AS (
            -- Part 1: Shift lintas hari normal (non-ACCOUNTING/SALES)
            SELECT DISTINCT
                kk.nama,
                kk.tanggal_scan
            FROM jadwal_karyawan jk
            JOIN informasi_jadwal ij
                ON ij.kode = jk.kode_shift
            JOIN kehadiran_karyawan kk
                ON kk.nama = jk.nama
            JOIN karyawan k
                ON k.id_karyawan = jk.id_karyawan
            WHERE
                k.dept NOT IN ('ACCOUNTING', 'SALES & MARKETING')
                AND ij.jam_pulang < ij.jam_masuk
                AND DATE(kk.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                AND kk.tanggal_scan BETWEEN
                    CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang) - INTERVAL 4 HOUR
                    AND CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang) + INTERVAL 6 HOUR
            
            UNION
            
            -- Part 2: ACCOUNTING & SALES - Shift lintas hari (2A jam 16:00-00:00)
            SELECT DISTINCT
                kk.nama,
                kk.tanggal_scan
            FROM jadwal_karyawan jk
            JOIN informasi_jadwal ij
                ON ij.kode = jk.kode_shift
            JOIN kehadiran_karyawan kk
                ON kk.nama = jk.nama
            JOIN karyawan k
                ON k.id_karyawan = jk.id_karyawan
            WHERE
                k.dept IN ('ACCOUNTING', 'SALES & MARKETING')
                AND ij.jam_pulang < ij.jam_masuk  -- Shift lintas hari seperti 2A
                AND DATE(kk.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                AND kk.tanggal_scan BETWEEN
                    CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang) - INTERVAL 4 HOUR
                    AND CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang) + INTERVAL 6 HOUR  -- ✅ DIKURANGI dari +12 ke +6 jam
            
            UNION
            
            -- Part 3: ACCOUNTING & SALES - Shift NORMAL tapi pulang LEWAT TENGAH MALAM
            -- Hanya untuk scan yang BENAR-BENAR pulang malam (00:00-05:59), BUKAN scan masuk pagi
            SELECT DISTINCT
                kk.nama,
                kk.tanggal_scan
            FROM jadwal_karyawan jk
            JOIN informasi_jadwal ij
                ON ij.kode = jk.kode_shift
            JOIN kehadiran_karyawan kk
                ON kk.nama = jk.nama
            JOIN karyawan k
                ON k.id_karyawan = jk.id_karyawan
            WHERE
                k.dept IN ('ACCOUNTING', 'SALES & MARKETING')
                AND ij.jam_pulang >= ij.jam_masuk  -- ✅ Shift NORMAL (1A: 08:00-16:00)
                AND DATE(kk.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)  -- ✅ Scan di H+1
                AND TIME(kk.tanggal_scan) BETWEEN '00:00:00' AND '05:59:59'  -- ✅ HANYA dini hari 00:00-05:59
                
                -- ✅ Scan harus dekat dengan jam pulang yang diharapkan (maksimal 6 jam setelah jam pulang)
                AND TIMESTAMPDIFF(
                    HOUR,
                    CONCAT(jk.tanggal, ' ', ij.jam_pulang),
                    kk.tanggal_scan
                ) BETWEEN -4 AND 6
                
                -- ✅ VALIDASI: Harus ada scan masuk di hari H
                AND EXISTS (
                    SELECT 1
                    FROM kehadiran_karyawan kk_in
                    WHERE kk_in.nama = jk.nama
                    AND DATE(kk_in.tanggal_scan) = jk.tanggal
                    AND kk_in.tanggal_scan BETWEEN
                        CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                        AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                )
                
                -- ✅ VALIDASI KRITIS: TIDAK ADA shift pagi di hari H+1
                -- Jika ada shift pagi (jam masuk < 10:00) di H+1, maka scan pagi bukan pulang malam!
                AND NOT EXISTS (
                    SELECT 1
                    FROM jadwal_karyawan jk_next
                    JOIN informasi_jadwal ij_next ON ij_next.kode = jk_next.kode_shift
                    WHERE jk_next.nama = jk.nama
                    AND jk_next.id_karyawan = jk.id_karyawan
                    AND jk_next.tanggal = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                    AND jk_next.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                    AND ij_next.jam_masuk < '10:00:00'  -- Ada shift pagi/siang di H+1
                )
        ),


            /* CTE 1: Scan Data per Karyawan per Tanggal */
            scan_data AS (
                SELECT
                    k.nama,
                    DATE(k.tanggal_scan) AS tanggal,
                    MIN(k.tanggal_scan) AS scan_masuk,
                    MAX(k.tanggal_scan) AS scan_pulang
                FROM kehadiran_karyawan k
                LEFT JOIN used_scan_pulang_malam u
                    ON u.nama = k.nama
                    AND u.tanggal_scan = k.tanggal_scan
                WHERE u.tanggal_scan IS NULL
                GROUP BY k.nama, DATE(k.tanggal_scan)
            ),


            /* CTE 2: Historical Frequency per Shift */
            historical_freq AS (
                SELECT 
                    jk.nama,
                    jk.kode_shift,
                    COUNT(*) AS freq_count
                FROM jadwal_karyawan jk
                WHERE jk.tanggal >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                GROUP BY jk.nama, jk.kode_shift
            ),

            /* CTE 3: Base Data dengan Actual Masuk/Pulang + DURATION VALIDATION */
            base_data AS (
                SELECT
                    jk.nama AS Nama,
                    jk.tanggal AS Tanggal,
                    jk.kode_shift AS Kode_Shift,
                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik AS NIK,
                    ij.jam_masuk,
                    ij.jam_pulang,
                    
                    /* Hitung durasi shift yang diharapkan (dalam menit) */
                    CASE
                        WHEN ij.jam_pulang < ij.jam_masuk THEN
                            TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ADDTIME(ij.jam_pulang, '24:00:00'))
                        ELSE
                            TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ij.jam_pulang)
                    END AS expected_duration_minutes,
                    
                    /* ===== ACTUAL MASUK - FIXED UNTUK 3A ===== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- FIXED: Shift 3A - Masuk H jam 22:00 sampai H+1 jam 03:00
                        WHEN jk.kode_shift = '3A' THEN (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            WHERE kk.nama = jk.nama
                            AND (
                                (
                                    DATE(kk.tanggal_scan) = jk.tanggal
                                    AND TIME(kk.tanggal_scan) >= '22:00:00'
                                )
                                OR
                                (
                                    DATE(kk.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                                    AND TIME(kk.tanggal_scan) <= '03:00:00'
                                )
                            )
                        )
                        
                        WHEN ij.jam_pulang < ij.jam_masuk THEN (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            LEFT JOIN used_scan_pulang_malam u
                                ON u.nama = kk.nama
                                AND u.tanggal_scan = kk.tanggal_scan
                            WHERE kk.nama = jk.nama
                            AND u.tanggal_scan IS NULL
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                        )
                        ELSE (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            LEFT JOIN used_scan_pulang_malam u
                                ON u.nama = kk.nama
                                AND u.tanggal_scan = kk.tanggal_scan
                            WHERE kk.nama = jk.nama
                            AND u.tanggal_scan IS NULL
                            -- ✅ PERBAIKAN: Pastikan scan di hari yang sama (H)
                            AND DATE(kk.tanggal_scan) = jk.tanggal
                            -- ✅ PERBAIKAN: Window lebih luas untuk ACCOUNTING/SALES (dari jam 02:00 pagi sampai +4 jam setelah jam masuk)
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(jk.tanggal, ' 02:00:00')  -- Mulai dari jam 2 pagi
                                AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                            -- ✅ VALIDASI: Scan tidak boleh terlalu dekat dengan jam pulang shift sebelumnya
                            AND NOT EXISTS (
                                SELECT 1
                                FROM jadwal_karyawan jk_prev
                                JOIN informasi_jadwal ij_prev ON ij_prev.kode = jk_prev.kode_shift
                                WHERE jk_prev.nama = jk.nama
                                AND jk_prev.tanggal = DATE_SUB(jk.tanggal, INTERVAL 1 DAY)
                                AND jk_prev.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                -- Jangan ambil scan yang terlalu dekat dengan jam pulang shift kemarin
                                AND ij_prev.jam_pulang < ij_prev.jam_masuk  -- Shift lintas hari
                                AND kk.tanggal_scan BETWEEN
                                    CONCAT(jk.tanggal, ' ', ij_prev.jam_pulang) - INTERVAL 2 HOUR
                                    AND CONCAT(jk.tanggal, ' ', ij_prev.jam_pulang) + INTERVAL 2 HOUR
                            )
                        )
                    END AS Actual_Masuk,
                    
                    /* ===== ACTUAL PULANG - FIXED DENGAN DURATION VALIDATION ===== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- FIXED: Shift 3A
                        WHEN jk.kode_shift = '3A' THEN (
                            SELECT kk_out.tanggal_scan
                            FROM kehadiran_karyawan kk_out
                            WHERE kk_out.nama = jk.nama
                            AND DATE(kk_out.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                            AND TIME(kk_out.tanggal_scan) >= '06:00:00'
                            AND TIME(kk_out.tanggal_scan) <= '11:00:00'
                            AND kk_out.tanggal_scan != COALESCE((
                                SELECT MIN(kk_in.tanggal_scan)
                                FROM kehadiran_karyawan kk_in
                                WHERE kk_in.nama = jk.nama
                                AND (
                                    (DATE(kk_in.tanggal_scan) = jk.tanggal
                                    AND TIME(kk_in.tanggal_scan) >= '22:00:00')
                                    OR
                                    (DATE(kk_in.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                                    AND TIME(kk_in.tanggal_scan) <= '03:00:00')
                                )
                            ), '1900-01-01')
                            -- VALIDASI DURASI: minimal 50% dari durasi shift
                            AND TIMESTAMPDIFF(MINUTE, 
                                COALESCE((
                                    SELECT MIN(kk_in.tanggal_scan)
                                    FROM kehadiran_karyawan kk_in
                                    WHERE kk_in.nama = jk.nama
                                    AND (
                                        (DATE(kk_in.tanggal_scan) = jk.tanggal
                                        AND TIME(kk_in.tanggal_scan) >= '22:00:00')
                                        OR
                                        (DATE(kk_in.tanggal_scan) = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                                        AND TIME(kk_in.tanggal_scan) <= '03:00:00')
                                    )
                                ), kk_out.tanggal_scan),
                                kk_out.tanggal_scan
                            ) >= (
                                CASE
                                    WHEN ij.jam_pulang < ij.jam_masuk THEN
                                        TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ADDTIME(ij.jam_pulang, '24:00:00'))
                                    ELSE
                                        TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ij.jam_pulang)
                                END * 0.5
                            )
                            ORDER BY kk_out.tanggal_scan DESC
                            LIMIT 1
                        )
                        
                        -- FIXED: Departemen ACCOUNTING & SALES & MARKETING - Extended Window
                        WHEN k.dept IN ('ACCOUNTING', 'SALES & MARKETING') THEN (
                            CASE
                                -- Untuk shift yang melewati tengah malam
                                WHEN ij.jam_pulang < ij.jam_masuk THEN (
                                    SELECT kk_out.tanggal_scan
                                    FROM kehadiran_karyawan kk_out
                                    WHERE kk_out.nama = jk.nama
                                    AND kk_out.tanggal_scan BETWEEN 
                                        CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY - INTERVAL 4 HOUR
                                        AND CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY + INTERVAL 12 HOUR
                                    AND kk_out.tanggal_scan != COALESCE((
                                        SELECT MIN(tanggal_scan) FROM kehadiran_karyawan 
                                        WHERE nama = jk.nama 
                                        AND tanggal_scan BETWEEN CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                            AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                    ), '1900-01-01')
                                    -- VALIDASI DURASI: minimal 50% dari durasi shift DAN maksimal 150%
                                    AND (
                                        (
                                            SELECT MIN(kk_in.tanggal_scan)
                                            FROM kehadiran_karyawan kk_in
                                            WHERE kk_in.nama = jk.nama
                                            AND kk_in.tanggal_scan BETWEEN
                                                CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                                AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                        ) IS NULL
                                        OR TIMESTAMPDIFF(
                                            MINUTE,
                                            (
                                                SELECT MIN(kk_in.tanggal_scan)
                                                FROM kehadiran_karyawan kk_in
                                                WHERE kk_in.nama = jk.nama
                                                AND kk_in.tanggal_scan BETWEEN
                                                    CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                                    AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                            ),
                                            kk_out.tanggal_scan
                                            ) >= (TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ADDTIME(ij.jam_pulang,'24:00:00')) * 0.5)

                                    )

                                    ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk_out.tanggal_scan, 
                                        CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY))
                                    LIMIT 1
                                )
                                -- Untuk shift normal
                                ELSE (
                                    SELECT kk_out.tanggal_scan
                                    FROM kehadiran_karyawan kk_out
                                    WHERE kk_out.nama = jk.nama
                                    AND kk_out.tanggal_scan BETWEEN 
                                        CONCAT(jk.tanggal, ' ', ij.jam_pulang) - INTERVAL 4 HOUR
                                        AND CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 12 HOUR
                                    AND kk_out.tanggal_scan != COALESCE((
                                        SELECT MIN(tanggal_scan) FROM kehadiran_karyawan 
                                        WHERE nama = jk.nama 
                                        AND tanggal_scan BETWEEN CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                            AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                    ), '1900-01-01')
                                    
                                    -- VALIDASI DURASI: minimal 50% dari durasi shift
                                    AND (
                                        (
                                            SELECT MIN(kk_in.tanggal_scan)
                                            FROM kehadiran_karyawan kk_in
                                            WHERE kk_in.nama = jk.nama
                                            AND kk_in.tanggal_scan BETWEEN
                                                CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                                AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                        ) IS NULL
                                        OR TIMESTAMPDIFF(
                                            MINUTE,
                                            (
                                                SELECT MIN(kk_in.tanggal_scan)
                                                FROM kehadiran_karyawan kk_in
                                                WHERE kk_in.nama = jk.nama
                                                AND kk_in.tanggal_scan BETWEEN
                                                    CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                                    AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                            ),
                                            kk_out.tanggal_scan
                                        ) >= (TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ij.jam_pulang) * 0.5)
                                    )
                                    
                                    -- ✅ VALIDASI TAMBAHAN: Jangan ambil scan jika terlalu dekat dengan jam masuk shift berikutnya
                                    AND NOT EXISTS (
                                        SELECT 1
                                        FROM jadwal_karyawan jk_next
                                        JOIN informasi_jadwal ij_next ON ij_next.kode = jk_next.kode_shift
                                        WHERE jk_next.nama = jk.nama
                                        AND jk_next.id_karyawan = jk.id_karyawan
                                        AND jk_next.tanggal = DATE_ADD(jk.tanggal, INTERVAL 1 DAY)
                                        AND jk_next.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                        -- Scan dalam 2 jam sebelum sampai 4 jam setelah jam masuk shift berikutnya
                                        AND kk_out.tanggal_scan BETWEEN
                                            CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij_next.jam_masuk) - INTERVAL 2 HOUR
                                            AND CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', ij_next.jam_masuk) + INTERVAL 4 HOUR
                                    )

                                    ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk_out.tanggal_scan, 
                                        CONCAT(jk.tanggal, ' ', ij.jam_pulang)))
                                    LIMIT 1
                                )
                            END
                        )
                        
                        -- Logika standar untuk departemen lain
                        WHEN ij.jam_pulang < ij.jam_masuk THEN (
                            SELECT kk_out.tanggal_scan
                            FROM kehadiran_karyawan kk_out
                            WHERE kk_out.nama = jk.nama
                            AND kk_out.tanggal_scan BETWEEN 
                                CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY - INTERVAL 4 HOUR
                                AND CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY + INTERVAL 6 HOUR
                            AND kk_out.tanggal_scan != COALESCE((
                                SELECT MIN(tanggal_scan) FROM kehadiran_karyawan 
                                WHERE nama = jk.nama 
                                AND tanggal_scan BETWEEN CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                    AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                            ), '1900-01-01')
                            -- VALIDASI DURASI: minimal 50% DAN maksimal 150% dari durasi shift
                            AND (
                                (
                                    SELECT MIN(kk_in.tanggal_scan)
                                    FROM kehadiran_karyawan kk_in
                                    WHERE kk_in.nama = jk.nama
                                    AND kk_in.tanggal_scan BETWEEN
                                        CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                        AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                ) IS NULL
                                OR TIMESTAMPDIFF(
                                    MINUTE,
                                    (
                                        SELECT MIN(kk_in.tanggal_scan)
                                        FROM kehadiran_karyawan kk_in
                                        WHERE kk_in.nama = jk.nama
                                        AND kk_in.tanggal_scan BETWEEN
                                            CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                            AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                    ),
                                    kk_out.tanggal_scan
                                ) >= (TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ADDTIME(ij.jam_pulang,'24:00:00')) * 0.5)

                            )

                            ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk_out.tanggal_scan, 
                                CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 1 DAY))
                            LIMIT 1
                        )
                        ELSE (
                            SELECT kk_out.tanggal_scan
                            FROM kehadiran_karyawan kk_out
                            WHERE kk_out.nama = jk.nama
                            AND kk_out.tanggal_scan BETWEEN 
                                CONCAT(jk.tanggal, ' ', ij.jam_pulang) - INTERVAL 4 HOUR
                                AND CONCAT(jk.tanggal, ' ', ij.jam_pulang) + INTERVAL 6 HOUR
                            AND kk_out.tanggal_scan != COALESCE((
                                SELECT MIN(tanggal_scan) FROM kehadiran_karyawan 
                                WHERE nama = jk.nama 
                                AND tanggal_scan BETWEEN CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                    AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                            ), '1900-01-01')
                            -- VALIDASI DURASI: minimal 50% DAN maksimal 150% dari durasi shift
                            AND (
                                (
                                    SELECT MIN(kk_in.tanggal_scan)
                                    FROM kehadiran_karyawan kk_in
                                    WHERE kk_in.nama = jk.nama
                                    AND kk_in.tanggal_scan BETWEEN
                                        CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                        AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                ) IS NULL
                                OR TIMESTAMPDIFF(
                                    MINUTE,
                                    (
                                        SELECT MIN(kk_in.tanggal_scan)
                                        FROM kehadiran_karyawan kk_in
                                        WHERE kk_in.nama = jk.nama
                                        AND kk_in.tanggal_scan BETWEEN
                                            CONCAT(jk.tanggal, ' ', ij.jam_masuk) - INTERVAL 6 HOUR
                                            AND CONCAT(jk.tanggal, ' ', ij.jam_masuk) + INTERVAL 4 HOUR
                                    ),
                                    kk_out.tanggal_scan
                                ) >= (TIMESTAMPDIFF(MINUTE, ij.jam_masuk, ij.jam_pulang) * 0.5)

                            )

                            ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk_out.tanggal_scan, 
                                CONCAT(jk.tanggal, ' ', ij.jam_pulang)))
                            LIMIT 1
                        )
                    END AS Actual_Pulang
                    
                FROM jadwal_karyawan jk
                LEFT JOIN karyawan k ON k.id_karyawan = jk.id_karyawan
                LEFT JOIN informasi_jadwal ij ON ij.kode = jk.kode_shift
            ),

            /* CTE 4: Add Actual Duration Calculation */
            base_with_duration AS (
                SELECT
                    base.*,
                    CASE
                        WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL
                        THEN TIMESTAMPDIFF(MINUTE, base.Actual_Masuk, base.Actual_Pulang)
                        ELSE NULL
                    END AS actual_duration_minutes
                FROM base_data base
            ),

            /* CTE 5: Prediksi Shift */
            prediction_data AS (
                SELECT
                    s.nama,
                    s.tanggal,
                    ij2.kode AS kode_shift,
                    
                    /* Prediksi Actual Masuk */
                    CASE
                        WHEN ij2.kode = '3A' THEN (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            WHERE kk.nama = s.nama
                            AND (
                                (
                                    DATE(kk.tanggal_scan) = s.tanggal
                                    AND TIME(kk.tanggal_scan) >= '22:00:00'
                                )
                                OR
                                (
                                    DATE(kk.tanggal_scan) = DATE_ADD(s.tanggal, INTERVAL 1 DAY)
                                    AND TIME(kk.tanggal_scan) <= '03:00:00'
                                )
                            )
                        )
                        
                        WHEN ij2.jam_pulang < ij2.jam_masuk THEN (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            LEFT JOIN used_scan_pulang_malam u
                                ON u.nama = kk.nama
                                AND u.tanggal_scan = kk.tanggal_scan
                            WHERE kk.nama = s.nama
                            AND u.tanggal_scan IS NULL  -- 🔑 EXCLUDE scan pulang malam
                            AND DATE(kk.tanggal_scan) BETWEEN DATE_SUB(s.tanggal, INTERVAL 1 DAY) AND s.tanggal
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(s.tanggal, ' ', ij2.jam_masuk) - INTERVAL 6 HOUR
                                AND CONCAT(s.tanggal, ' ', ij2.jam_masuk) + INTERVAL 4 HOUR
                        )
                        ELSE (
                            SELECT MIN(kk.tanggal_scan)
                            FROM kehadiran_karyawan kk
                            LEFT JOIN used_scan_pulang_malam u
                                ON u.nama = kk.nama
                                AND u.tanggal_scan = kk.tanggal_scan
                            WHERE kk.nama = s.nama
                            AND u.tanggal_scan IS NULL  -- 🔑 EXCLUDE scan pulang malam
                            AND DATE(kk.tanggal_scan) = s.tanggal
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(s.tanggal, ' ', ij2.jam_masuk) - INTERVAL 6 HOUR
                                AND CONCAT(s.tanggal, ' ', ij2.jam_masuk) + INTERVAL 4 HOUR
                        )
                    END AS pred_actual_masuk,
                    
                    /* Prediksi Actual Pulang - dengan validasi durasi */
                    CASE
                        WHEN ij2.kode = '3A' THEN (
                            SELECT kk.tanggal_scan
                            FROM kehadiran_karyawan kk
                            WHERE kk.nama = s.nama
                            AND DATE(kk.tanggal_scan) = DATE_ADD(s.tanggal, INTERVAL 1 DAY)
                            AND TIME(kk.tanggal_scan) >= '06:00:00'
                            AND TIME(kk.tanggal_scan) <= '11:00:00'
                            AND kk.tanggal_scan != s.scan_masuk
                            AND TIMESTAMPDIFF(MINUTE, s.scan_masuk, kk.tanggal_scan) BETWEEN (
                                CASE
                                    WHEN ij2.jam_pulang < ij2.jam_masuk THEN
                                        TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ADDTIME(ij2.jam_pulang, '24:00:00'))
                                    ELSE
                                        TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ij2.jam_pulang)
                                END * 0.5
                            ) AND (
                                CASE
                                    WHEN ij2.jam_pulang < ij2.jam_masuk THEN
                                        TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ADDTIME(ij2.jam_pulang, '24:00:00'))
                                    ELSE
                                        TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ij2.jam_pulang)
                                END * 1.5
                            )
                            ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk.tanggal_scan, 
                                CONCAT(s.tanggal, ' 06:00:00') + INTERVAL 1 DAY))
                            LIMIT 1
                        )
                        
                        -- 🔑 UNTUK SHIFT LINTAS HARI (termasuk ACCOUNTING & SALES & MARKETING)
                        WHEN ij2.jam_pulang < ij2.jam_masuk THEN (
                            SELECT kk.tanggal_scan
                            FROM kehadiran_karyawan kk
                            WHERE kk.nama = s.nama
                            AND DATE(kk.tanggal_scan) BETWEEN s.tanggal AND DATE_ADD(s.tanggal, INTERVAL 1 DAY)
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(s.tanggal, ' ', ij2.jam_pulang) + INTERVAL 1 DAY - INTERVAL 4 HOUR
                                AND CONCAT(s.tanggal, ' ', ij2.jam_pulang) + INTERVAL 1 DAY + INTERVAL 12 HOUR
                            AND kk.tanggal_scan != s.scan_masuk
                            AND TIMESTAMPDIFF(MINUTE, s.scan_masuk, kk.tanggal_scan) BETWEEN (
                                TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ADDTIME(ij2.jam_pulang, '24:00:00')) * 0.5
                            ) AND (
                                TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ADDTIME(ij2.jam_pulang, '24:00:00')) * 1.5
                            )
                            ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk.tanggal_scan, 
                                CONCAT(s.tanggal, ' ', ij2.jam_pulang) + INTERVAL 1 DAY))
                            LIMIT 1
                        )
                        ELSE (
                            SELECT kk.tanggal_scan
                            FROM kehadiran_karyawan kk
                            WHERE kk.nama = s.nama
                            AND DATE(kk.tanggal_scan) = s.tanggal
                            AND kk.tanggal_scan BETWEEN 
                                CONCAT(s.tanggal, ' ', ij2.jam_pulang) - INTERVAL 4 HOUR
                                AND CONCAT(s.tanggal, ' ', ij2.jam_pulang) + INTERVAL 12 HOUR
                            AND kk.tanggal_scan != s.scan_masuk
                            AND TIMESTAMPDIFF(MINUTE, s.scan_masuk, kk.tanggal_scan) BETWEEN (
                                TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ij2.jam_pulang) * 0.5
                            ) AND (
                                TIMESTAMPDIFF(MINUTE, ij2.jam_masuk, ij2.jam_pulang) * 1.5
                            )
                            ORDER BY ABS(TIMESTAMPDIFF(MINUTE, kk.tanggal_scan, 
                                CONCAT(s.tanggal, ' ', ij2.jam_pulang)))
                            LIMIT 1
                        )
                    END AS pred_actual_pulang,
                    
                    (
                        0.7 * CASE 
                            WHEN s.scan_masuk IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk))
                            ELSE 999 
                        END +
                        0.3 * CASE 
                            WHEN s.scan_pulang IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang))
                            ELSE 999 
                        END
                    ) - COALESCE(hf.freq_count * 5, 0) AS final_score,
                    
                    CASE 
                        WHEN s.scan_masuk IS NOT NULL AND s.scan_pulang IS NOT NULL
                        THEN ROUND(100 * (1 - ((
                            0.7 * ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) +
                            0.3 * ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang))
                        ) / 180)), 2)
                        WHEN s.scan_masuk IS NOT NULL 
                        THEN ROUND(50 * (1 - (ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) / 90)), 2)
                        WHEN s.scan_pulang IS NOT NULL 
                        THEN ROUND(50 * (1 - (ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang)) / 90)), 2)
                        ELSE 0
                    END AS probabilitas,
                    
                    CASE 
                        WHEN (0.7 * CASE WHEN s.scan_masuk IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) ELSE 999 END +
                            0.3 * CASE WHEN s.scan_pulang IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang)) ELSE 999 END
                        ) <= 45 THEN 'Sangat Tinggi'
                        WHEN (0.7 * CASE WHEN s.scan_masuk IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) ELSE 999 END +
                            0.3 * CASE WHEN s.scan_pulang IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang)) ELSE 999 END
                        ) <= 90 THEN 'Tinggi'
                        WHEN (0.7 * CASE WHEN s.scan_masuk IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) ELSE 999 END +
                            0.3 * CASE WHEN s.scan_pulang IS NOT NULL 
                            THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang)) ELSE 999 END
                        ) <= 180 THEN 'Sedang'
                        ELSE 'Rendah'
                    END AS confidence_score,
                    
                    COALESCE(hf.freq_count, 0) AS freq_shift,
                    
                    ROW_NUMBER() OVER (
                        PARTITION BY s.nama, s.tanggal
                        ORDER BY (
                            0.7 * CASE WHEN s.scan_masuk IS NOT NULL 
                                THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_masuk), ij2.jam_masuk)) ELSE 999 END +
                            0.3 * CASE WHEN s.scan_pulang IS NOT NULL 
                                THEN ABS(TIMESTAMPDIFF(MINUTE, TIME(s.scan_pulang), ij2.jam_pulang)) ELSE 999 END
                        ) - COALESCE(hf.freq_count * 5, 0) ASC
                    ) AS rn
                    
                FROM scan_data s
                CROSS JOIN informasi_jadwal ij2
                LEFT JOIN karyawan k ON k.nama = s.nama  -- 🔑 TAMBAHKAN INI
                LEFT JOIN historical_freq hf ON hf.nama = s.nama AND hf.kode_shift = ij2.kode
                WHERE ij2.kode NOT IN ('CT','CTT','EO','OF1','CTB','X')
                AND ij2.lokasi_kerja = 'Ciater'
            )

            /* ===== MAIN SELECT ===== */
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
                ij.jam_masuk AS Jadwal_Masuk,
                ij.jam_pulang AS Jadwal_Pulang,
                base.Actual_Masuk,
                base.Actual_Pulang,
                
                /* Durasi Kerja */
                base.expected_duration_minutes AS Durasi_Shift_Diharapkan_Menit,
                base.actual_duration_minutes AS Durasi_Kerja_Aktual_Menit,
                CASE 
                    WHEN base.actual_duration_minutes IS NOT NULL THEN
                        CONCAT(
                            FLOOR(base.actual_duration_minutes / 60), ' jam ',
                            MOD(base.actual_duration_minutes, 60), ' menit'
                        )
                    ELSE NULL
                END AS Durasi_Kerja_Aktual,
                
                /* Prediksi */
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.kode_shift 
                END AS Prediksi_Shift,
                
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.pred_actual_masuk 
                END AS Prediksi_Actual_Masuk,
                
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.pred_actual_pulang 
                END AS Prediksi_Actual_Pulang,
                
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.probabilitas 
                END AS Probabilitas_Prediksi,
                
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.confidence_score 
                END AS Confidence_Score,
                
                CASE 
                    WHEN base.Actual_Masuk IS NOT NULL AND base.Actual_Pulang IS NOT NULL 
                    THEN NULL ELSE pred.freq_shift 
                END AS Frekuensi_Shift_Historis,
                
                /* ===== STATUS KEHADIRAN ===== */
                CASE
                    WHEN base.Kode_Shift IN ('CT','CTT','EO','OF1','CTB','X') THEN ij.keterangan
                    WHEN base.Actual_Masuk IS NULL AND base.Actual_Pulang IS NULL THEN 'Tidak Hadir'
                    ELSE 'Hadir'
                END AS Status_Kehadiran,
                
                /* ===== STATUS MASUK - DURATION-BASED LOGIC ===== */
            CASE
                -- 🔥 FIX 1: Jika masuk NULL tapi durasi kerja valid → MASUK TEPAT WAKTU
                WHEN base.Actual_Masuk IS NULL
                    AND base.actual_duration_minutes IS NOT NULL
                    AND base.actual_duration_minutes >= (base.expected_duration_minutes * 0.9)
                    THEN 'Masuk Tepat Waktu'
                
                WHEN base.Actual_Masuk IS NULL THEN 'Tidak scan masuk'
                
                -- ✅ PRIORITAS 1: Untuk departemen NON-ACCOUNTING/SALES: Jika durasi kerja >= 90% = TEPAT WAKTU
                # WHEN base.Departemen NOT IN ('ACCOUNTING', 'SALES & MARKETING')
                #     AND base.actual_duration_minutes >= (base.expected_duration_minutes * 0.9)
                #     THEN 'Masuk Tepat Waktu'
                
                -- 🔒 FIX: NON-ACCOUNTING/SALES TIDAK BOLEH KOMPENSASI DURASI
                WHEN base.Departemen NOT IN ('ACCOUNTING', 'SALES & MARKETING')
                    AND base.Actual_Masuk IS NOT NULL
                    AND TIME(base.Actual_Masuk) <= ADDTIME(ij.jam_masuk, '00:15:00')
                    THEN 'Masuk Tepat Waktu'

                
                -- 🆕 PRIORITAS 2A: LOGIKA KHUSUS SHIFT 3A - ACCOUNTING & SALES & MARKETING
                WHEN base.Departemen IN ('ACCOUNTING', 'SALES & MARKETING')
                    AND base.Kode_Shift = '3A'
                    AND base.Actual_Masuk IS NOT NULL
                    AND base.Actual_Pulang IS NOT NULL
                    THEN
                    CASE
                        -- Jika masuk di H malam (22:00-23:59) = TEPAT WAKTU (tidak perlu kompensasi)
                        WHEN DATE(base.Actual_Masuk) = DATE(base.Tanggal)
                            AND TIME(base.Actual_Masuk) >= '22:00:00'
                            AND TIME(base.Actual_Masuk) <= '23:59:59'
                            THEN 'Masuk Tepat Waktu'
                        
                        -- Jika masuk di H+1 dini hari, CEK KOMPENSASI
                        WHEN DATE(base.Actual_Masuk) = DATE_ADD(DATE(base.Tanggal), INTERVAL 1 DAY)
                            AND (
                                -- Kompensasi 1: Durasi minimal 9 jam penuh
                                base.actual_duration_minutes >= 540
                                OR 
                                -- Kompensasi 2: Pulang minimal 1 jam setelah jadwal (jam 09:00+)
                                TIMESTAMPDIFF(MINUTE, 
                                    CONCAT(DATE_ADD(base.Tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang),
                                    base.Actual_Pulang
                                ) >= 60
                            )
                            THEN 'Masuk Tepat Waktu'
                        
                        -- Selain itu = TELAT (masuk H+1 tanpa kompensasi yang cukup)
                        ELSE 'Masuk Telat'
                    END
                
                -- 🆕 PRIORITAS 2B: LOGIKA KHUSUS SHIFT NON-3A - ACCOUNTING & SALES & MARKETING
                WHEN base.Departemen IN ('ACCOUNTING', 'SALES & MARKETING')
                    AND base.Kode_Shift != '3A'
                    AND base.Actual_Masuk IS NOT NULL
                    AND base.Actual_Pulang IS NOT NULL
                    AND (
                        -- Kondisi 1: Durasi kerja minimal 9 jam penuh (540 menit)
                        base.actual_duration_minutes >= 540
                        OR 
                        -- Kondisi 2: Pulang minimal 1 jam (60 menit) setelah jadwal pulang
                        (
                            CASE 
                                WHEN ij.jam_pulang < ij.jam_masuk THEN
                                    -- Shift lintas hari (misal 2A: pulang jam 00:00 di H+1)
                                    TIMESTAMPDIFF(MINUTE, 
                                        CONCAT(DATE_ADD(base.Tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang),
                                        base.Actual_Pulang
                                    )
                                ELSE
                                    -- Shift normal (misal 1A: pulang jam 16:00 di H)
                                    TIMESTAMPDIFF(MINUTE, 
                                        CONCAT(base.Tanggal, ' ', ij.jam_pulang),
                                        base.Actual_Pulang
                                    )
                            END >= 60  -- Minimal 60 menit setelah jadwal pulang
                        )
                    )
                    THEN 'Masuk Tepat Waktu'
                
                -- ✅ PRIORITAS 3: Cek berdasarkan waktu masuk untuk shift 3A (NON-ACCOUNTING)
                WHEN base.Kode_Shift = '3A' THEN 
                    CASE
                        WHEN DATE(base.Actual_Masuk) = DATE(base.Tanggal)
                            AND TIME(base.Actual_Masuk) >= '22:00:00'
                            AND TIME(base.Actual_Masuk) <= '23:59:59'
                            THEN 'Masuk Tepat Waktu'
                        WHEN DATE(base.Actual_Masuk) = DATE_ADD(DATE(base.Tanggal), INTERVAL 1 DAY)
                            AND TIME(base.Actual_Masuk) <= '00:15:00'  -- Toleransi 15 menit
                            THEN 'Masuk Tepat Waktu'
                        ELSE 'Masuk Telat'
                    END
                    
                WHEN ij.jam_pulang < ij.jam_masuk THEN 
                    CASE
                        WHEN DATE(base.Actual_Masuk) = DATE(base.Tanggal) 
                            AND TIME(base.Actual_Masuk) <= ADDTIME(ij.jam_masuk, '00:15:00')
                            THEN 'Masuk Tepat Waktu'
                        WHEN DATE(base.Actual_Masuk) = DATE_SUB(DATE(base.Tanggal), INTERVAL 1 DAY)
                            AND TIME(base.Actual_Masuk) >= TIME(ij.jam_masuk) 
                            THEN 'Masuk Tepat Waktu'
                        ELSE 'Masuk Telat'
                    END
                ELSE 
                    CASE
                        -- Toleransi 15 menit untuk semua shift normal
                        WHEN TIME(base.Actual_Masuk) <= ADDTIME(ij.jam_masuk, '00:15:00') 
                            THEN 'Masuk Tepat Waktu'
                        ELSE 'Masuk Telat'
                    END
            END AS Status_Masuk,

            /* ===== STATUS PULANG - DURATION-BASED LOGIC ===== */
            CASE
                WHEN base.Actual_Pulang IS NULL THEN 'Tidak scan pulang'
                
                -- ✅ PRIORITAS 1: Untuk departemen NON-ACCOUNTING/SALES
                WHEN base.Departemen NOT IN ('ACCOUNTING', 'SALES & MARKETING') THEN
                    CASE
                        -- Jika jam pulang >= jadwal pulang → TEPAT WAKTU
                        WHEN TIME(base.Actual_Pulang) >= ij.jam_pulang
                            THEN 'Pulang Tepat Waktu'
                        -- Jika durasi kerja >= 90% dari yang diharapkan = TEPAT WAKTU
                        WHEN base.actual_duration_minutes >= (base.expected_duration_minutes * 0.9) 
                            THEN 'Pulang Tepat Waktu'
                        -- Jika durasi < 90% = PULANG TERLALU CEPAT
                        ELSE 'Pulang Terlalu Cepat'
                    END
                
                -- 🆕 PRIORITAS 2: LOGIKA KHUSUS ACCOUNTING & SALES & MARKETING (SEMUA SHIFT)
                WHEN base.Departemen IN ('ACCOUNTING', 'SALES & MARKETING')
                    AND base.Actual_Masuk IS NOT NULL
                    AND base.Actual_Pulang IS NOT NULL THEN
                    CASE
                        -- Cek kompensasi: durasi >= 9 jam ATAU pulang >= 1 jam setelah jadwal
                        WHEN base.actual_duration_minutes >= 540  -- Durasi minimal 9 jam penuh
                            OR 
                            (
                                CASE 
                                    WHEN ij.jam_pulang < ij.jam_masuk THEN
                                        -- Shift lintas hari (misal 3A: pulang jam 08:00 di H+1)
                                        TIMESTAMPDIFF(MINUTE, 
                                            CONCAT(DATE_ADD(base.Tanggal, INTERVAL 1 DAY), ' ', ij.jam_pulang),
                                            base.Actual_Pulang
                                        )
                                    ELSE
                                        -- Shift normal (misal 1A: pulang jam 16:00 di H)
                                        TIMESTAMPDIFF(MINUTE, 
                                            CONCAT(base.Tanggal, ' ', ij.jam_pulang),
                                            base.Actual_Pulang
                                        )
                                END >= 60  -- Minimal 60 menit setelah jadwal pulang
                            )
                            THEN 'Pulang Tepat Waktu'
                        -- Jika tidak memenuhi kompensasi, cek waktu pulang normal
                        WHEN TIME(base.Actual_Pulang) >= ij.jam_pulang
                            THEN 'Pulang Tepat Waktu'
                        ELSE 'Pulang Terlalu Cepat'
                    END
                
                -- Fallback
                ELSE 'Pulang Terlalu Cepat'
                
            END AS Status_Pulang

            FROM base_with_duration base
            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            LEFT JOIN prediction_data pred ON pred.nama = base.Nama 
                AND pred.tanggal = base.Tanggal 
                AND pred.rn = 1

            ORDER BY base.Nama, base.Tanggal;
            """
            

            query26DESEMBER = """
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
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

                # CASE
                #     WHEN base.Actual_Masuk IS NULL THEN 'Tidak scan masuk'
                #     WHEN base.Actual_Masuk <= base.Scheduled_Start THEN 'Masuk Tepat Waktu'
                #     ELSE 'Masuk Telat'
                # END AS Status_Masuk,
                
                # CASE
                #     WHEN base.Actual_Masuk IS NULL THEN 'Tidak scan masuk'

                #     /* ===== KHUSUS SHIFT 3 & 3A (lintas hari) ===== */
                #     WHEN base.Kode_Shift IN ('3','3A','D2/3A','D2/3') THEN
                #         CASE
                #             WHEN TIME(base.Actual_Masuk) BETWEEN '20:00:00' AND '23:59:59'
                #             OR TIME(base.Actual_Masuk) BETWEEN '00:00:00' AND '02:59:59'
                #             THEN 'Masuk Tepat Waktu'
                #             ELSE 'Masuk Telat'
                #         END

                #     /* ===== DEFAULT ===== */
                #     WHEN base.Actual_Masuk <= base.Scheduled_Start THEN 'Masuk Tepat Waktu'
                #     ELSE 'Masuk Telat'
                # END AS Status_Masuk,
                
                CASE
                    WHEN base.Actual_Masuk IS NULL
                        THEN 'Tidak scan masuk'

                    WHEN base.Actual_Masuk > base.Scheduled_Start
                        THEN 'Masuk Telat'

                    ELSE 'Masuk Tepat Waktu'
                END AS Status_Masuk,



                -- ===== STATUS PULANG (FIXED) =====
                # CASE
                #     WHEN base.Actual_Pulang IS NULL 
                #         THEN 'Tidak scan pulang'
                #     -- Pulang terlalu cepat (lebih dari 15 menit sebelum jadwal)
                #     WHEN base.Actual_Pulang < DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
                #         THEN 'Pulang Terlalu Cepat'
                #     -- Pulang tepat waktu (dalam rentang -15 menit s/d +15 menit dari jadwal)
                #     WHEN base.Actual_Pulang BETWEEN 
                #             DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE) 
                #             AND DATE_ADD(base.Scheduled_End, INTERVAL 15 MINUTE)
                #         THEN 'Pulang Tepat Waktu'
                #     -- Pulang telat (lebih dari 15 menit setelah jadwal)
                #     ELSE 'Pulang Tepat Waktu'
                # END AS Status_Pulang
                
                # CASE
                #     WHEN base.Actual_Pulang IS NULL THEN 'Tidak scan pulang'

                #     /* ===== KHUSUS SHIFT 3 & 3A ===== */
                #     WHEN base.Kode_Shift IN ('3','3A','D2/3A','D2/3') THEN
                #         CASE
                #             WHEN TIME(base.Actual_Pulang) BETWEEN '05:00:00' AND '10:00:00'
                #                 THEN 'Pulang Tepat Waktu'
                #             ELSE 'Pulang Terlalu Cepat'
                #         END

                #     /* ===== DEFAULT ===== */
                #     WHEN base.Actual_Pulang < DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
                #         THEN 'Pulang Terlalu Cepat'
                #     WHEN base.Actual_Pulang BETWEEN
                #         DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
                #         AND DATE_ADD(base.Scheduled_End, INTERVAL 15 MINUTE)
                #         THEN 'Pulang Tepat Waktu'
                #     ELSE 'Pulang Tepat Waktu'
                # END AS Status_Pulang
                
                CASE
                    WHEN base.Actual_Pulang IS NULL 
                        THEN 'Tidak scan pulang'

                    WHEN base.Actual_Pulang < base.Scheduled_End
                        THEN 'Pulang Terlalu Cepat'

                    ELSE 'Pulang Tepat Waktu'
                END AS Status_Pulang



            FROM (

                SELECT
                    jk.nama AS Nama,
                    jk.tanggal AS Tanggal,
                    jk.kode_shift AS Kode_Shift,
                    si.jam_masuk AS Jadwal_Masuk,
                    si.jam_pulang AS Jadwal_Pulang,

                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik,

                    # CASE
                    #     WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
                    #         THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
                    #     ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    # END AS Scheduled_Start,
                    
                    CASE
                        -- SHIFT 3A → masuk malam hari sebelumnya
                        WHEN jk.kode_shift = '3A'
                            THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)

                        -- shift lain normal
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    END AS Scheduled_Start,


                    # CASE
                    #     WHEN si.lintas_hari = 1
                    #         THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                    #     ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    # END AS Scheduled_End,
                    
                    CASE
                        -- KHUSUS 3A → selesai di hari yang sama
                        WHEN jk.kode_shift = '3A'
                            THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)

                        -- shift lintas hari lainnya
                        WHEN si.lintas_hari = 1
                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)

                        ELSE
                            CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    END AS Scheduled_End,



                    /* =====================
                    ACTUAL MASUK - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift IN ('3','3A')
                        AND si.lintas_hari = 1
                        THEN (

                            SELECT MIN(k.tanggal_scan)
                            FROM kehadiran_karyawan k
                            WHERE k.nama = jk.nama

                            AND (
                                /* =====================================================
                                MODE KHUSUS: HANYA AKTIF DI AWAL BULAN
                                ===================================================== */
                                (
                                    DAY(jk.tanggal) = 1
                                    AND
                                    (
                                        -- scan dini hari hari H
                                        (
                                            DATE(k.tanggal_scan) = jk.tanggal
                                            AND TIME(k.tanggal_scan) BETWEEN '00:00:00' AND '05:00:00'
                                        )
                                        OR
                                        -- scan malam H-1 (wajib ada jadwal H-1)
                                        (
                                            DATE(k.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY)
                                            AND TIME(k.tanggal_scan) BETWEEN '22:00:00' AND '23:59:59'
                                            AND EXISTS (
                                                SELECT 1
                                                FROM jadwal_karyawan jp
                                                WHERE jp.nama = jk.nama
                                                AND jp.tanggal = DATE_SUB(jk.tanggal, INTERVAL 1 DAY)
                                                AND jp.kode_shift IN ('3','3A')
                                            )
                                        )
                                    )
                                )

                                OR

                                /* =====================================================
                                MODE NORMAL (HARI TENGAH BULAN)
                                ===================================================== */
                                (
                                    DAY(jk.tanggal) <> 1
                                    AND k.tanggal_scan BETWEEN
                                        CAST(CONCAT(jk.tanggal, ' 20:00:00') AS DATETIME)
                                        AND
                                        CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 02:59:59') AS DATETIME)
                                )
                            )
                            /* ============================================
                            HARD BLOCK: cegah 23:xx nempel ke tanggal yg salah
                            (hanya saat awal bulan)
                            ============================================ */
                            AND NOT (
                                DAY(jk.tanggal) = 1
                                AND DATE(k.tanggal_scan) = jk.tanggal
                                AND TIME(k.tanggal_scan) >= '22:00:00'
                            )
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            AND k3.tanggal_scan BETWEEN
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
                                END
                            )
                            AND
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
                                END
                            )
                        )
                    END AS Actual_Masuk,

                    /* =====================
                    ACTUAL PULANG - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        /* ===== SHIFT 3A : hanya valid jika ada jadwal H-1 ===== */
                        WHEN jk.kode_shift = '3A'
                        AND si.lintas_hari = 1
                        AND EXISTS (
                            SELECT 1
                            FROM jadwal_karyawan j_prev
                            WHERE j_prev.nama = jk.nama
                            AND j_prev.tanggal = DATE_SUB(jk.tanggal, INTERVAL 1 DAY)
                            AND j_prev.kode_shift = '3A'
                        )
                        THEN (
                            SELECT MAX(k.tanggal_scan)
                            FROM kehadiran_karyawan k
                            WHERE k.nama = jk.nama
                            AND k.tanggal_scan BETWEEN
                                CAST(CONCAT(jk.tanggal, ' 06:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(jk.tanggal, ' 11:00:00') AS DATETIME)
                        )

                        /* ===== SHIFT 3B CHECK-OUT (PAGI) ===== */
                        WHEN jk.kode_shift = '3B' THEN (
                            SELECT MAX(k.tanggal_scan)
                            FROM kehadiran_karyawan k
                            WHERE k.nama = jk.nama
                            AND k.tanggal_scan BETWEEN
                                CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 05:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' 10:00:00') AS DATETIME)
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            AND k4.tanggal_scan BETWEEN
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                    END
                                )
                                AND
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
                                    END
                                )
                            AND DATE(k4.tanggal_scan) IN (
                                DATE(jk.tanggal),
                                DATE(
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                    END
                                )
                            )
                            AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR
                            AND k4.tanggal_scan >=
                            (
                                CASE
                                    WHEN si.lintas_hari = 1
                                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                END
                            )
                        )
                    END AS Actual_Pulang


                FROM jadwal_karyawan jk
                LEFT JOIN shift_info si ON jk.kode_shift = si.kode
                LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

                GROUP BY
                    jk.nama, jk.tanggal, jk.kode_shift,
                    si.jam_masuk, si.jam_pulang,
                    k.jabatan, k.dept, k.id_karyawan, k.nik

            ) AS base

            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            ORDER BY base.Nama, base.Tanggal;
            """


            
            # Gunakan query dengan perbaikan logika pulang
            querysolvingstatus_pulang_bug_error = """
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
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

                -- ===== STATUS PULANG (FIXED) =====
                CASE
                    WHEN base.Actual_Pulang IS NULL 
                        THEN 'Tidak scan pulang'
                    -- Pulang terlalu cepat (lebih dari 15 menit sebelum jadwal)
                    WHEN base.Actual_Pulang < DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
                        THEN 'Pulang Terlalu Cepat'
                    -- Pulang tepat waktu (dalam rentang -15 menit s/d +15 menit dari jadwal)
                    WHEN base.Actual_Pulang BETWEEN 
                            DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE) 
                            AND DATE_ADD(base.Scheduled_End, INTERVAL 15 MINUTE)
                        THEN 'Pulang Tepat Waktu'
                    -- Pulang telat (lebih dari 15 menit setelah jadwal)
                    ELSE 'Pulang Tepat Waktu'
                END AS Status_Pulang

            FROM (

                SELECT
                    jk.nama AS Nama,
                    jk.tanggal AS Tanggal,
                    jk.kode_shift AS Kode_Shift,
                    si.jam_masuk AS Jadwal_Masuk,
                    si.jam_pulang AS Jadwal_Pulang,

                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik,

                    CASE
                        WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
                            THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    END AS Scheduled_Start,

                    CASE
                        WHEN si.lintas_hari = 1
                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    END AS Scheduled_End,


                    /* =====================
                    ACTUAL MASUK - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            -- Filter tanggal: scan bisa di hari sebelumnya (jam 22:00+) atau hari jadwal (jam 00:00-05:00)
                            AND (
                                (DATE(k3.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k3.tanggal_scan) >= '22:00:00')
                                OR
                                (DATE(k3.tanggal_scan) = jk.tanggal AND TIME(k3.tanggal_scan) <= '05:00:00')
                            )
                            -- Window waktu absolute
                            AND k3.tanggal_scan BETWEEN
                                CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
                            -- ANTI-DUPLIKASI: scan ini tidak boleh sudah dipakai sebagai pulang di jadwal sebelumnya
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM jadwal_karyawan jk_prev
                                LEFT JOIN shift_info si_prev ON jk_prev.kode_shift = si_prev.kode
                                WHERE jk_prev.nama = jk.nama
                                AND jk_prev.tanggal < jk.tanggal
                                AND jk_prev.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                -- Cek apakah scan ini masuk window pulang jadwal sebelumnya
                                AND k3.tanggal_scan BETWEEN
                                    CAST(CONCAT(jk_prev.tanggal, ' 06:00:00') AS DATETIME)
                                    AND
                                    CAST(CONCAT(jk_prev.tanggal, ' 12:00:00') AS DATETIME)
                                AND DATE(k3.tanggal_scan) = jk_prev.tanggal
                            )
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            AND k3.tanggal_scan BETWEEN
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
                                END
                            )
                            AND
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
                                END
                            )
                        )
                    END AS Actual_Masuk,

                    /* =====================
                    ACTUAL PULANG - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            -- PENTING: Tanggal scan HARUS sama dengan tanggal jadwal
                            AND DATE(k4.tanggal_scan) = jk.tanggal
                            -- Window waktu: jam 06:00 - 11:00 di hari jadwal
                            AND TIME(k4.tanggal_scan) BETWEEN '06:00:00' AND '11:00:00'
                            AND k4.tanggal_scan BETWEEN
                                CAST(CONCAT(jk.tanggal, ' 06:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(jk.tanggal, ' 11:00:00') AS DATETIME)
                            -- ANTI-DUPLIKASI: scan pulang tidak boleh dipakai sebagai masuk di jadwal berikutnya
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM jadwal_karyawan jk_next
                                LEFT JOIN shift_info si_next ON jk_next.kode_shift = si_next.kode
                                WHERE jk_next.nama = jk.nama
                                AND jk_next.tanggal > jk.tanggal
                                AND jk_next.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                -- Cek apakah scan ini masuk window masuk jadwal berikutnya
                                AND (
                                    (DATE(k4.tanggal_scan) = DATE_SUB(jk_next.tanggal, INTERVAL 1 DAY) AND TIME(k4.tanggal_scan) >= '22:00:00')
                                    OR
                                    (DATE(k4.tanggal_scan) = jk_next.tanggal AND TIME(k4.tanggal_scan) <= '05:00:00')
                                )
                            )
                            -- Scan pulang harus lebih besar dari scan masuk (jika scan masuk ada)
                            AND k4.tanggal_scan > COALESCE(
                                (
                                    SELECT MIN(k5.tanggal_scan)
                                    FROM kehadiran_karyawan k5
                                    WHERE k5.nama = jk.nama
                                    AND (
                                        (DATE(k5.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k5.tanggal_scan) >= '22:00:00')
                                        OR
                                        (DATE(k5.tanggal_scan) = jk.tanggal AND TIME(k5.tanggal_scan) <= '05:00:00')
                                    )
                                    AND k5.tanggal_scan BETWEEN
                                        CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
                                        AND
                                        CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
                                ),
                                CAST('1970-01-01 00:00:00' AS DATETIME)  -- Default jika scan masuk NULL
                            )
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            AND k4.tanggal_scan BETWEEN
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                    END
                                )
                                AND
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
                                    END
                                )
                            AND DATE(k4.tanggal_scan) IN (
                                DATE(jk.tanggal),
                                DATE(
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                    END
                                )
                            )
                            AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR
                            AND k4.tanggal_scan >=
                            (
                                CASE
                                    WHEN si.lintas_hari = 1
                                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                END
                            )
                        )
                    END AS Actual_Pulang


                FROM jadwal_karyawan jk
                LEFT JOIN shift_info si ON jk.kode_shift = si.kode
                LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

                GROUP BY
                    jk.nama, jk.tanggal, jk.kode_shift,
                    si.jam_masuk, si.jam_pulang,
                    k.jabatan, k.dept, k.id_karyawan, k.nik

            ) AS base

            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            ORDER BY base.Nama, base.Tanggal;
            """
            
            # Data sudah ada, namu status pulang dan masuk nya error bug           
            querydefaultstatuspulang = """
            SELECT
                base.Nama,
                base.Tanggal,
                base.Kode_Shift,
                base.Jabatan,
                base.Departemen,
                base.id_karyawan,
                base.NIK,
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

                    k.jabatan AS Jabatan,
                    k.dept AS Departemen,
                    k.id_karyawan,
                    k.nik,

                    CASE
                        WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
                            THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
                    END AS Scheduled_Start,

                    CASE
                        WHEN si.lintas_hari = 1
                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                    END AS Scheduled_End,


                    /* =====================
                    ACTUAL MASUK - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            -- Filter tanggal: scan bisa di hari sebelumnya (jam 22:00+) atau hari jadwal (jam 00:00-05:00)
                            AND (
                                (DATE(k3.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k3.tanggal_scan) >= '22:00:00')
                                OR
                                (DATE(k3.tanggal_scan) = jk.tanggal AND TIME(k3.tanggal_scan) <= '05:00:00')
                            )
                            -- Window waktu absolute
                            AND k3.tanggal_scan BETWEEN
                                CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
                            -- ANTI-DUPLIKASI: scan ini tidak boleh sudah dipakai sebagai pulang di jadwal sebelumnya
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM jadwal_karyawan jk_prev
                                LEFT JOIN shift_info si_prev ON jk_prev.kode_shift = si_prev.kode
                                WHERE jk_prev.nama = jk.nama
                                AND jk_prev.tanggal < jk.tanggal
                                AND jk_prev.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                -- Cek apakah scan ini masuk window pulang jadwal sebelumnya
                                AND k3.tanggal_scan BETWEEN
                                    CAST(CONCAT(jk_prev.tanggal, ' 06:00:00') AS DATETIME)
                                    AND
                                    CAST(CONCAT(jk_prev.tanggal, ' 12:00:00') AS DATETIME)
                                AND DATE(k3.tanggal_scan) = jk_prev.tanggal
                            )
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MIN(k3.tanggal_scan)
                            FROM kehadiran_karyawan k3
                            WHERE k3.nama = jk.nama
                            AND k3.tanggal_scan BETWEEN
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
                                END
                            )
                            AND
                            (
                                CASE
                                    WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
                                        THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
                                END
                            )
                        )
                    END AS Actual_Masuk,

                    /* =====================
                    ACTUAL PULANG - DENGAN LOGIC KHUSUS SHIFT 3A
                    ===================== */
                    CASE
                        WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
                        -- LOGIC KHUSUS UNTUK SHIFT 3A (LINTAS HARI 00:00-08:00)
                        WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            -- PENTING: Tanggal scan HARUS sama dengan tanggal jadwal
                            AND DATE(k4.tanggal_scan) = jk.tanggal
                            -- Window waktu: jam 06:00 - 11:00 di hari jadwal
                            AND TIME(k4.tanggal_scan) BETWEEN '06:00:00' AND '11:00:00'
                            AND k4.tanggal_scan BETWEEN
                                CAST(CONCAT(jk.tanggal, ' 06:00:00') AS DATETIME)
                                AND
                                CAST(CONCAT(jk.tanggal, ' 11:00:00') AS DATETIME)
                            -- ANTI-DUPLIKASI: scan pulang tidak boleh dipakai sebagai masuk di jadwal berikutnya
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM jadwal_karyawan jk_next
                                LEFT JOIN shift_info si_next ON jk_next.kode_shift = si_next.kode
                                WHERE jk_next.nama = jk.nama
                                AND jk_next.tanggal > jk.tanggal
                                AND jk_next.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
                                -- Cek apakah scan ini masuk window masuk jadwal berikutnya
                                AND (
                                    (DATE(k4.tanggal_scan) = DATE_SUB(jk_next.tanggal, INTERVAL 1 DAY) AND TIME(k4.tanggal_scan) >= '22:00:00')
                                    OR
                                    (DATE(k4.tanggal_scan) = jk_next.tanggal AND TIME(k4.tanggal_scan) <= '05:00:00')
                                )
                            )
                            -- Scan pulang harus lebih besar dari scan masuk (jika scan masuk ada)
                            AND k4.tanggal_scan > COALESCE(
                                (
                                    SELECT MIN(k5.tanggal_scan)
                                    FROM kehadiran_karyawan k5
                                    WHERE k5.nama = jk.nama
                                    AND (
                                        (DATE(k5.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k5.tanggal_scan) >= '22:00:00')
                                        OR
                                        (DATE(k5.tanggal_scan) = jk.tanggal AND TIME(k5.tanggal_scan) <= '05:00:00')
                                    )
                                    AND k5.tanggal_scan BETWEEN
                                        CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
                                        AND
                                        CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
                                ),
                                CAST('1970-01-01 00:00:00' AS DATETIME)  -- Default jika scan masuk NULL
                            )
                        )
                        
                        -- LOGIC DEFAULT UNTUK SHIFT LAINNYA (TETAP SEPERTI SEMULA)
                        ELSE (
                            SELECT MAX(k4.tanggal_scan)
                            FROM kehadiran_karyawan k4
                            WHERE k4.nama = jk.nama
                            AND k4.tanggal_scan BETWEEN
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
                                    END
                                )
                                AND
                                (
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
                                    END
                                )
                            AND DATE(k4.tanggal_scan) IN (
                                DATE(jk.tanggal),
                                DATE(
                                    CASE
                                        WHEN si.lintas_hari = 1
                                            THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                        ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                    END
                                )
                            )
                            AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR
                            AND k4.tanggal_scan >=
                            (
                                CASE
                                    WHEN si.lintas_hari = 1
                                        THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                    ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
                                            - INTERVAL 2 HOUR
                                END
                            )
                        )
                    END AS Actual_Pulang


                FROM jadwal_karyawan jk
                LEFT JOIN shift_info si ON jk.kode_shift = si.kode
                LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

                GROUP BY
                    jk.nama, jk.tanggal, jk.kode_shift,
                    si.jam_masuk, si.jam_pulang,
                    k.jabatan, k.dept, k.id_karyawan, k.nik

            ) AS base

            LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            ORDER BY base.Nama, base.Tanggal;
            """
            
            # query = """
            # SELECT
            #     base.Nama,
            #     base.Tanggal,
            #     base.Kode_Shift,
            #     base.Jabatan,
            #     base.Departemen,
            #     base.id_karyawan,
            #     base.NIK,
            #     base.Jadwal_Masuk,
            #     base.Jadwal_Pulang,
            #     base.Actual_Masuk,
            #     base.Actual_Pulang,

            #     -- Status Kehadiran (tidak berubah)
            #     CASE
            #         WHEN base.Kode_Shift IN ('CT','CTT','EO','OF1','CTB','X')
            #             THEN ij.keterangan
            #         WHEN base.Actual_Masuk IS NULL AND base.Actual_Pulang IS NULL
            #             THEN 'Tidak Hadir'
            #         ELSE 'Hadir'
            #     END AS Status_Kehadiran,

            #     -- ===== STATUS MASUK (FIXED) =====
            #     CASE
            #         WHEN base.Actual_Masuk IS NULL 
            #             THEN 'Tidak scan masuk'
            #         WHEN base.Actual_Masuk <= base.Scheduled_Start 
            #             THEN 'Masuk Tepat Waktu'
            #         WHEN base.Actual_Masuk <= DATE_ADD(base.Scheduled_Start, INTERVAL 15 MINUTE)
            #             THEN 'Masuk Telat'
            #         ELSE 'Masuk Telat'
            #     END AS Status_Masuk,

            #     -- ===== STATUS PULANG (FIXED) =====
            #     CASE
            #         WHEN base.Actual_Pulang IS NULL 
            #             THEN 'Tidak scan pulang'
            #         -- Pulang terlalu cepat (lebih dari 15 menit sebelum jadwal)
            #         WHEN base.Actual_Pulang < DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE)
            #             THEN 'Pulang Terlalu Cepat'
            #         -- Pulang tepat waktu (dalam rentang -15 menit s/d +15 menit dari jadwal)
            #         WHEN base.Actual_Pulang BETWEEN 
            #                 DATE_SUB(base.Scheduled_End, INTERVAL 15 MINUTE) 
            #                 AND DATE_ADD(base.Scheduled_End, INTERVAL 15 MINUTE)
            #             THEN 'Pulang Tepat Waktu'
            #         -- Pulang telat (lebih dari 15 menit setelah jadwal)
            #         ELSE 'Pulang Tepat Waktu'
            #     END AS Status_Pulang

            # FROM (

            #     SELECT
            #         jk.nama AS Nama,
            #         jk.tanggal AS Tanggal,
            #         jk.kode_shift AS Kode_Shift,
            #         si.jam_masuk AS Jadwal_Masuk,
            #         si.jam_pulang AS Jadwal_Pulang,

            #         k.jabatan AS Jabatan,
            #         k.dept AS Departemen,
            #         k.id_karyawan,
            #         k.nik,

            #         -- ===== SCHEDULED START (TIDAK BERUBAH) =====
            #         CASE
            #             WHEN si.lintas_hari = 0 AND si.jam_masuk = '00:00:00'
            #                 THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 23:00:00') AS DATETIME)
            #             ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME)
            #         END AS Scheduled_Start,

            #         -- ===== SCHEDULED END (FIXED!) =====
            #         -- Khusus shift 3A (00:00-08:00): Pulang di hari yang sama, BUKAN hari berikutnya!
            #         CASE
            #             WHEN jk.kode_shift = '3A' AND si.jam_masuk = '00:00:00' AND si.jam_pulang = '08:00:00'
            #                 THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
            #             WHEN si.lintas_hari = 1
            #                 THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
            #             ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
            #         END AS Scheduled_End,

            #         /* =====================
            #         ACTUAL MASUK - LOGIC TETAP SAMA
            #         ===================== */
            #         CASE
            #             WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
            #             -- LOGIC KHUSUS UNTUK SHIFT 3A
            #             WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
            #                 SELECT MIN(k3.tanggal_scan)
            #                 FROM kehadiran_karyawan k3
            #                 WHERE k3.nama = jk.nama
            #                 AND (
            #                     (DATE(k3.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k3.tanggal_scan) >= '22:00:00')
            #                     OR
            #                     (DATE(k3.tanggal_scan) = jk.tanggal AND TIME(k3.tanggal_scan) <= '05:00:00')
            #                 )
            #                 AND k3.tanggal_scan BETWEEN
            #                     CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
            #                     AND
            #                     CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
            #                 AND NOT EXISTS (
            #                     SELECT 1 
            #                     FROM jadwal_karyawan jk_prev
            #                     LEFT JOIN shift_info si_prev ON jk_prev.kode_shift = si_prev.kode
            #                     WHERE jk_prev.nama = jk.nama
            #                     AND jk_prev.tanggal < jk.tanggal
            #                     AND jk_prev.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
            #                     AND k3.tanggal_scan BETWEEN
            #                         CAST(CONCAT(jk_prev.tanggal, ' 06:00:00') AS DATETIME)
            #                         AND
            #                         CAST(CONCAT(jk_prev.tanggal, ' 12:00:00') AS DATETIME)
            #                     AND DATE(k3.tanggal_scan) = jk_prev.tanggal
            #                 )
            #             )
                        
            #             -- LOGIC DEFAULT UNTUK SHIFT LAINNYA
            #             ELSE (
            #                 SELECT MIN(k3.tanggal_scan)
            #                 FROM kehadiran_karyawan k3
            #                 WHERE k3.nama = jk.nama
            #                 AND k3.tanggal_scan BETWEEN
            #                 (
            #                     CASE
            #                         WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
            #                             THEN CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 18:00:00') AS DATETIME)
            #                         ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) - INTERVAL 6 HOUR
            #                     END
            #                 )
            #                 AND
            #                 (
            #                     CASE
            #                         WHEN si.lintas_hari = 1 AND si.jam_masuk = '00:00:00'
            #                             THEN CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 24 HOUR
            #                         ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 4 HOUR
            #                     END
            #                 )
            #             )
            #         END AS Actual_Masuk,

            #         /* =====================
            #         ACTUAL PULANG - LOGIC TETAP SAMA
            #         ===================== */
            #         CASE
            #             WHEN jk.kode_shift IN ('CT','CTT','EO','OF1','CTB','X') THEN NULL
                        
            #             -- LOGIC KHUSUS UNTUK SHIFT 3A
            #             WHEN jk.kode_shift = '3A' AND si.lintas_hari = 1 AND si.jam_masuk = '00:00:00' THEN (
            #                 SELECT MAX(k4.tanggal_scan)
            #                 FROM kehadiran_karyawan k4
            #                 WHERE k4.nama = jk.nama
            #                 AND DATE(k4.tanggal_scan) = jk.tanggal
            #                 AND TIME(k4.tanggal_scan) BETWEEN '06:00:00' AND '11:00:00'
            #                 AND k4.tanggal_scan BETWEEN
            #                     CAST(CONCAT(jk.tanggal, ' 06:00:00') AS DATETIME)
            #                     AND
            #                     CAST(CONCAT(jk.tanggal, ' 11:00:00') AS DATETIME)
            #                 AND NOT EXISTS (
            #                     SELECT 1 
            #                     FROM jadwal_karyawan jk_next
            #                     LEFT JOIN shift_info si_next ON jk_next.kode_shift = si_next.kode
            #                     WHERE jk_next.nama = jk.nama
            #                     AND jk_next.tanggal > jk.tanggal
            #                     AND jk_next.kode_shift NOT IN ('CT','CTT','EO','OF1','CTB','X')
            #                     AND (
            #                         (DATE(k4.tanggal_scan) = DATE_SUB(jk_next.tanggal, INTERVAL 1 DAY) AND TIME(k4.tanggal_scan) >= '22:00:00')
            #                         OR
            #                         (DATE(k4.tanggal_scan) = jk_next.tanggal AND TIME(k4.tanggal_scan) <= '05:00:00')
            #                     )
            #                 )
            #                 AND k4.tanggal_scan > COALESCE(
            #                     (
            #                         SELECT MIN(k5.tanggal_scan)
            #                         FROM kehadiran_karyawan k5
            #                         WHERE k5.nama = jk.nama
            #                         AND (
            #                             (DATE(k5.tanggal_scan) = DATE_SUB(jk.tanggal, INTERVAL 1 DAY) AND TIME(k5.tanggal_scan) >= '22:00:00')
            #                             OR
            #                             (DATE(k5.tanggal_scan) = jk.tanggal AND TIME(k5.tanggal_scan) <= '05:00:00')
            #                         )
            #                         AND k5.tanggal_scan BETWEEN
            #                             CAST(CONCAT(DATE_SUB(jk.tanggal, INTERVAL 1 DAY), ' 22:00:00') AS DATETIME)
            #                             AND
            #                             CAST(CONCAT(jk.tanggal, ' 05:00:00') AS DATETIME)
            #                     ),
            #                     CAST('1970-01-01 00:00:00' AS DATETIME)
            #                 )
            #             )
                        
            #             -- LOGIC DEFAULT UNTUK SHIFT LAINNYA
            #             ELSE (
            #                 SELECT MAX(k4.tanggal_scan)
            #                 FROM kehadiran_karyawan k4
            #                 WHERE k4.nama = jk.nama
            #                 AND k4.tanggal_scan BETWEEN
            #                     (
            #                         CASE
            #                             WHEN si.lintas_hari = 1 AND si.jam_pulang = '00:00:00'
            #                                 THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 24 HOUR
            #                             WHEN si.lintas_hari = 1
            #                                 THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
            #                             ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) - INTERVAL 12 HOUR
            #                         END
            #                     )
            #                     AND
            #                     (
            #                         CASE
            #                             WHEN si.lintas_hari = 1
            #                                 THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME) + INTERVAL 2 HOUR
            #                             ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME) + INTERVAL 6 HOUR
            #                         END
            #                     )
            #                 AND DATE(k4.tanggal_scan) IN (
            #                     DATE(jk.tanggal),
            #                     DATE(
            #                         CASE
            #                             WHEN si.lintas_hari = 1
            #                                 THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
            #                             ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
            #                         END
            #                     )
            #                 )
            #                 AND k4.tanggal_scan > CAST(CONCAT(jk.tanggal, ' ', si.jam_masuk) AS DATETIME) + INTERVAL 1 HOUR
            #                 AND k4.tanggal_scan >=
            #                 (
            #                     CASE
            #                         WHEN si.lintas_hari = 1
            #                             THEN CAST(CONCAT(DATE_ADD(jk.tanggal, INTERVAL 1 DAY), ' ', si.jam_pulang) AS DATETIME)
            #                                 - INTERVAL 2 HOUR
            #                         ELSE CAST(CONCAT(jk.tanggal, ' ', si.jam_pulang) AS DATETIME)
            #                                 - INTERVAL 2 HOUR
            #                     END
            #                 )
            #             )
            #         END AS Actual_Pulang

            #     FROM jadwal_karyawan jk
            #     LEFT JOIN shift_info si ON jk.kode_shift = si.kode
            #     LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan

            #     GROUP BY
            #         jk.nama, jk.tanggal, jk.kode_shift,
            #         si.jam_masuk, si.jam_pulang,
            #         k.jabatan, k.dept, k.id_karyawan, k.nik

            # ) AS base

            # LEFT JOIN informasi_jadwal ij ON ij.kode = base.Kode_Shift
            # ORDER BY base.Nama, base.Tanggal;
            # """

            cur.execute(query)
            rows = cur.fetchall()

            inserted_count = 0
            skipped_count = 0

            # 🔥 OPTIMIZATION 2: Batch insert dengan bulk insert
            batch_data = []
            batch_size = 100

            for row in rows:
                batch_data.append((
                    row["Nama"],
                    row["Tanggal"],
                    row["Kode_Shift"],
                    row["Jabatan"],
                    row["Departemen"],
                    row["id_karyawan"],
                    row["NIK"],
                    row["Jadwal_Masuk"],
                    row["Jadwal_Pulang"],
                    row["Actual_Masuk"],
                    row["Actual_Pulang"],
                    row["Prediksi_Shift"],
                    row["Prediksi_Actual_Masuk"],
                    row["Prediksi_Actual_Pulang"],
                    row["Probabilitas_Prediksi"],
                    row["Confidence_Score"],
                    row["Frekuensi_Shift_Historis"],
                    row["Status_Kehadiran"],
                    row["Status_Masuk"],
                    row["Status_Pulang"],
                ))
                if cur.rowcount == 1:
                    inserted_count += 1
                elif cur.rowcount == 2:
                    updated_count += 1


                # Insert dalam batch
                if len(batch_data) >= batch_size:
                    upsert_sql = """
                        INSERT INTO croscek (
                            Nama, Tanggal, Kode_Shift,
                            Jabatan, Departemen,
                            id_karyawan, NIK,
                            Jadwal_Masuk, Jadwal_Pulang,
                            Actual_Masuk, Actual_Pulang,
                            Prediksi_Shift, Prediksi_Actual_Masuk, Prediksi_Actual_Pulang,
                            Probabilitas_Prediksi, Confidence_Score, Frekuensi_Shift_Historis,
                            Status_Kehadiran, Status_Masuk, Status_Pulang
                        ) VALUES (%s,%s,%s,%s,%s,
                                %s,%s,
                                %s,%s,
                                %s,%s,
                                %s,%s,%s,
                                %s,%s,%s,
                                %s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                            Kode_Shift = VALUES(Kode_Shift),
                            Jabatan = VALUES(Jabatan),
                            Departemen = VALUES(Departemen),
                            id_karyawan = VALUES(id_karyawan),
                            NIK = VALUES(NIK),
                            Jadwal_Masuk = VALUES(Jadwal_Masuk),
                            Jadwal_Pulang = VALUES(Jadwal_Pulang),
                            Actual_Masuk = VALUES(Actual_Masuk),
                            Actual_Pulang = VALUES(Actual_Pulang),
                            Status_Kehadiran = VALUES(Status_Kehadiran),
                            Status_Masuk = VALUES(Status_Masuk),
                            Status_Pulang = VALUES(Status_Pulang)
                        """

                    for data in batch_data:
                        cur.execute(upsert_sql, data)

                    conn.commit()
                    batch_data = []

            # Insert sisa data
            if batch_data:
                upsert_sql = """
                    INSERT INTO croscek (
                        Nama, Tanggal, Kode_Shift,
                        Jabatan, Departemen,
                        id_karyawan, NIK,
                        Jadwal_Masuk, Jadwal_Pulang,
                        Actual_Masuk, Actual_Pulang,
                        Prediksi_Shift, Prediksi_Actual_Masuk, Prediksi_Actual_Pulang,
                        Probabilitas_Prediksi, Confidence_Score, Frekuensi_Shift_Historis,
                        Status_Kehadiran, Status_Masuk, Status_Pulang
                    ) VALUES (%s,%s,%s,%s,%s,
                            %s,%s,
                            %s,%s,
                            %s,%s,
                            %s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        Kode_Shift = VALUES(Kode_Shift),
                        Jabatan = VALUES(Jabatan),
                        Departemen = VALUES(Departemen),
                        id_karyawan = VALUES(id_karyawan),
                        NIK = VALUES(NIK),
                        Jadwal_Masuk = VALUES(Jadwal_Masuk),
                        Jadwal_Pulang = VALUES(Jadwal_Pulang),
                        Actual_Masuk = VALUES(Actual_Masuk),
                        Actual_Pulang = VALUES(Actual_Pulang),
                        Status_Kehadiran = VALUES(Status_Kehadiran),
                        Status_Masuk = VALUES(Status_Masuk),
                        Status_Pulang = VALUES(Status_Pulang)
                    """

                for data in batch_data:
                    cur.execute(upsert_sql, data)
                
                conn.commit()

            # Fetch data terbaru dari tabel croscek
            cur.execute("""
                SELECT
                    Nama,
                    Tanggal,
                    Kode_Shift,
                    Jabatan,
                    Departemen,
                    id_karyawan,
                    NIK,
                    Jadwal_Masuk,
                    Jadwal_Pulang,
                    Actual_Masuk,
                    Actual_Pulang,
                    Status_Kehadiran,
                    Status_Masuk,
                    Status_Pulang
                FROM croscek
                ORDER BY Nama, Tanggal
            """)
            
            result_rows = cur.fetchall()

            # Convert TIME/DATE fields to strings
            for row in result_rows:
                if row['Jadwal_Masuk'] is not None:
                    row['Jadwal_Masuk'] = str(row['Jadwal_Masuk'])
                if row['Jadwal_Pulang'] is not None:
                    row['Jadwal_Pulang'] = str(row['Jadwal_Pulang'])
                if row['Actual_Masuk'] is not None:
                    row['Actual_Masuk'] = str(row['Actual_Masuk'])
                if row['Actual_Pulang'] is not None:
                    row['Actual_Pulang'] = str(row['Actual_Pulang'])
                if isinstance(row['Tanggal'], date):
                    row['Tanggal'] = str(row['Tanggal'])

            cur.close()
            conn.close()

            return jsonify({
                "data": result_rows,
                "summary": {
                    "total": len(rows),
                    "inserted": inserted_count,
                    "skipped": skipped_count,
                    "from_cache": False
                }
            })
        except Exception as e:
            print("ERROR CROSCEK:", e)
            return jsonify({"error": str(e)}), 500
        
    # ======================
    # SIMPAN / UPDATE DATA
    # ======================
    if request.method == "POST":
        try:
            data = request.json
            if not data:
                return jsonify({"error": "Payload kosong"}), 400

            insert_sql = """
            INSERT INTO croscek (
                Nama, Tanggal, Kode_Shift, Jabatan, Departemen,
                id_karyawan, NIK,
                Jadwal_Masuk, Jadwal_Pulang,
                Actual_Masuk, Actual_Pulang,
                Prediksi_Shift, Prediksi_Actual_Masuk, Prediksi_Actual_Pulang,
                Probabilitas_Prediksi, Confidence_Score, Frekuensi_Shift_Historis,
                Status_Kehadiran, Status_Masuk, Status_Pulang
            ) VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,
                %s,%s,
                %s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s
            )
            ON DUPLICATE KEY UPDATE
                Kode_Shift       = VALUES(Kode_Shift),
                Jabatan          = VALUES(Jabatan),
                Departemen       = VALUES(Departemen),
                Jadwal_Masuk     = VALUES(Jadwal_Masuk),
                Jadwal_Pulang    = VALUES(Jadwal_Pulang),
                Actual_Masuk     = VALUES(Actual_Masuk),
                Actual_Pulang    = VALUES(Actual_Pulang),
                Status_Kehadiran = VALUES(Status_Kehadiran),
                Status_Masuk     = VALUES(Status_Masuk),
                Status_Pulang    = VALUES(Status_Pulang)
            """

            inserted = 0
            updated_rows = []
            inserted_data = []

            for row in data:

                raw_tgl = row["Tanggal"]

                if isinstance(raw_tgl, str):
                    try:
                        # ISO: 2024-11-01
                        tgl = datetime.fromisoformat(raw_tgl[:10]).date()
                    except:
                        try:
                            # JS Date: Sat, 01 Nov 2024
                            tgl = datetime.strptime(raw_tgl[:16], "%a, %d %b %Y").date()
                        except:
                            raise ValueError(f"Format tanggal tidak dikenali: {raw_tgl}")
                else:
                    tgl = raw_tgl

                cur.execute("""
                    SELECT Status_Kehadiran, Status_Masuk, Status_Pulang
                    FROM croscek
                    WHERE id_karyawan=%s AND Tanggal=%s
                """, (row["id_karyawan"], tgl))

                old = cur.fetchone()
                changed_fields = []

                if old:
                    if old["Status_Kehadiran"] != row["Status_Kehadiran"]:
                        changed_fields.append("Status_Kehadiran")
                    if old["Status_Masuk"] != row["Status_Masuk"]:
                        changed_fields.append("Status_Masuk")
                    if old["Status_Pulang"] != row["Status_Pulang"]:
                        changed_fields.append("Status_Pulang")

                if old and not changed_fields:
                    continue  # 🔥 hemat DB

                cur.execute(insert_sql, (
                    row["Nama"],
                    tgl,
                    row["Kode_Shift"],
                    row["Jabatan"],
                    row["Departemen"],
                    row["id_karyawan"],
                    row["NIK"],
                    row["Jadwal_Masuk"],
                    row["Jadwal_Pulang"],
                    row["Actual_Masuk"],
                    row["Actual_Pulang"],
                    row["Prediksi_Shift"],
                    row["Prediksi_Actual_Masuk"],
                    row["Prediksi_Actual_Pulang"],
                    row["Probabilitas_Prediksi"],
                    row["Confidence_Score"],
                    row["Frekuensi_Shift_Historis"],
                    row["Status_Kehadiran"],
                    row["Status_Masuk"],
                    row["Status_Pulang"],
                ))

                if old and changed_fields:
                    updated_rows.append({
                        "Nama": row["Nama"],
                        "Tanggal": str(tgl),
                        "Fields": changed_fields
                    })

                inserted += 1

            conn.commit()

            # 🔥 AMBIL DATA TERBARU DARI DATABASE UNTUK DITAMPILKAN DI UI
            cur.execute("""
                SELECT
                    Nama,
                    Tanggal,
                    Kode_Shift,
                    Jabatan,
                    Departemen,
                    id_karyawan,
                    NIK,
                    Jadwal_Masuk,
                    Jadwal_Pulang,
                    Actual_Masuk,
                    Actual_Pulang,
                    Status_Kehadiran,
                    Status_Masuk,
                    Status_Pulang
                FROM croscek
                ORDER BY Tanggal DESC, Nama ASC
            """)
            
            inserted_data = cur.fetchall()
            
            # Convert TIME/DATE fields to strings untuk JSON serialization
            for row in inserted_data:
                if row['Jadwal_Masuk'] is not None:
                    row['Jadwal_Masuk'] = str(row['Jadwal_Masuk'])
                if row['Jadwal_Pulang'] is not None:
                    row['Jadwal_Pulang'] = str(row['Jadwal_Pulang'])
                if row['Actual_Masuk'] is not None:
                    row['Actual_Masuk'] = str(row['Actual_Masuk'])
                if row['Actual_Pulang'] is not None:
                    row['Actual_Pulang'] = str(row['Actual_Pulang'])
                if isinstance(row['Tanggal'], date):
                    row['Tanggal'] = str(row['Tanggal'])

            cur.close()
            conn.close()

            return jsonify({
                "success": True,
                "total": len(data),
                "inserted": inserted,
                "updated": len(updated_rows),
                "updated_rows": updated_rows,
                "data": inserted_data
            })

        except Exception as e:
            conn.rollback()
            print("ERROR:", e)
            return jsonify({"error": str(e)}), 500


from datetime import datetime, date, timedelta
@app.route("/api/croscek/final", methods=["GET"])
def get_croscek_final():
    conn = db()
    cur = conn.cursor(dictionary=True)

    def serialize_row(row):
        result = {}
        for k, v in row.items():
            if isinstance(v, timedelta):
                total_seconds = int(v.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                result[k] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            elif isinstance(v, (datetime, date)):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    try:
        cur.execute("""
            SELECT
                Nama,
                Tanggal,
                Kode_Shift,
                Jabatan,
                Departemen,
                id_karyawan,
                NIK,
                Jadwal_Masuk,
                Jadwal_Pulang,
                Actual_Masuk,
                Actual_Pulang,
                Status_Kehadiran,
                Status_Masuk,
                Status_Pulang
            FROM croscek
            ORDER BY Tanggal, Nama
        """)

        rows = cur.fetchall()
        data = [serialize_row(row) for row in rows]

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        print("ERROR FETCH FINAL:", e)
        return jsonify({"error": str(e)}), 500







# # Helper function yang bikin error
# def parse_month_year(month_year_str):
#     dt = datetime.strptime(month_year_str, '%B %Y')
#     return dt.year, dt.month

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)