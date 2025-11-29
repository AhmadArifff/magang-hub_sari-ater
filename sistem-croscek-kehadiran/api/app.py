# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import pandas as pd
from io import BytesIO
import os
from datetime import datetime
import tempfile

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

# -----------------------
# GET ALL jadwal
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
# CREATE jadwal
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
# UPDATE jadwal
# -----------------------
@app.route("/api/update/<kode>", methods=["PUT"])
def update_jadwal(kode):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE informasi_jadwal
            SET lokasi_kerja=%s, nama_shift=%s, jam_masuk=%s, jam_pulang=%s,
                keterangan=%s, `group`=%s, status=%s, kontrol=%s
            WHERE kode=%s
        """, (
            data.get("lokasi_kerja"),
            data.get("nama_shift"),
            data.get("jam_masuk"),
            data.get("jam_pulang"),
            data.get("keterangan"),
            data.get("group"),
            data.get("status"),
            data.get("kontrol"),
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
# DELETE jadwal
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

# -----------------------
# UPLOAD EXCEL
# -----------------------
@app.route("/api/upload", methods=["POST"])
def upload_excel():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "File tidak ditemukan"}), 400

        # Baca Excel dengan pandas
        df = pd.read_excel(BytesIO(file.read()))

        required_cols = ["kode","lokasi_kerja","nama_shift","jam_masuk","jam_pulang","keterangan","group","status","kontrol"]
        for col in required_cols:
            if col not in df.columns:
                return jsonify({"error": f"Kolom '{col}' tidak ada di file"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO informasi_jadwal
                (kode, lokasi_kerja, nama_shift, jam_masuk, jam_pulang, keterangan, `group`, status, kontrol)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row["kode"], row["lokasi_kerja"], row["nama_shift"], row["jam_masuk"], row["jam_pulang"],
                row["keterangan"], row["group"], row.get("status","non-active"), row.get("kontrol","")
            ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Upload berhasil"})
    except Exception as e:
        print("ERROR UPLOAD:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------------
# 1. UPLOAD + PREVIEW ROSTER (JADWAL)
# -------------------------------
@app.route("/api/import/jadwal/preview", methods=["POST"])
def preview_jadwal():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File tidak ditemukan"}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False)
    file.save(tmp.name)

    df = pd.read_excel(tmp.name, header=None)
    html_preview = df.to_html(index=False)

    return jsonify({
        "html": html_preview,
        "rows": df.fillna("").values.tolist()
    })


# -------------------------------
# 2. SIMPAN JADWAL KE DATABASE
# -------------------------------
@app.route("/api/import/jadwal/save", methods=["POST"])
def save_jadwal():
    rows = request.json.get("rows")
    if not rows:
        return jsonify({"error": "Data kosong"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jadwal_karyawan (
            id_absen VARCHAR(20),
            nama VARCHAR(100),
            tanggal DATE,
            kode_shift VARCHAR(10)
        )
    """)

    # Ambil bulan & tahun dari baris ke-2 kolom 0
    month_header = str(rows[1][0])
    dt = datetime.strptime(month_header, "%B %Y")
    year, month = dt.year, dt.month

    # Mulai dari baris ke-6 (index 5)
    data_rows = rows[5:]

    for row in data_rows:
        id_absen = str(row[1]).strip()
        nama = str(row[2]).strip()

        for col_index in range(3, len(row)):
            kode_shift = row[col_index]

            if kode_shift == "" or pd.isna(kode_shift):
                continue

            day = col_index - 2
            try:
                tanggal = datetime(year, month, day).date()
            except:
                continue

            cursor.execute("""
                INSERT INTO jadwal_karyawan (id_absen, nama, tanggal, kode_shift)
                VALUES (%s, %s, %s, %s)
            """, (id_absen, nama, str(tanggal), str(kode_shift)))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Jadwal berhasil disimpan"})


# -------------------------------
# 3. PREVIEW KEHADIRAN
# -------------------------------
@app.route("/api/import/kehadiran/preview", methods=["POST"])
def preview_kehadiran():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File tidak ditemukan"}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False)
    file.save(tmp.name)

    df = pd.read_excel(tmp.name)
    html_preview = df.to_html(index=False)

    return jsonify({
        "html": html_preview,
        "rows": df.fillna("").to_dict(orient="records")
    })


# -------------------------------
# 4. SIMPAN KEHADIRAN KE DB
# -------------------------------
@app.route("/api/import/kehadiran/save", methods=["POST"])
def save_kehadiran():
    rows = request.json.get("rows")
    if not rows:
        return jsonify({"error": "Data kosong"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

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

    for row in rows:
        verifikasi = int(row.get("Verifikasi")) if row.get("Verifikasi") not in ["", None] else None
        io = int(row.get("I/O")) if row.get("I/O") not in ["", None] else None

        cursor.execute("""
            INSERT INTO kehadiran_karyawan (
                tanggal_scan, tanggal, jam, pin, nip, nama, jabatan, departemen, kantor,
                verifikasi, io, workcode, sn, mesin
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            row.get("Tanggal scan"),
            row.get("Tanggal"),
            row.get("Jam"),
            row.get("PIN"),
            row.get("NIP"),
            row.get("Nama"),
            row.get("Jabatan"),
            row.get("Departemen"),
            row.get("Kantor"),
            verifikasi,
            io,
            row.get("Workcode"),
            row.get("SN"),
            row.get("Mesin"),
        ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Kehadiran berhasil disimpan"})


# -------------------------------
# 5. AMBIL DATA INFO JADWAL
# -------------------------------
@app.route("/api/info-jadwal", methods=["GET"])
def list_info_jadwal():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify([{"fileName": f} for f in files])


# -------------------------------
# 6. DOWNLOAD FILE INFO JADWAL
# -------------------------------
@app.route("/api/info-jadwal/<name>", methods=["GET"])
def get_info_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)


# -------------------------------
# 7. API CROSCEK (dipanggil frontend)
# -------------------------------
@app.route("/api/croscek", methods=["POST"])
def api_croscek():
    data = request.json
    return jsonify({"message": "Croscek diproses di frontend", "received": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
