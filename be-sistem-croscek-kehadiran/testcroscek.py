import mysql.connector
import pandas as pd
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Set

class AttendanceCrosscheck:
    """
    Processor untuk crosscheck attendance dengan logic khusus untuk shift 3A (malam lintas hari)
    
    Shift 3A: 00:00 - 08:00 (lintas hari)
    - Check-in normal: scan antara 22:00 H-1 sampai 00:00 H (tepat midnight)
    - Check-in telat: scan setelah 00:00:01 H (dini hari)
    - Check-out: scan antara 06:00 - 11:00 H
    
    ANTI-DUPLICATE: Setiap scan hanya bisa dipakai 1x
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize dengan config database
        
        Args:
            db_config: Dict with keys: host, user, password, database
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        # Track scan yang sudah digunakan untuk hindari duplikasi
        self.used_checkins: Set[datetime] = set()
        self.used_checkouts: Set[datetime] = set()
        
    def connect(self):
        """Establish database connection"""
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor(dictionary=True)
        
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def fetch_schedules(self, employee_name: str = None, 
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch jadwal karyawan dari database
        
        Args:
            employee_name: Filter by employee name (optional)
            start_date: Start date 'YYYY-MM-DD' (optional)
            end_date: End date 'YYYY-MM-DD' (optional)
        """
        query = """
            SELECT 
                jk.nama,
                jk.tanggal,
                jk.kode_shift,
                jk.id_karyawan,
                k.nik,
                k.jabatan,
                k.dept as departemen,
                si.jam_masuk,
                si.jam_pulang,
                si.lintas_hari,
                ij.keterangan
            FROM jadwal_karyawan jk
            LEFT JOIN shift_info si ON jk.kode_shift = si.kode
            LEFT JOIN karyawan k ON jk.id_karyawan = k.id_karyawan
            LEFT JOIN informasi_jadwal ij ON jk.kode_shift = ij.kode
            WHERE 1=1
        """
        params = []
        
        if employee_name:
            query += " AND jk.nama = %s"
            params.append(employee_name)
        if start_date:
            query += " AND jk.tanggal >= %s"
            params.append(start_date)
        if end_date:
            query += " AND jk.tanggal <= %s"
            params.append(end_date)
            
        query += " ORDER BY jk.nama, jk.tanggal"
        
        self.cursor.execute(query, params)
        return pd.DataFrame(self.cursor.fetchall())
    
    def fetch_attendance(self, employee_name: str = None,
                        start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch data kehadiran dari database
        
        Args:
            employee_name: Filter by employee name (optional)
            start_date: Start date 'YYYY-MM-DD' (optional)
            end_date: End date 'YYYY-MM-DD' (optional)
        """
        query = """
            SELECT 
                nama,
                tanggal_scan,
                tanggal,
                jam
            FROM kehadiran_karyawan
            WHERE 1=1
        """
        params = []
        
        if employee_name:
            query += " AND nama = %s"
            params.append(employee_name)
        if start_date:
            # Ambil data dari H-1 untuk handle shift malam
            query += " AND tanggal >= DATE_SUB(%s, INTERVAL 1 DAY)"
            params.append(start_date)
        if end_date:
            # Ambil data sampai H+1 untuk handle checkout lintas hari
            query += " AND tanggal <= DATE_ADD(%s, INTERVAL 1 DAY)"
            params.append(end_date)
            
        query += " ORDER BY nama, tanggal_scan"
        
        self.cursor.execute(query, params)
        df = pd.DataFrame(self.cursor.fetchall())
        
        if not df.empty:
            # Convert to datetime
            df['tanggal_scan'] = pd.to_datetime(df['tanggal_scan'])
            df['tanggal'] = pd.to_datetime(df['tanggal'])
        
        return df
    
    def find_checkin_3a(self, attendance_df: pd.DataFrame, 
                        employee_name: str, schedule_date: datetime,
                        debug: bool = False) -> Optional[datetime]:
        """
        Logic OPTIMAL untuk mencari check-in shift 3A dengan ANTI-DUPLICATE
        
        Shift 3A (00:00-08:00) - Jadwal H:
        
        WINDOW PENCARIAN CHECK-IN:
        1. Scan malam H-1: 22:00 - 23:59:59 (NORMAL)
        2. Tepat midnight H: 00:00:00 (NORMAL) 
        3. Dini hari H: 00:00:01 - 05:00:00 (TELAT)
        
        ANTI-DUPLICATE: Skip scan yang sudah dipakai
        
        Args:
            attendance_df: DataFrame attendance records
            employee_name: Nama karyawan
            schedule_date: Tanggal jadwal (datetime object)
            debug: Print debug info
        """
        emp_scans = attendance_df[attendance_df['nama'] == employee_name].copy()
        
        if emp_scans.empty:
            return None
        
        prev_date = schedule_date - timedelta(days=1)
        
        if debug:
            print(f"\n=== CHECKIN DEBUG untuk {schedule_date.date()} ===")
            print(f"Prev date: {prev_date.date()}")
        
        # WINDOW 1: Scan malam H-1 (22:00 - 23:59:59)
        night_scans = emp_scans[
            (emp_scans['tanggal_scan'].dt.date == prev_date.date()) &
            (emp_scans['tanggal_scan'].dt.time >= time(22, 0, 0)) &
            (~emp_scans['tanggal_scan'].isin(self.used_checkins))  # ANTI-DUPLICATE
        ]
        
        if debug and not night_scans.empty:
            print(f"Night scans found: {night_scans['tanggal_scan'].tolist()}")
        
        if not night_scans.empty:
            result = night_scans['tanggal_scan'].min()
            self.used_checkins.add(result)  # Mark as used
            if debug:
                print(f"Selected: {result}")
            return result
        
        # WINDOW 2: Tepat midnight H (00:00:00)
        midnight_scans = emp_scans[
            (emp_scans['tanggal_scan'].dt.date == schedule_date.date()) &
            (emp_scans['tanggal_scan'].dt.time == time(0, 0, 0)) &
            (~emp_scans['tanggal_scan'].isin(self.used_checkins))
        ]
        
        if debug and not midnight_scans.empty:
            print(f"Midnight scans found: {midnight_scans['tanggal_scan'].tolist()}")
        
        if not midnight_scans.empty:
            result = midnight_scans['tanggal_scan'].min()
            self.used_checkins.add(result)
            if debug:
                print(f"Selected: {result}")
            return result
        
        # WINDOW 3: Dini hari H (00:00:01 - 05:00:00) - TELAT
        early_scans = emp_scans[
            (emp_scans['tanggal_scan'].dt.date == schedule_date.date()) &
            (emp_scans['tanggal_scan'].dt.time > time(0, 0, 0)) &
            (emp_scans['tanggal_scan'].dt.time <= time(5, 0, 0)) &
            (~emp_scans['tanggal_scan'].isin(self.used_checkins))
        ]
        
        if debug and not early_scans.empty:
            print(f"Early morning scans found: {early_scans['tanggal_scan'].tolist()}")
        
        if not early_scans.empty:
            result = early_scans['tanggal_scan'].min()
            self.used_checkins.add(result)
            if debug:
                print(f"Selected: {result}")
            return result
        
        if debug:
            print("No checkin found")
        
        return None
    
    def find_checkout_3a(self, attendance_df: pd.DataFrame,
                         employee_name: str, schedule_date: datetime,
                         checkin_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Logic OPTIMAL untuk mencari check-out shift 3A dengan ANTI-DUPLICATE
        
        Shift 3A checkout - Jadwal H:
        
        WINDOW PENCARIAN CHECK-OUT:
        1. Pagi H: 06:00 - 11:00 (NORMAL)
        2. Pagi H+1: 06:00 - 11:00 (CHECKOUT LINTAS HARI - hanya jika scan malam H-1)
        
        VALIDASI:
        - Checkout harus > checkin
        - Checkout HARUS setelah jam 06:00 (tidak boleh ambil scan pagi terlalu dini)
        - Skip scan yang sudah dipakai
        
        Args:
            attendance_df: DataFrame attendance records
            employee_name: Nama karyawan
            schedule_date: Tanggal jadwal (datetime object)
            checkin_time: Waktu check-in (untuk validasi)
        """
        emp_scans = attendance_df[attendance_df['nama'] == employee_name].copy()
        
        if emp_scans.empty:
            return None
        
        next_date = schedule_date + timedelta(days=1)
        prev_date = schedule_date - timedelta(days=1)
        
        # Tentukan apakah checkin dari malam H-1 (untuk menentukan window checkout)
        checkin_from_prev_night = False
        if checkin_time and checkin_time.date() == prev_date.date():
            checkin_from_prev_night = True
        
        # WINDOW 1: Pagi hari H (06:00 - 11:00)
        # Ini untuk checkout normal di hari yang sama dengan jadwal
        checkout_h = emp_scans[
            (emp_scans['tanggal_scan'].dt.date == schedule_date.date()) &
            (emp_scans['tanggal_scan'].dt.time >= time(6, 0, 0)) &
            (emp_scans['tanggal_scan'].dt.time <= time(11, 0, 0)) &
            (~emp_scans['tanggal_scan'].isin(self.used_checkouts))
        ]
        
        # Validasi: checkout > checkin
        if not checkout_h.empty and checkin_time:
            checkout_h = checkout_h[checkout_h['tanggal_scan'] > checkin_time]
        
        if not checkout_h.empty:
            result = checkout_h['tanggal_scan'].max()
            self.used_checkouts.add(result)
            return result
        
        # WINDOW 2: Pagi hari H+1 (06:00 - 11:00) - CHECKOUT LINTAS HARI
        # HANYA jika checkin dari malam H-1 (scan 22:00-23:59)
        if checkin_from_prev_night:
            checkout_h1 = emp_scans[
                (emp_scans['tanggal_scan'].dt.date == next_date.date()) &
                (emp_scans['tanggal_scan'].dt.time >= time(6, 0, 0)) &
                (emp_scans['tanggal_scan'].dt.time <= time(11, 0, 0)) &
                (~emp_scans['tanggal_scan'].isin(self.used_checkouts))
            ]
            
            if not checkout_h1.empty and checkin_time:
                checkout_h1 = checkout_h1[checkout_h1['tanggal_scan'] > checkin_time]
            
            if not checkout_h1.empty:
                result = checkout_h1['tanggal_scan'].max()
                self.used_checkouts.add(result)
                return result
        
        return None
    
    def determine_checkin_status_3a(self, checkin: Optional[datetime], 
                                     schedule_date: datetime) -> str:
        """
        Tentukan status check-in untuk shift 3A
        
        Rules:
        - Normal: scan 22:00-23:59:59 H-1 atau tepat 00:00:00 H
        - Telat: scan 00:00:01 ke atas di H
        - Tidak scan: tidak ada data
        """
        if checkin is None:
            return "Tidak scan masuk"
        
        prev_date = schedule_date - timedelta(days=1)
        
        # Normal: scan malam H-1
        if (checkin.date() == prev_date.date() and 
            checkin.time() >= time(22, 0, 0)):
            return "Normal"
        
        # Normal: scan tepat midnight
        if (checkin.date() == schedule_date.date() and 
            checkin.time() == time(0, 0, 0)):
            return "Normal"
        
        # Telat: scan dini hari setelah 00:00:00
        if (checkin.date() == schedule_date.date() and 
            checkin.time() > time(0, 0, 0)):
            return "Telat"
        
        return "Telat"
    
    def generate_keterangan_3a(self, checkin: Optional[datetime],
                               checkout: Optional[datetime],
                               schedule_date: datetime,
                               status_masuk: str) -> str:
        """
        Generate keterangan deskriptif untuk shift 3A
        
        Logic:
        - Jika masuk malam H-1 + checkout H+1 → "checkout tgl X"
        - Jika masuk malam H-1 + checkout H → "masuk DD/MM HH:MM"
        - Jika masuk tepat waktu H → "valid"
        - Jika masuk telat → "masuk dini hari"
        """
        if checkin is None and checkout is None:
            return "tidak ada scan"
        
        if checkin is None and checkout is not None:
            return "hanya checkout"
        
        if checkin is not None and checkout is None:
            return "belum checkout"
        
        # Ada checkin dan checkout
        prev_date = schedule_date - timedelta(days=1)
        next_date = schedule_date + timedelta(days=1)
        
        if status_masuk == "Normal":
            # Jika masuk malam H-1
            if checkin.date() == prev_date.date():
                # Cek apakah checkout di H+1 (lintas 2 hari)
                if checkout and checkout.date() == next_date.date():
                    return f"checkout tgl {checkout.day}"
                else:
                    # Checkout di hari H (normal)
                    return f"masuk {checkin.strftime('%d/%m')} {checkin.strftime('%H:%M')}"
            else:
                # Masuk di hari H (tepat midnight atau sebelum dini hari)
                return "valid"
        else:  # Telat
            return "masuk dini hari"
    
    def process_crosscheck(self, schedule_df: pd.DataFrame, 
                          attendance_df: pd.DataFrame) -> pd.DataFrame:
        """
        Main processor untuk crosscheck attendance
        
        PENTING: Process BERURUTAN dari tanggal terkecil untuk tracking scan
        
        Args:
            schedule_df: DataFrame jadwal karyawan (HARUS sorted by tanggal)
            attendance_df: DataFrame kehadiran
            
        Returns:
            DataFrame hasil crosscheck
        """
        results = []
        
        # Reset tracking untuk setiap karyawan
        current_employee = None
        
        for idx, schedule in schedule_df.iterrows():
            employee_name = schedule['nama']
            schedule_date = pd.to_datetime(schedule['tanggal'])
            shift_code = schedule['kode_shift']
            
            # Reset tracking jika ganti karyawan
            if current_employee != employee_name:
                current_employee = employee_name
                self.used_checkins = set()
                self.used_checkouts = set()
            
            # Handle shift khusus (cuti, off, dll)
            # PENTING: Mark scan sebagai used agar tidak tumpang tindih ke jadwal berikutnya
            if shift_code in ['CT', 'CTT', 'EO', 'OF1', 'CTB', 'X']:
                # Cari dan mark scan di window shift ini sebagai "used"
                # KECUALI scan dini hari (00:00-05:00) karena mungkin untuk jadwal hari ini
                
                prev_date = schedule_date - timedelta(days=1)
                emp_scans = attendance_df[attendance_df['nama'] == employee_name].copy()
                
                # Mark scan malam H-1 sebagai used (jika ada)
                night_scans = emp_scans[
                    (emp_scans['tanggal_scan'].dt.date == prev_date.date()) &
                    (emp_scans['tanggal_scan'].dt.time >= time(22, 0, 0))
                ]
                for _, scan in night_scans.iterrows():
                    self.used_checkins.add(scan['tanggal_scan'])
                
                # JANGAN mark scan dini hari H (00:00-05:00)
                # Karena ini kemungkinan untuk jadwal shift H (bukan libur)
                
                # Mark scan pagi H sebagai used (jika ada)
                morning_scans = emp_scans[
                    (emp_scans['tanggal_scan'].dt.date == schedule_date.date()) &
                    (emp_scans['tanggal_scan'].dt.time >= time(6, 0, 0)) &
                    (emp_scans['tanggal_scan'].dt.time <= time(11, 0, 0))
                ]
                for _, scan in morning_scans.iterrows():
                    self.used_checkouts.add(scan['tanggal_scan'])
                
                results.append({
                    'Nama': employee_name,
                    'Tanggal': schedule_date.date(),
                    'Kode_Shift': shift_code,
                    'Jabatan': schedule['jabatan'],
                    'Departemen': schedule['departemen'],
                    'id_karyawan': schedule['id_karyawan'],
                    'NIK': schedule['nik'],
                    'Jadwal_Masuk': schedule['jam_masuk'],
                    'Jadwal_Pulang': schedule['jam_pulang'],
                    'Actual_Masuk': None,
                    'Actual_Pulang': None,
                    'Status_Kehadiran': 'Tidak ada data',
                    'Status_Masuk': 'Tidak ada data',
                    'Status_Pulang': '-',
                    'Keterangan': 'tidak ada scan'
                })
                continue
            
            # Process shift 3A (khusus logic)
            if shift_code == '3A':
                # Debug mode (set True untuk troubleshooting)
                debug_mode = False
                
                checkin = self.find_checkin_3a(
                    attendance_df, employee_name, schedule_date, debug=debug_mode
                )
                checkout = self.find_checkout_3a(
                    attendance_df, employee_name, schedule_date, checkin
                )
                
                status_masuk = self.determine_checkin_status_3a(checkin, schedule_date)
                
                # Tentukan status kehadiran
                if checkin is None and checkout is None:
                    status_kehadiran = "Tidak ada data"
                elif checkin is None and checkout is not None:
                    status_kehadiran = "Hadir (checkout only)"
                else:
                    status_kehadiran = "Hadir"
                
                # Status checkout
                if checkout is None:
                    status_pulang = "Tidak scan pulang" if checkin else "-"
                else:
                    status_pulang = "Normal"
                
                # Keterangan
                keterangan = self.generate_keterangan_3a(
                    checkin, checkout, schedule_date, status_masuk
                )
                
                results.append({
                    'Nama': employee_name,
                    'Tanggal': schedule_date.date(),
                    'Kode_Shift': shift_code,
                    'Jabatan': schedule['jabatan'],
                    'Departemen': schedule['departemen'],
                    'id_karyawan': schedule['id_karyawan'],
                    'NIK': schedule['nik'],
                    'Jadwal_Masuk': schedule['jam_masuk'],
                    'Jadwal_Pulang': schedule['jam_pulang'],
                    'Actual_Masuk': checkin.time() if checkin else None,
                    'Actual_Pulang': checkout.time() if checkout else None,
                    'Status_Kehadiran': status_kehadiran,
                    'Status_Masuk': status_masuk,
                    'Status_Pulang': status_pulang,
                    'Keterangan': keterangan
                })
            else:
                # TODO: Implement logic untuk shift lain (1, 2, 3B, dll)
                results.append({
                    'Nama': employee_name,
                    'Tanggal': schedule_date.date(),
                    'Kode_Shift': shift_code,
                    'Jabatan': schedule['jabatan'],
                    'Departemen': schedule['departemen'],
                    'id_karyawan': schedule['id_karyawan'],
                    'NIK': schedule['nik'],
                    'Jadwal_Masuk': schedule['jam_masuk'],
                    'Jadwal_Pulang': schedule['jam_pulang'],
                    'Actual_Masuk': None,
                    'Actual_Pulang': None,
                    'Status_Kehadiran': 'TODO: Implement shift ' + shift_code,
                    'Status_Masuk': '-',
                    'Status_Pulang': '-',
                    'Keterangan': 'Belum diimplementasi'
                })
        
        return pd.DataFrame(results)
    
    def save_to_database(self, result_df: pd.DataFrame):
        """
        Save hasil crosscheck ke tabel croscek
        
        Args:
            result_df: DataFrame hasil crosscheck
        """
        for idx, row in result_df.iterrows():
            # Convert time to string for MySQL
            actual_masuk = None
            actual_pulang = None
            
            if pd.notna(row['Actual_Masuk']):
                actual_masuk = f"{row['Tanggal']} {row['Actual_Masuk']}"
            
            if pd.notna(row['Actual_Pulang']):
                actual_pulang = f"{row['Tanggal']} {row['Actual_Pulang']}"
            
            query = """
                INSERT INTO croscek (
                    Nama, Tanggal, Kode_Shift, Jabatan, Departemen,
                    id_karyawan, NIK, Jadwal_Masuk, Jadwal_Pulang,
                    Actual_Masuk, Actual_Pulang, Status_Kehadiran,
                    Status_Masuk, Status_Pulang
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    Actual_Masuk = VALUES(Actual_Masuk),
                    Actual_Pulang = VALUES(Actual_Pulang),
                    Status_Kehadiran = VALUES(Status_Kehadiran),
                    Status_Masuk = VALUES(Status_Masuk),
                    Status_Pulang = VALUES(Status_Pulang)
            """
            
            params = (
                row['Nama'],
                row['Tanggal'],
                row['Kode_Shift'],
                row['Jabatan'],
                row['Departemen'],
                int(row['id_karyawan']),
                row['NIK'],
                row['Jadwal_Masuk'],
                row['Jadwal_Pulang'],
                actual_masuk,
                actual_pulang,
                row['Status_Kehadiran'],
                row['Status_Masuk'],
                row['Status_Pulang']
            )
            
            self.cursor.execute(query, params)
        
        self.conn.commit()
    
    def run_crosscheck(self, employee_name: str = None,
                       start_date: str = None, end_date: str = None,
                       save_to_db: bool = True) -> pd.DataFrame:
        """
        Main method untuk menjalankan crosscheck
        
        Args:
            employee_name: Filter karyawan (optional)
            start_date: Tanggal mulai 'YYYY-MM-DD' (optional)
            end_date: Tanggal akhir 'YYYY-MM-DD' (optional)
            save_to_db: Save hasil ke database (default True)
            
        Returns:
            DataFrame hasil crosscheck
        """
        try:
            self.connect()
            
            # Fetch data
            print("Fetching schedules...")
            schedule_df = self.fetch_schedules(employee_name, start_date, end_date)
            
            if schedule_df.empty:
                print("No schedule data found!")
                return pd.DataFrame()
            
            print(f"Found {len(schedule_df)} schedule records")
            
            print("Fetching attendance...")
            attendance_df = self.fetch_attendance(employee_name, start_date, end_date)
            
            print(f"Found {len(attendance_df)} attendance records")
            
            # Process crosscheck
            print("Processing crosscheck...")
            result_df = self.process_crosscheck(schedule_df, attendance_df)
            
            # Save to database
            if save_to_db:
                print("Saving to database...")
                self.save_to_database(result_df)
                print("Successfully saved to database!")
            
            return result_df
            
        finally:
            self.disconnect()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',  # Sesuaikan password MySQL Anda
        'database': 'croscek_absen'  # Sesuaikan nama database
    }
    
    # Initialize processor
    processor = AttendanceCrosscheck(db_config)
    
    # Run crosscheck untuk karyawan CUCU SAEPULOH bulan Desember 2025
    result = processor.run_crosscheck(
        employee_name='CUCU SAEPULOH',
        start_date='2025-11-30',
        end_date='2025-12-27',
        save_to_db=True
    )
    
    # Display result
    print("\n" + "="*80)
    print("HASIL CROSSCHECK")
    print("="*80)
    
    # Format time columns properly
    def format_time(t):
        if pd.isna(t):
            return '–'
        if isinstance(t, pd.Timedelta):
            # Convert timedelta to time
            hours = int(t.total_seconds() // 3600)
            minutes = int((t.total_seconds() % 3600) // 60)
            seconds = int(t.total_seconds() % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        if isinstance(t, time):
            return t.strftime('%H:%M:%S')
        return str(t)
    
    # Format output LENGKAP
    display_df = result[[
        'Nama', 'Tanggal', 'Kode_Shift', 'Jabatan', 'Departemen',
        'Jadwal_Masuk', 'Jadwal_Pulang',
        'Actual_Masuk', 'Actual_Pulang',
        'Status_Kehadiran', 'Status_Masuk', 'Status_Pulang',
        'Keterangan'
    ]].copy()
    
    # Format time columns
    display_df['Jadwal_Masuk'] = display_df['Jadwal_Masuk'].apply(format_time)
    display_df['Jadwal_Pulang'] = display_df['Jadwal_Pulang'].apply(format_time)
    display_df['Actual_Masuk'] = display_df['Actual_Masuk'].apply(format_time)
    display_df['Actual_Pulang'] = display_df['Actual_Pulang'].apply(format_time)
    
    display_df.columns = [
        'Nama', 'Tanggal', 'Kode Shift', 'Jabatan', 'Departemen',
        'Jadwal Masuk', 'Jadwal Pulang',
        'Aktual Masuk', 'Aktual Pulang',
        'Status Kehadiran', 'Status Masuk', 'Status Pulang',
        'Keterangan'
    ]
    
    print(display_df.to_string(index=False))
    
    # Also print simplified version (for quick check)
    print("\n" + "="*80)
    print("RINGKASAN (Simplified)")
    print("="*80)
    
    simplified_df = result[[
        'Tanggal', 'Jadwal_Masuk', 'Jadwal_Pulang',
        'Actual_Masuk', 'Actual_Pulang', 
        'Status_Masuk', 'Keterangan'
    ]].copy()
    
    # Format time untuk simplified
    simplified_df['Jadwal_Masuk'] = simplified_df['Jadwal_Masuk'].apply(
        lambda t: '–' if pd.isna(t) else (
            f"{int(t.total_seconds()//3600):02d}:{int((t.total_seconds()%3600)//60):02d}" 
            if isinstance(t, pd.Timedelta) else str(t)
        )
    )
    simplified_df['Jadwal_Pulang'] = simplified_df['Jadwal_Pulang'].apply(
        lambda t: '–' if pd.isna(t) else (
            f"{int(t.total_seconds()//3600):02d}:{int((t.total_seconds()%3600)//60):02d}" 
            if isinstance(t, pd.Timedelta) else str(t)
        )
    )
    simplified_df['Actual_Masuk'] = simplified_df['Actual_Masuk'].apply(
        lambda t: '–' if pd.isna(t) else t.strftime('%H:%M') if isinstance(t, time) else str(t)
    )
    simplified_df['Actual_Pulang'] = simplified_df['Actual_Pulang'].apply(
        lambda t: '–' if pd.isna(t) else t.strftime('%H:%M') if isinstance(t, time) else str(t)
    )
    
    simplified_df.columns = [
        'Tanggal Shift', 'Jadwal Masuk', 'Jadwal Pulang',
        'Check-in', 'Check-out', 
        'Status Masuk', 'Keterangan'
    ]
    
    print(simplified_df.to_string(index=False))
    
    # Export to Excel (optional)
    # result.to_excel('crosscheck_result.xlsx', index=False)
    # print("\nResult exported to crosscheck_result.xlsx")