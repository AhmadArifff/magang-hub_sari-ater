// src/pages/Croscek.jsx
import { useState, useEffect } from "react";
import { UploadCloud, FileSpreadsheet, ArrowRight, Search, X, Plus, Trash2, Download } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";
import ExcelJS from "exceljs";
import { saveAs } from "file-saver";
import logoCompany from "../assets/Image/logo.jpg";


export default function Croscek() {
  const API = "http://127.0.0.1:5000/api";

  // PREVIEW FRONTEND
  const [jadwalPreview, setJadwalPreview] = useState("");
  const [jadwalFile, setJadwalFile] = useState(null);

  const [kehadiranPreview, setKehadiranPreview] = useState("");
  const [kehadiranFile, setKehadiranFile] = useState(null);

  const [croscekData, setCroscekData] = useState([]);

  // LOADING / STATUS
  const [loadingJadwal, setLoadingJadwal] = useState(false);
  const [loadingKehadiran, setLoadingKehadiran] = useState(false);
  const [savingJadwal, setSavingJadwal] = useState(false);
  const [savingKehadiran, setSavingKehadiran] = useState(false);
  const [processing, setProcessing] = useState(false);

  // MODAL PREVIEW CROSCEK
  const [showModal, setShowModal] = useState(false);

  // PAGINATION & SEARCH
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const rowsPerPage = 15; // Tetap gunakan ini, bukan itemsPerPage

  // TAMBAHAN: STATE UNTUK FILTER TANGGAL (diperlukan untuk input tanggal awal dan akhir)
  const [startDate, setStartDate] = useState(''); // State untuk tanggal awal
  const [endDate, setEndDate] = useState(''); // State untuk tanggal akhir

  // TAMBAHAN: STATE UNTUK CRUD JADWAL KARYAWAN (DISESUAIKAN DENGAN KOLOM BARU, nik MANUAL)
  const [jadwalKaryawanList, setJadwalKaryawanList] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [newData, setNewData] = useState({
    nik: "", nama: "", tanggal: "", kode_shift: ""  // Tambahkan nik
  });
  const [showModalTambah, setShowModalTambah] = useState(false);
  const [loadingCRUD, setLoadingCRUD] = useState(false);

  // TAMBAHAN: LOAD DATA JADWAL KARYAWAN
  const loadJadwalKaryawan = async () => {
    try {
      const res = await fetch(`${API}/jadwal-karyawan/list`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setJadwalKaryawanList(data);
    } catch (e) {
      alert("Gagal load data jadwal karyawan: " + e.message);
    }
  };

  // TAMBAHAN: USE EFFECT UNTUK LOAD DATA
  useEffect(() => {
    loadJadwalKaryawan();
  }, []);

  // -----------------------------
  // TABEL UTILITY
  // -----------------------------
  const styleHtmlTable = (html) => {
    return html
      .replace(
        /<table/g,
        `<table class='min-w-full border border-gray-300 text-xs md:text-sm bg-white'`
      )
      .replace(
        /<td/g,
        `<td class='border border-gray-300 px-2 md:px-3 py-2 whitespace-nowrap'`
      )
      .replace(
        /<th/g,
        `<th class='border border-gray-300 bg-gray-100 px-2 md:px-3 py-2 text-center font-semibold'`
      );
  };

  const jsonToHtml = (rows, sheetName = "") => {
    if (!rows || rows.length === 0)
      return `<div class="text-sm text-gray-500">No data</div>`;
    const keys = Object.keys(rows[0]);
    let html = `<div class="mb-2 text-sm font-medium">${sheetName}</div>
      <table class="min-w-full border border-gray-300 text-xs md:text-sm bg-white">
      <thead class="bg-gray-100"><tr>`;
    for (const k of keys) html += `<th class="border px-2 py-1 text-left">${k}</th>`;
    html += `</tr></thead><tbody>`;

    const maxPreview = 500;
    for (let i = 0; i < Math.min(rows.length, maxPreview); i++) {
      const r = rows[i];
      html += `<tr>`;
      for (const k of keys)
        html += `<td class="border px-2 py-1">${String(r[k] ?? "")}</td>`;
      html += `</tr>`;
    }
    if (rows.length > maxPreview) {
      html += `<tr><td class="border px-2 py-1" colspan="${keys.length}">
          Preview truncated — ${rows.length} total rows (showing ${maxPreview})
        </td></tr>`;
    }
    html += `</tbody></table>`;
    return html;
  };

  const attendancePreferredCols = [
    "Tanggal scan",
    "Tanggal",
    "Jam",
    "Nama",
    "PIN",
    "NIP",
    "Verifikasi",
    "I/O",
    "Workcode",
    "SN",
    "Mesin",
    "Jabatan",
    "Departemen",
    "Kantor",
  ];

  function pickAttendanceColumns(rows) {
    if (!rows || rows.length === 0) return [];
    const first = rows[0];
    const present = new Set(Object.keys(first).map((k) => String(k).trim()));
    const cols = [];
    for (const p of attendancePreferredCols) {
      if (present.has(p)) cols.push(p);
    }
    for (const k of Object.keys(first)) {
      if (k && !k.toString().startsWith("__EMPTY") && !cols.includes(k))
        cols.push(k);
    }
    return cols;
  }

  function cleanRowsWithCols(rows, cols) {
    return rows.map((r) => {
      const obj = {};
      for (const c of cols) obj[c] = r[c] ?? "";
      return obj;
    });
  }

  // -----------------------------------------
  // UPLOAD + PREVIEW JADWAL
  // -----------------------------------------
  async function handleUploadJadwal(e) {
    const file = e.target.files[0];
    if (!file) return;

    setLoadingJadwal(true);
    setJadwalFile(file);

    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });

      let html = "";
      for (const sheetName of workbook.SheetNames) {
        const sheet = workbook.Sheets[sheetName];
        let sheetHtml = "";

        try {
          sheetHtml = XLSX.utils.sheet_to_html(sheet);
          sheetHtml =
            `<div class="mb-2 font-semibold">${sheetName}</div>` +
            styleHtmlTable(sheetHtml);
        } catch {
          const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });
          sheetHtml = jsonToHtml(rows, sheetName);
        }

        html += sheetHtml;
      }

      setJadwalPreview(html);
    } catch (err) {
      alert("Gagal membaca file jadwal");
    }

    setLoadingJadwal(false);
  }
  

  // Tambahkan state untuk bulan yang dipilih (0-11, default bulan sekarang)
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth());

  // Fungsi untuk handle perubahan bulan
  const handleMonthChange = (e) => {
    setSelectedMonth(parseInt(e.target.value));
  };

  // EXPORT TEMPLATE EXCEL UNTUK JADWAL (diperbaiki dengan aoa_to_sheet untuk memastikan data muncul)
  const exportTemplateJadwal = () => {
    const wb = XLSX.utils.book_new();

    // Gunakan bulan yang dipilih, tahun sekarang
    const month = selectedMonth; // 0-11
    const year = new Date().getFullYear();

    // Nama bulan (dalam bahasa Indonesia)
    const monthNames = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
    const monthText = `${monthNames[month]} ${year}`;

    // Total hari di bulan ini
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Mapping hari singkat (Sabtu=SB, Minggu=MG, Senin=SN, Selasa=SL, Rabu=RB, Kamis=KM, Jumat=JM)
    const dayShort = ["MG", "SN", "SL", "RB", "KM", "JM", "SB"];

    // Buat array data untuk sheet (baris 0-based)
    const data = [];

    // Baris 0: SCHEDULE (akan di-merge A1:AH1)
    data.push(["SCHEDULE", ...Array(33).fill("")]);

    // Baris 1: Bulan & tahun (akan di-merge A2:AH2)
    data.push([monthText, ...Array(33).fill("")]);

    // Baris 2: Kosong (spacing)
    data.push(Array(34).fill(""));

    // Baris 3: Header atas (NO, ID ABSEN, NAMA, lalu hari-hari)
    const headerRow3 = ["NO", "ID ABSEN", "NAMA"];
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d);
      const dayCode = dayShort[date.getDay()];
      headerRow3.push(dayCode);
    }
    // Pad dengan kosong jika kurang dari 34 kolom
    while (headerRow3.length < 34) {
      headerRow3.push("");
    }
    data.push(headerRow3);

    // Baris 4: Header bawah (kosong untuk NO/ID ABSEN/NAMA, lalu tanggal)
    const headerRow4 = ["", "", ""];
    for (let d = 1; d <= daysInMonth; d++) {
      headerRow4.push(d);
    }
    while (headerRow4.length < 34) {
      headerRow4.push("");
    }
    data.push(headerRow4);

    // Baris 5: Kosong untuk data record (baris 6 di Excel)
    data.push(Array(34).fill(""));

    // Buat worksheet dari array
    const ws = XLSX.utils.aoa_to_sheet(data);

    // Set merges
    ws['!merges'] = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: 33 } }, // A1:AH1 = SCHEDULE
      { s: { r: 1, c: 0 }, e: { r: 1, c: 33 } }, // A2:AH2 = Month
      { s: { r: 3, c: 0 }, e: { r: 4, c: 0 } }, // A4:A5 = NO
      { s: { r: 3, c: 1 }, e: { r: 4, c: 1 } }, // B4:B5 = ID ABSEN
      { s: { r: 3, c: 2 }, e: { r: 4, c: 2 } }, // C4:C5 = NAMA
    ];

    // Lebar kolom
    ws['!cols'] = Array(34).fill({ wch: 5 });

    XLSX.utils.book_append_sheet(wb, ws, "Template Jadwal");
    XLSX.writeFile(wb, `template_jadwal_karyawan_Bulan_ke-${month + 1}-${year}.xlsx`);
  };

  async function saveJadwal() {
    if (!jadwalFile) return alert("Upload file dulu");

    setSavingJadwal(true);
    try {
      const form = new FormData();
      form.append("file", jadwalFile);

      const res = await fetch(`${API}/import-jadwal-karyawan`, {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "Gagal menyimpan jadwal");
        return;
      }
      alert(data.message || "Berhasil menyimpan jadwal");
      loadJadwalKaryawan(); // Reload data setelah save
    } catch (err) {
      alert("Error saat menyimpan jadwal: " + err.message);
    }
    setSavingJadwal(false);
  }


  // -----------------------------------------
  // UPLOAD + PREVIEW KEHADIRAN
  // -----------------------------------------
  async function handleUploadKehadiran(e) {
    const file = e.target.files[0];
    if (!file) return;

    setLoadingKehadiran(true);
    setKehadiranFile(file);

    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });

      let htmlAll = "";

      for (const sheetName of workbook.SheetNames) {
        const sheet = workbook.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(sheet, { defval: "" });
        const cols = pickAttendanceColumns(rows);
        const cleaned = cleanRowsWithCols(rows, cols);

        htmlAll += jsonToHtml(cleaned, sheetName);
      }

      setKehadiranPreview(htmlAll);
    } catch (err) {
      alert("Gagal membaca file kehadiran");
    }

    setLoadingKehadiran(false);
  }

  async function saveKehadiran() {
      if (!kehadiranFile) return alert("Upload file dulu!");

      setSavingKehadiran(true);

      try {
          const form = new FormData();
          form.append("file", kehadiranFile);

          const res = await fetch(`${API}/import-kehadiran`, {
              method: "POST",
              body: form,
          });

          const data = await res.json();

          // CEK STATUS RESPONSE
          if (!res.ok) {
              alert(data.error || "Gagal menyimpan kehadiran!");
              setSavingKehadiran(false);
              return;
          }

          // Status OK → tampilkan pesan sukses
          alert(data.message || "Kehadiran berhasil disimpan");
      } catch (e) {
          alert("Error saat menyimpan kehadiran: " + e.message);
      }

      setSavingKehadiran(false);
  }


  // EXPORT TEMPLATE EXCEL UNTUK KEHADIRAN (diperbaiki sesuai spesifikasi)
  const exportTemplateKehadiran = () => {
    const wb = XLSX.utils.book_new();

    // Header kolom sesuai spesifikasi (urutan: Tanggal scan, Tanggal, Jam, PIN, NIP, Nama, Jabatan, Departemen, Kantor, Verifikasi, I/O, Workcode, SN, Mesin)
    const headers = ["Tanggal scan", "Tanggal", "Jam", "PIN", "NIP", "Nama", "Jabatan", "Departemen", "Kantor", "Verifikasi", "I/O", "Workcode", "SN", "Mesin"];

    // Buat array data untuk sheet (baris 0-based)
    const data = [];

    // Baris 0: Kosong (Excel baris 1)
    data.push(Array(14).fill(""));

    // Baris 1: Header (Excel baris 2, A2:N2)
    data.push(headers);

    // Baris 2 sampai 4: Kosong (Excel baris 3-5)
    for (let i = 0; i < 3; i++) {
      data.push(Array(14).fill(""));
    }

    // Baris 5: Kosong untuk data record (Excel baris 6, A6:N6)
    data.push(Array(14).fill(""));

    // Buat worksheet dari array
    const ws = XLSX.utils.aoa_to_sheet(data);

    // Style untuk header (baris 1, kolom 0-13, center, dan jika library mendukung: gray fill, white font, bold)
    const headerStyle = {
      fill: { fgColor: { rgb: "808080" } },
      font: { color: { rgb: "FFFFFF" }, bold: true },
      alignment: { horizontal: "center", vertical:"middle" }
    };

    // Terapkan style ke header (baris 1, kolom 0-13)
    headers.forEach((_, index) => {
      const cell = XLSX.utils.encode_cell({ r: 1, c: index });
      if (ws[cell]) ws[cell].s = headerStyle;
    });

    // Lebar kolom
    ws['!cols'] = headers.map(() => ({ wch: 15 }));

    XLSX.utils.book_append_sheet(wb, ws, "Template Kehadiran");
    XLSX.writeFile(wb, "template_kehadiran.xlsx");
  };


  // TAMBAHAN: STATE UNTUK KEHADIRAN (DINAMIS DARI DATA)
  const [selectedMonthKehadiran, setSelectedMonthKehadiran] = useState(null);
  const [selectedYearKehadiran, setSelectedYearKehadiran] = useState(null);
  const [availablePeriods, setAvailablePeriods] = useState([]);
  const [loadingPeriods, setLoadingPeriods] = useState(false);

  // LOAD PERIODE
  const loadAvailablePeriods = async () => {
    setLoadingPeriods(true);
    try {
      const res = await fetch(`${API}/kehadiran/available-periods`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAvailablePeriods(data.periods || []);

      // Auto-select periode terbaru
      if (data.periods?.length > 0) {
        setSelectedMonthKehadiran(data.periods[0].bulan);
        setSelectedYearKehadiran(data.periods[0].tahun);
      }
    } catch (e) {
      alert("Gagal load periode kehadiran: " + e.message);
    }
    setLoadingPeriods(false);
  };

  useEffect(() => {
    loadAvailablePeriods();
  }, []);

  // HAPUS PERIODE
  const handleDeleteKehadiranPeriod = async () => {
    if (!selectedMonthKehadiran || !selectedYearKehadiran) {
      alert("Silakan pilih periode terlebih dahulu.");
      return;
    }

    if (!window.confirm(
        `Yakin ingin menghapus semua data kehadiran untuk ${selectedMonthKehadiran}/${selectedYearKehadiran}?`
    )) return;

    try {
      const res = await fetch(`${API}/kehadiran/delete-period`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bulan: selectedMonthKehadiran,
          tahun: selectedYearKehadiran,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Gagal hapus periode");
        return;
      }

      alert(data.message);
      loadAvailablePeriods();
    } catch (e) {
      alert("Error saat hapus periode: " + e.message);
    }
  };

  // TAMBAHAN: STATE UNTUK PROGRESS BAR POP-UP
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressInterval, setProgressInterval] = useState(null); // Untuk menyimpan ID interval

  async function prosesCroscek() {
    setProcessing(true);
    setShowProgressModal(true); // Tampilkan modal progress
    setProgress(0); // Reset progress

    // Simulasi progress: Naik 10% setiap 500ms (total ~5 detik untuk mencapai 100%)
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev; // Jangan lewati 90% sampai data selesai
        return prev + 10;
      });
    }, 500);
    setProgressInterval(interval);

    try {
      const res = await fetch(`${API}/croscek`);
      // const data = await res.json();
      // setCroscekData(data.data || []);
      const data = await res.json();
      const rows = data.data || [];
      // buat uid stabil: gunakan id jika ada, kalau tidak pakai kombinasi Nama|Tanggal|Kode_Shift atau index
      const rowsWithUid = rows.map((r, idx) => {
        const baseId = r.id ?? `${r.Nama}__${r.Tanggal}__${r.Kode_Shift}`;
        return { __uid: baseId, ...r };
      });
      setCroscekData(rowsWithUid);
      setShowModal(true); // Tampilkan modal preview setelah selesai
      // setReasonMap({});
    } catch (err) {
      alert("Gagal memproses croscek");
    }

    // Set progress ke 100% dan tutup modal setelah delay
    setProgress(100);
    clearInterval(interval); // Hentikan interval
    setTimeout(() => {
      setShowProgressModal(false);
      setProcessing(false);
    }, 1000); // Delay 1 detik untuk menampilkan 100%
  }


  // -----------------------------------------
  // PAGINATION + SEARCH + FILTER TANGGAL
  // -----------------------------------------
  // Filter data berdasarkan search dan tanggal
  const filteredData = croscekData.filter(row => {
    const matchesSearch = !search || row.Nama.toLowerCase().includes(search.toLowerCase()) || row.Tanggal.includes(search);
    const rowDate = new Date(row.Tanggal); // Asumsikan Tanggal dalam format YYYY-MM-DD
    const start = startDate ? new Date(startDate) : null;
    const end = endDate ? new Date(endDate) : null;
    const matchesDate = (!start || rowDate >= start) && (!end || rowDate <= end);
    return matchesSearch && matchesDate;
  });

  // Pagination untuk filteredData
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  const paginated = filteredData.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  // TAMBAHAN: CRUD HANDLERS UNTUK JADWAL KARYAWAN (DISESUAIKAN DENGAN nik MANUAL)
  const handleCreate = async () => {
    if (!newData.nama || !newData.kode_shift || !newData.tanggal)
      return alert("Lengkapi data dulu, masa nambah jadwal tapi kosong? 😄");

    setLoadingCRUD(true);
    try {
      await fetch(`${API}/jadwal-karyawan/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newData),
      });
      setShowModalTambah(false);
      setNewData({ nik: "", nama: "", tanggal: "", kode_shift: "" });
      loadJadwalKaryawan();
    } catch (e) {
      alert("Gagal tambah: " + e.message);
    } finally {
      setLoadingCRUD(false);
    }
  };

  const [listKaryawan, setListKaryawan] = useState([]);
  const [showNamaDropdown, setShowNamaDropdown] = useState(false);
  useEffect(() => {
    const handleClick = (e) => {
      // Periksa apakah klik di dalam dropdown atau input
      if (!e.target.closest('.nama-dropdown') && !e.target.closest('.nama-input')) {
        setShowNamaDropdown(false);
      }
    };
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  const [showShiftDropdown, setShowShiftDropdown] = useState(false);
  useEffect(() => {
    const handleClick = (e) => {
      // Periksa apakah klik di dalam dropdown atau input
      if (!e.target.closest('.shift-dropdown') && !e.target.closest('.shift-input')) {
        setShowShiftDropdown(false);
      }
    };
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, []);

  const loadListKaryawan = async () => {
    try {
      const res = await fetch(`${API}/karyawan/list/nama`);
      const data = await res.json();

      console.log("DEBUG LIST KARYAWAN:", data);

      setListKaryawan(
        Array.isArray(data)
          ? data
          : Array.isArray(data.data)
          ? data.data
          : []
      );
    } catch (e) {
      alert("Gagal load list karyawan: " + e.message);
    }
  };

  // pastikan nama karyawan unik
  const uniqueKaryawan = Array.isArray(listKaryawan)
    ? Array.from(new Map(
        listKaryawan
          .filter(x => x.nama)     // pastikan nama tidak null
          .map(item => [item.nama, item])
      ).values())
    : [];


  useEffect(() => {
    loadListKaryawan();
  }, []);

  const handleEditChange = (nik, field, value) => {
    setJadwalKaryawanList(prev => prev.map(item => (item.no === nik ? { ...item, [field]: value } : item)));
  };

  const handleUpdate = async (nik) => {
    const data = jadwalKaryawanList.find(item => item.no === nik);
    if (!data) {
      alert("Data tidak ditemukan");
      return;
    }
    try {
      setLoadingCRUD(true);
      const res = await fetch(`${API}/jadwal-karyawan/update/${nik}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const json = await res.json();
        alert("Gagal update: " + (json.error || res.statusText));
        return;
      }
      setEditingId(null);
      await loadJadwalKaryawan();
    } catch (e) {
      alert("Update gagal: " + e.message);
    } finally {
      setLoadingCRUD(false);
    }
  };

  const [kodeShiftOptions, setKodeShiftOptions] = useState([]);
  const [searchShift, setSearchShift] = useState("");

  const filteredShiftOptions = kodeShiftOptions.filter(k =>
    k.toLowerCase().includes(searchShift.toLowerCase())
  );


  const loadKodeShiftOptions = async () => {
    try {
      const res = await fetch(`${API}/informasi-jadwal/list`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // misal backend mengembalikan array objek { kode_shift: "A", keterangan: "Shift Pagi" }
      setKodeShiftOptions(data.map(item => item.kode_shift));
    } catch (e) {
      alert("Gagal load kode shift: " + e.message);
    }
  };

  useEffect(() => {
    loadKodeShiftOptions();
  }, []);




  const handleDelete = async (nik) => {
    if (!confirm("Hapus data ini?")) return;
    try {
      const res = await fetch(`${API}/jadwal-karyawan/delete/${nik}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json();
        alert("Gagal hapus: " + (json.error || res.statusText));
        return;
      }
      await loadJadwalKaryawan();
    } catch (e) {
      alert("Hapus gagal: " + e.message);
    }
  };

  // TAMBAHAN: FILTER & PAGINATION UNTUK TABEL JADWAL KARYAWAN
  const [searchJadwal, setSearchJadwal] = useState("");
  const [pageJadwal, setPageJadwal] = useState(1);
  const rowsPerPageJadwal = 10;

  // 📌 FILTER BULAN–TAHUN UNTUK JADWAL KARYAWAN
  const [selectedMonthJadwal, setSelectedMonthJadwal] = useState(null);
  const [selectedYearJadwal, setSelectedYearJadwal] = useState(null);
  const [availablePeriodsJadwal, setAvailablePeriodsJadwal] = useState([]);

  // 🔥 Extract bulan-tahun dari tanggal jadwal yang ada
  const extractPeriodsJadwal = (list) => {
    const set = new Set();

    list.forEach(item => {
      if (!item.tanggal) return;
      const d = new Date(item.tanggal);
      const bulan = d.getMonth() + 1;
      const tahun = d.getFullYear();
      set.add(`${bulan}-${tahun}`);
    });

    const periods = Array.from(set).map(str => {
      const [bulan, tahun] = str.split("-").map(Number);
      return { bulan, tahun };
    });

    // urutkan terbaru dulu
    periods.sort((a, b) => b.tahun - a.tahun || b.bulan - a.bulan);

    setAvailablePeriodsJadwal(periods);

    if (periods.length > 0) {
      setSelectedMonthJadwal(periods[0].bulan);
      setSelectedYearJadwal(periods[0].tahun);
    }
  };

  useEffect(() => {
    loadJadwalKaryawan();
  }, []);

  useEffect(() => {
    extractPeriodsJadwal(jadwalKaryawanList);
  }, [jadwalKaryawanList]);



  const filteredJadwal = jadwalKaryawanList.filter(item => {
    if (!selectedMonthJadwal || !selectedYearJadwal) return true;

    const d = new Date(item.tanggal);
    const bulan = d.getMonth() + 1;
    const tahun = d.getFullYear();

    return bulan === selectedMonthJadwal && tahun === selectedYearJadwal;
  }).filter(item => {
    const keyword = searchJadwal.toLowerCase();
    return Object.values(item).some(val =>
      String(val).toLowerCase().includes(keyword)
    );
  });


  const totalPagesJadwal = Math.ceil(filteredJadwal.length / rowsPerPageJadwal);
  const paginatedJadwal = filteredJadwal.slice((pageJadwal - 1) * rowsPerPageJadwal, pageJadwal * rowsPerPageJadwal);
  

  const colsJadwal = ["nik", "nama", "tanggal", "kode_shift"];

  // format jam ke HH:MM:SS untuk actual masuk/pulang
  const formatJam = (val) => {
    if (!val) return "";
    const d = new Date(val);
    if (isNaN(d)) return val; 
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
  };

  const [reasonMap, setReasonMap] = useState({});


  // Export Crocek Absensi (filtered data)
  const exportFilteredData = () => {
    const wb = XLSX.utils.book_new();

    const headers = [
      "Nama", "Tanggal", "Kode Shift", "Jabatan", "Departemen",
      "Jadwal Masuk", "Jadwal Pulang", "Aktual Masuk", "Aktual Pulang",
      "Keterangan Jadwal", "Status Kehadiran", "Status Masuk", "Status Pulang"
    ];

    // Format tanggal ke dd-mm-yyyy
    const formatTanggal = (tgl) => {
      if (!tgl) return "";
      const d = new Date(tgl);
      if (isNaN(d)) return tgl;
      const day = String(d.getDate()).padStart(2, "0");
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const year = d.getFullYear();
      return `${day}-${month}-${year}`;
    };

    const data = [headers];

    filteredData.forEach((row, i) => {
      const uid = row.__uid ?? row.id ?? i;
      const finalStatus =
        row.Status_Kehadiran === "Tidak Hadir"
          ? (reasonMap[uid] || "Tidak Hadir")
          : row.Status_Kehadiran;

      data.push([
        row.Nama,
        formatTanggal(row.Tanggal),
        row.Kode_Shift,
        row.Jabatan,
        row.Departemen,
        row.Jadwal_Masuk,
        row.Jadwal_Pulang,
        formatJam(row.Actual_Masuk),
        formatJam(row.Actual_Pulang),
        row.Keterangan,
        finalStatus,
        row.Status_Masuk,
        row.Status_Pulang
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(data);
    ws['!cols'] = headers.map(() => ({ wch: 15 }));

    XLSX.utils.book_append_sheet(wb, ws, "Hasil Croscek");

    XLSX.writeFile(
      wb,
      `hasil_croscek_${startDate || 'all'}_sd_${endDate || 'all'}.xlsx`
    );
  };



  // 🔥 HANDLER UNTUK KOSONGKAN SEMUA DATA JADWAL KARYAWAN
  const handleKosongkanJadwal = async () => {
    if (!window.confirm("Yakin ingin menghapus SEMUA data jadwal karyawan?")) return;

    try {
      const res = await fetch(`${API}/jadwal-karyawan/clear`, {
        method: "POST",
      });

      let result = {};
      try {
        result = await res.json();
      } catch (e) {
        console.warn("Response bukan JSON:", e);
      }

      if (res.ok) {
        alert(result.message || "Semua jadwal berhasil dikosongkan!");
        loadJadwalKaryawan();
      } else {
        alert("Gagal mengosongkan: " + (result.error || "Unknown error"));
      }
    } catch (err) {
      alert("Terjadi kesalahan: " + err.message);
    }
  };


  // Helper: convert imported image URL -> base64 (ExcelJS expects base64)
  async function imageToBase64(path) {
    const resp = await fetch(path);
    const blob = await resp.blob();
    return await new Promise((res, rej) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrl = reader.result;
        // return base64 without prefix
        res(dataUrl.split(",")[1]);
      };
      reader.onerror = rej;
      reader.readAsDataURL(blob);
    });
  }

  // === Format Tanggal Indonesia Per-Hari ===
  function formatDateIdPerDay(date) {
    const bulan = ["Januari","Februari","Maret","April","Mei","Juni","Juli","Agustus","September","Oktober","November","Desember"];
    const d = new Date(date);
    if (isNaN(d)) return "";
    const dayName = d.toLocaleDateString("id-ID", { weekday: "long" });
    return `Periode : ${dayName}, ${String(d.getDate()).padStart(2,"0")} ${bulan[d.getMonth()]} ${d.getFullYear()}`;
  }

  // helper: format time hh:mm dari string/datetime
  function formatTime(t) {
    if (!t) return "";
    try {
      const d = new Date(t);
      if (isNaN(d)) {
        // maybe t is TIME like "15:00:00"
        const parts = String(t).split(":");
        if (parts.length >= 2) return `${parts[0].padStart(2,"0")}:${parts[1].padStart(2,"0")}`;
        return String(t);
      }
      return `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
    } catch(e) { return String(t); }
  }

  // === FULL UPDATE Export Rekap Perhari (dengan blok TERLAMBAT) ===
  async function exportRekapPerhari() {
    try {
      if (!filteredData || filteredData.length === 0) {
        alert("Tidak ada data untuk diexport.");
        return;
      }

      const dataWithIndex = filteredData.map((r, idx) => ({ ...r, _idx: idx }));

      // Pisahkan filter untuk bagian utama (sakit/izin/alpa/tidak hadir) dan terlambat
      const filteredRekapUtama = dataWithIndex.filter(row => {
        const status = (row.Status_Kehadiran || "").toUpperCase();
        const selected = reasonMap?.[row.__uid];
        // hanya selected atau status sakit/izin/alpa/tidak hadir, tanpa telat
        // if (selected || ["ALPA","SAKIT","IZIN","TIDAK HADIR","DINAS LUAR"].includes(status)) {
        //   return true;
        // }
        // return false;
        if (
          ["ALPA","SAKIT","IZIN","TIDAK HADIR","DINAS LUAR"].includes(status)
        ) {
          return true;
        }

        // jika ada selected, pastikan BUKAN TL & BUKAN PA
        if (selected) {
          const hasAbsenceReason =
            selected.ALPA ||
            selected.SAKIT ||
            selected.IZIN ||
            selected.TIDAK_HADIR ||
            selected.DINAS_LUAR;

          return Boolean(hasAbsenceReason);
        }

        return false;
      });

      const filteredRekapTerlambat = dataWithIndex.filter(row => {
        const masuk = (row.Status_Masuk || "").toUpperCase();
        // hanya yang telat
        if (masuk.includes("TELAT") || masuk.includes("TERLAMBAT")) {
          return true;
        }
        return false;
      });

      const getReason = (row) => reasonMap?.[row.__uid] || row.Status_Kehadiran || "";
      const getNik = (r) => (r.NIP || r.nip || r.NIK || r.id_karyawan || "") + "";

      // group per tanggal untuk utama dan terlambat terpisah
      const rowsByDateUtama = {};
      for (const r of filteredRekapUtama) {
        const dt = new Date(r.Tanggal);
        const key = isNaN(dt) ? String(r.Tanggal) : dt.toISOString().slice(0,10);
        if (!rowsByDateUtama[key]) rowsByDateUtama[key] = [];
        rowsByDateUtama[key].push(r);
      }

      const rowsByDateTerlambat = {};
      for (const r of filteredRekapTerlambat) {
        const dt = new Date(r.Tanggal);
        const key = isNaN(dt) ? String(r.Tanggal) : dt.toISOString().slice(0,10);
        if (!rowsByDateTerlambat[key]) rowsByDateTerlambat[key] = [];
        rowsByDateTerlambat[key].push(r);
      }

      const dateKeys = [...new Set([
        ...Object.keys(rowsByDateUtama || {}),
        ...Object.keys(rowsByDateTerlambat || {})
      ])]
      .filter(Boolean)      // hilangkan null/undefined/"" 
      .sort();

      const hasRange = startDate && endDate;

      const wb = new ExcelJS.Workbook();

      // create one sheet per day (always)
      const createSheetForRows = async (sheetName, rowsForSheetUtama, rowsForSheetTerlambat, currentDateKey) => {
        const ws = wb.addWorksheet(sheetName);

        ws.columns = [
          { key: "A", width: 6 }, { key: "B", width: 30 }, { key: "C", width: 18 },
          { key: "D", width: 20 }, { key: "E", width: 18 }, { key: "F", width: 8 },
          { key: "G", width: 28 }, { key: "H", width: 10 }, { key: "I", width: 10 }
        ];

        // logo + header (sama style)
        try {
          const base64 = await imageToBase64(logoCompany);
          const imageId = wb.addImage({ base64, extension: "jpg" });
          ws.mergeCells("A1:A2");
          ws.addImage(imageId, { tl: { col: 0.2, row: 0.2 }, ext: { width: 40, height: 40 } });
          ws.getRow(1).height = 18;
          ws.getRow(2).height = 18;
        } catch (e) { console.warn("Gagal load logo:", e); }

        ws.mergeCells("B1:I1");
        ws.getCell("B1").value = { richText:[
          { text:"Sari Ater ", font:{ name:"Times New Roman", size:9, color:{ argb:"FF23FF23" }, underline:true } },
          { text:"Hot Spring Ciater", font:{ name:"Mistral", size:9, color:{ argb:"FFFF0000" }, italic:true, underline:true } }
        ]};
        ws.getCell("B1").alignment = { vertical:"middle", horizontal:"left" };

        ws.mergeCells("B2:I2");
        ws.getCell("B2").value = "Human Resources Department";
        ws.getCell("B2").font = { name:"Arial", size:8, bold:true };
        ws.getCell("B2").alignment = { vertical:"middle", horizontal:"left" };

        ws.mergeCells("A3:I3");
        ws.getCell("A3").value = "REKAPITULASI HARIAN";
        ws.getCell("A3").font = { name:"Times New Roman", size:9, bold:true, italic:true };
        ws.getCell("A3").alignment = { vertical:"middle", horizontal:"center" };

        ws.mergeCells("A4:I4");
        ws.getCell("A4").value = "( Sakit, Izin, Alpa & Terlambat masuk kerja )";
        ws.getCell("A4").font = { name:"Times New Roman", size:9, italic:true };
        ws.getCell("A4").alignment = { vertical:"middle", horizontal:"center" };

        // periode (selalu per-hari)
        ws.mergeCells("A5:I5");
        ws.getCell("A5").value = formatDateIdPerDay(currentDateKey);
        ws.getCell("A5").font = { name:"Times New Roman", size:9, bold:true, italic:true };
        ws.getCell("A5").alignment = { vertical:"middle", horizontal:"center" };

        let curRow = 6;

        // Group by shift untuk bagian utama
        const groupedUtama = {};
        for (const r of rowsForSheetUtama) {
          const key = r.Kode_Shift ?? "UNSPEC";
          if (!groupedUtama[key]) groupedUtama[key] = [];
          groupedUtama[key].push(r);
        }

        const shiftsUtama = Object.keys(groupedUtama).sort((a,b)=> {
          const na = Number(a), nb = Number(b);
          if (!isNaN(na) && !isNaN(nb)) return na-nb;
          return a.localeCompare(b);
        });

        // --- REKAP UTAMA (Izin/Sakit/Alpa/Tidak Hadir) ---
        for (const shift of shiftsUtama) {
          // shift header (merge A-I)
          ws.mergeCells(`A${curRow}:I${curRow}`);
          ws.getCell(`A${curRow}`).value = `Shift : ${shift}`;
          ws.getCell(`A${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
          ws.getCell(`A${curRow}`).alignment = { horizontal:"left", vertical:"middle" };
          ws.getCell(`A${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`A${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
          curRow++;

          // header kolom: No, Nama, NIK, Jabatan, Dept, Shift, Keterangan(merge G-I)
          // A-F headers
          const headersLeft = ["No","Nama Karyawan","NIK","Jabatan","Dept","Shift"];
          for (let i=0;i<headersLeft.length;i++){
            const col = String.fromCharCode(65+i);
            ws.getCell(`${col}${curRow}`).value = headersLeft[i];
            ws.getCell(`${col}${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
            ws.getCell(`${col}${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
            ws.getCell(`${col}${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`${col}${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
          }
          // Keterangan header merged G-I
          ws.mergeCells(`G${curRow}:I${curRow}`);
          ws.getCell(`G${curRow}`).value = "Keterangan";
          ws.getCell(`G${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
          ws.getCell(`G${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
          ws.getCell(`G${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
          ws.getCell(`G${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

          curRow++;

          // data rows
          const rows = groupedUtama[shift];
          for (let i=0;i<rows.length;i++){
            const r = rows[i];
            const nomor = i+1;

            // first fill A-F normally
            const leftVals = [
              nomor,
              r.Nama ?? "",
              getNik(r),
              r.Jabatan ?? "",
              r.Departemen ?? "",
              r.Kode_Shift ?? ""
            ];
            for (let ci=0; ci<leftVals.length; ci++){
              const col = String.fromCharCode(65+ci);
              ws.getCell(`${col}${curRow}`).value = leftVals[ci];
              ws.getCell(`${col}${curRow}`).font = { name:"Times New Roman", size:9 };
              ws.getCell(`${col}${curRow}`).alignment = { horizontal: "center", vertical:"middle" };
              ws.getCell(`${col}${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            }

            // merge G-I for keterangan value
            ws.mergeCells(`G${curRow}:I${curRow}`);
            // const keteranganVal = (r.Status_Kehadiran === "Tidak Hadir") ? ( getReason(r) || "Tidak Hadir" ) : (r.Status_Kehadiran || "");
            let keteranganVal = "";
            if (["ALPA","SAKIT","IZIN","TIDAK HADIR","DINAS LUAR"].includes(
              (r.Status_Kehadiran || "").toUpperCase()
            )) {
              keteranganVal = r.Status_Kehadiran;
            }
            ws.getCell(`G${curRow}`).value = keteranganVal;
            ws.getCell(`G${curRow}`).font = { name:"Times New Roman", size:9 };
            ws.getCell(`G${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
            // set borders for merged region (G,H,I)
            ["G","H","I"].forEach(c => {
              ws.getCell(`${c}${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            });

            curRow++;
          }

          curRow++; // spacing antar shift
        }

        // === setelah rekap utama -> lewati 2 baris sebelum blok terlambat ===
        curRow += 2;

        // --- BLOK DATA KARYAWAN TERLAMBAT ---
        if (rowsForSheetTerlambat.length > 0) {
          // header title
          ws.mergeCells(`A${curRow}:I${curRow}`);
          ws.getCell(`A${curRow}`).value = "Data Karyaman yang terlambat masuk kerja";
          ws.getCell(`A${curRow}`).font = { name:"Times New Roman", size:11, bold:true, italic:true };
          ws.getCell(`A${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
          curRow++;

          // periode under title (same style requested)
          ws.mergeCells(`A${curRow}:I${curRow}`);
          ws.getCell(`A${curRow}`).value = formatDateIdPerDay(currentDateKey);
          ws.getCell(`A${curRow}`).font = { name:"Times New Roman", size:11, bold:true, italic:true };
          ws.getCell(`A${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
          curRow++;

          // group late rows by shift
          const lateGroup = {};
          for (const r of rowsForSheetTerlambat) {
            const key = r.Kode_Shift ?? "UNSPEC";
            if (!lateGroup[key]) lateGroup[key] = [];
            lateGroup[key].push(r);
          }
          const lateShifts = Object.keys(lateGroup).sort();

          for (const sh of lateShifts) {
            // shift header
            ws.mergeCells(`A${curRow}:I${curRow}`);
            ws.getCell(`A${curRow}`).value = `Shift : ${sh}`;
            ws.getCell(`A${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
            ws.getCell(`A${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`A${curRow}`).alignment = { horizontal:"left", vertical:"middle" };
            ws.getCell(`A${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
            curRow++;

            // Header 2-bar rows:
            // Merge A-D vertically (2 rows)
            ws.mergeCells(`A${curRow}:A${curRow+1}`);
            ws.mergeCells(`B${curRow}:B${curRow+1}`);
            ws.mergeCells(`C${curRow}:C${curRow+1}`);
            ws.mergeCells(`D${curRow}:D${curRow+1}`);
            ws.getCell(`A${curRow}`).value = "No";
            ws.getCell(`B${curRow}`).value = "Nama Karyawan";
            ws.getCell(`C${curRow}`).value = "NIK";
            ws.getCell(`D${curRow}`).value = "Jabatan";
            ["A","B","C","D"].forEach(col => {
              ws.getCell(`${col}${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
              ws.getCell(`${col}${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
              // also put borders for both rows of merge
              ws.getCell(`${col}${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
              ws.getCell(`${col}${curRow+1}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
              ws.getCell(`${col}${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
            });

            // E-G row1 merged as "Jadwal Kerja"
            ws.mergeCells(`E${curRow}:G${curRow}`);
            ws.getCell(`E${curRow}`).value = "Jadwal Kerja";
            ws.getCell(`E${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
            ws.getCell(`E${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
            ws.getCell(`E${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`E${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

            // Under E-G row+1: Dept, Shift, Jam Cek In
            ws.getCell(`E${curRow+1}`).value = "Dept";
            ws.getCell(`F${curRow+1}`).value = "Shift";
            ws.getCell(`G${curRow+1}`).value = "Jam Cek In";
            ["E","F","G"].forEach(col => {
              ws.getCell(`${col}${curRow+1}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
              ws.getCell(`${col}${curRow+1}`).alignment = { horizontal:"center", vertical:"middle" };
              ws.getCell(`${col}${curRow+1}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
              ws.getCell(`${col}${curRow+1}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
            });

            // H header merged vertical (Actual)
            ws.mergeCells(`H${curRow}:H${curRow+1}`);
            ws.getCell(`H${curRow}`).value = "Actual";
            ws.getCell(`H${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
            ws.getCell(`H${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
            ws.getCell(`H${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`H${curRow+1}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`H${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
            
            // I header merged vertical (Durasi Terlambat)
            ws.mergeCells(`I${curRow}:I${curRow+1}`);
            ws.getCell(`I${curRow}`).value = "Durasi Terlambat";
            ws.getCell(`I${curRow}`).font = { name:"Times New Roman", size:9, bold:true, italic:true };
            ws.getCell(`I${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
            ws.getCell(`I${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`I${curRow+1}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
            ws.getCell(`I${curRow}`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

            // Update column widths for better layout
            ws.columns = [
              { key: "A", width: 6 }, { key: "B", width: 30 }, { key: "C", width: 18 },
              { key: "D", width: 20 }, { key: "E", width: 18 }, { key: "F", width: 12 },
              { key: "G", width: 12 }, { key: "H", width: 12 }, { key: "I", width: 18 }
            ];


            curRow += 2;

            // fill data rows for this shift
            const arr = lateGroup[sh];
            for (let i=0;i<arr.length;i++){
              const r = arr[i];
              const nomor = i+1;

              // Jadwal masuk: may be r.Jadwal_Masuk (TIME) or Scheduled_Start string
              const jamCekIn = formatTime(r.Jadwal_Masuk || r.Scheduled_Start);
              const jamActual = formatTime(r.Actual_Masuk);
              // compute duration: Actual_Masuk - Scheduled_Start
              let durasi = "";
              try {
                const sched = r.Scheduled_Start || r.Jadwal_Masuk;
                const jamScheduled = formatTime(sched);
                const jamActual = formatTime(r.Actual_Masuk);

                const baseDate = currentDateKey; // yyyy-mm-dd dari sheet
                const start = new Date(`${baseDate}T${jamScheduled}:00`);
                const actual = new Date(`${baseDate}T${jamActual}:00`);

                if (!isNaN(start) && !isNaN(actual) && actual > start) {
                  const ms = actual - start;
                  const h = Math.floor(ms / 1000 / 3600);
                  const m = Math.floor((ms / 1000 / 60) % 60);
                  durasi = `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`;
                }
              } catch(e) { durasi = ""; }


              const vals = [
                nomor,
                r.Nama ?? "",
                getNik(r),
                r.Jabatan ?? "",
                r.Departemen ?? "",
                r.Kode_Shift ?? "",
                jamCekIn,
                jamActual,
                durasi
              ];

              // write columns A..I
              for (let c=0;c<vals.length;c++){
                const col = String.fromCharCode(65 + c);
                ws.getCell(`${col}${curRow}`).value = vals[c];
                ws.getCell(`${col}${curRow}`).font = { name:"Times New Roman", size:9 };
                ws.getCell(`${col}${curRow}`).alignment = { horizontal:"center", vertical:"middle" };
                ws.getCell(`${col}${curRow}`).border = { top:{style:"thin"}, left:{style:"thin"}, bottom:{style:"thin"}, right:{style:"thin"} };
              }
              curRow++;
            }

            curRow += 2; // spacing setelah list shift terlambat
          } // end for late shifts
        } // end if terlambatRowsAll

        // --- footer (tanda tangan) seperti sebelumnya ---
        curRow++;
        const now = new Date();
        const monthEn = ["January","February","March","April","May","June","July","August","September","October","November","December"];
        ws.getCell(`A${curRow}`).value = `${String(now.getDate()).padStart(2,"0")} ${monthEn[now.getMonth()]} ${now.getFullYear()}`;
        ws.getCell(`A${curRow}`).font = { name:"Times New Roman", size:9 };

        ws.getCell(`A${curRow+1}`).value = "Human Resources Dept.";
        ws.getCell(`A${curRow+1}`).font = { name:"Times New Roman", size:9, italic:true };
        ws.mergeCells(`E${curRow+1}:I${curRow+1}`);
        ws.getCell(`E${curRow+1}`).value = "Mengetahui,";
        ws.getCell(`E${curRow+1}`).font = { name:"Times New Roman", size:9, italic:true };
        ws.getCell(`E${curRow+1}`).alignment = { horizontal:"center" };

        ws.getCell(`A${curRow+4}`).value = "………………….";
        ws.getCell(`A${curRow+4}`).font = { name:"Times New Roman", size:9, bold:true, underline:true };
        ws.mergeCells(`E${curRow+4}:I${curRow+4}`);
        ws.getCell(`E${curRow+4}`).value = "………………….";
        ws.getCell(`E${curRow+4}`).font = { name:"Times New Roman", size:9, bold:true, underline:true };
        ws.getCell(`E${curRow+4}`).alignment = { horizontal:"center" };

        ws.getCell(`A${curRow+5}`).value = "Time Keeper Staff";
        ws.getCell(`A${curRow+5}`).font = { name:"Times New Roman", size:9, italic:true };
        ws.getCell(`D${curRow+5}`).value = "Menyetujui,";
        ws.getCell(`D${curRow+5}`).font = { name:"Times New Roman", size:9, italic:true };

        ws.getCell(`D${curRow+8}`).value = "Maman Somantri";
        ws.getCell(`D${curRow+8}`).font = { name:"Times New Roman", size:9, italic:true, underline:true };
        ws.getCell(`D${curRow+9}`).value = "HR Manager";
        ws.getCell(`D${curRow+9}`).font = { name:"Times New Roman", size:9, italic:true };

      }; // end createSheetForRows

      // === generate per day sheet ===
      for (const key of dateKeys) {
        const rowsForDateUtama = rowsByDateUtama[key] || [];
        const rowsForDateTerlambat = rowsByDateTerlambat[key] || [];
        const dt = new Date(key);
        const sheetName = isNaN(dt) ? key : `${String(dt.getDate()).padStart(2,"0")}-${String(dt.getMonth()+1).padStart(2,"0")}-${dt.getFullYear()}`;
        await createSheetForRows(sheetName, rowsForDateUtama, rowsForDateTerlambat, key);
      }

      // write workbook
      const buffer = await wb.xlsx.writeBuffer();
      saveAs(new Blob([buffer]), `rekap_harian_${startDate || 'all'}_to_${endDate || 'all'}.xlsx`);
      alert("Export Rekap Perhari selesai (per hari per sheet).");
    } catch(err) {
      console.error("Export failed:", err);
      alert("Gagal export: " + (err.message || err));
    }
  }

  const STATUS_TANPA_SCAN = [
    "TIDAK HADIR",
    "LIBUR",
    "EXTRAOFF",
    "CUTI ISTIMEWA",
    "CUTI TAHUNAN",
    "CUTI BERSAMA",
    "LIBUR SETELAH MASUK DOBLE SHIFT"
  ];

  function isEmptyTime(value) {
    if (!value) return true;

    const v = String(value).trim();

    return (
      v === "" ||
      v === "0:00" ||
      v === "0:00:00" ||
      v === "00:00" ||
      v === "00:00:00"
    );
  }


  function getMonthKey(dateStr) {
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  }

  function groupByMonth(data) {
    const map = {};
    data.forEach(r => {
      const key = getMonthKey(r.Tanggal);
      if (!map[key]) map[key] = [];
      map[key].push(r);
    });
    return map;
  }


  async function exportRekapKehadiran() {
    try {
      // function applyReasonMap(data, reasonMap) {
      //   return data.map(row => {
      //     if (reasonMap[row.__uid]) {
      //       return {
      //         ...row,
      //         Status_Kehadiran: reasonMap[row.__uid]   // gunakan status yg dipilih user
      //       };
      //     }
      //     return row;
      //   });
      // }

      function applyReasonMap(data, reasonMap) {
        return data.map(row => {
          const rawReason = reasonMap[row.__uid];

          const reason =
            typeof rawReason === "string"
              ? { Status_Kehadiran: rawReason }
              : (rawReason || {});

          const statusKehadiranFinal =
            (reason.Status_Kehadiran || row.Status_Kehadiran || "HADIR")
              .trim()
              .toUpperCase();

          const isShiftOff = isEmptyTime(row.Jadwal_Masuk);

          const bebasScan =
            isShiftOff ||
            STATUS_TANPA_SCAN.includes(statusKehadiranFinal);

          const tidakScanMasuk =
            !bebasScan && isEmptyTime(row.Actual_Masuk);

          const tidakScanPulang =
            !bebasScan && isEmptyTime(row.Actual_Pulang);

          return {
            ...row,
            Status_Kehadiran: statusKehadiranFinal,
            TL_Code: reason.TL_Code || "",
            PA_Code: reason.PA_Code || "",
            TidakPostingDatang: tidakScanMasuk ? 1 : 0,
            TidakPostingPulang: tidakScanPulang ? 1 : 0
          };
        });
      }

      
      if (!filteredData || filteredData.length === 0) {
        alert("Tidak ada data untuk diexport.");
        return;
      }

      // Function to get column letter from number (1-based)
      function getColumnLetter(colNum) {
        let letter = '';
        while (colNum > 0) {
          colNum--;
          letter = String.fromCharCode(65 + (colNum % 26)) + letter;
          colNum = Math.floor(colNum / 26);
        }
        return letter;
      }

      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("Rekap Kehadiran");

      // Set kolom width (A sampai AC = 29 kolom)
      ws.columns = Array(27).fill({ width: 12 });

      // Freeze panes: kolom A-F dan baris 1-8
      ws.views = [
        {
          state: "frozen",
          ySplit: 8,  // Freeze baris 1-8
          xSplit: 6   // Freeze kolom A-F (6 kolom)
        }
      ];
      ws.getColumn("A").width = 6;
      ws.getColumn("B").width = 8;
      ws.getColumn("C").width = 30;
      ws.getColumn("D").width = 15;
      ws.getColumn("E").width = 35;
      ws.getColumn("F").width = 20;

      // ===== ROW 1: TITLE =====
      ws.mergeCells("A1:AA1");
      ws.getCell("A1").value = "REKAPITULASI KEHADIRAN KARYAWAN";
      ws.getCell("A1").font = { name: "Calibri", size: 11, bold: true, italic: true };
      ws.getCell("A1").alignment = { horizontal: "center", vertical:"middle" };
      ws.getRow(1).height = 25;

      // ===== ROW 2: COMPANY NAME =====
      ws.mergeCells("A2:AA2");
      ws.getCell("A2").value = "SARI ATER HOT SPRINGS CIATER";
      ws.getCell("A2").font = { name: "Calibri", size: 11, bold: true, italic: true };
      ws.getCell("A2").alignment = { horizontal: "center", vertical:"middle" };
      ws.getRow(2).height = 25;

      // ===== ROW 3: PERIODE =====
      // Get periode dari filtered data (ambil bulan & tahun dari tanggal pertama)
      const firstDate = new Date(filteredData[0].Tanggal);
      const monthIdx = firstDate.getMonth();
      const year = firstDate.getFullYear();
      const monthNames = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"];
      const periodText = `PERIODE : ${monthNames[monthIdx]} ${year}`;

      ws.mergeCells("A3:AA3");
      ws.getCell("A3").value = periodText;
      ws.getCell("A3").font = { name: "Calibri", size: 11, bold: true, italic: true };
      ws.getCell("A3").alignment = { horizontal: "center", vertical:"middle" };
      ws.getRow(3).height = 25;

      // ===== ROW 4: EMPTY =====
      ws.mergeCells("A4:AA4");
      ws.getRow(4).height = 10;

      // ===== ROW 5-8: HEADERS =====
      // Row 5: Main headers
      const headerCols = {
        A: "NO.",
        B: "NO.",
        C: "NAMA",
        D: "NIK",
        E: "JABATAN",
        F: "DEPARTEMEN",
        G: "KEHADIRAN"
      };

      // Merge A5:B8 for NO.
      ws.mergeCells("A5:B8");
      ws.getCell("A5").value = "NO.";
      ws.getCell("A5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("A5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("A5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("A5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
      
      // Merge C5:C8 for NAMA
      ws.mergeCells("C5:C8");
      ws.getCell("C5").value = "NAMA";
      ws.getCell("C5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("C5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("C5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("C5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge D5:D8 for NIK
      ws.mergeCells("D5:D8");
      ws.getCell("D5").value = "NIK";
      ws.getCell("D5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("D5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("D5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("D5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge E5:E8 for JABATAN
      ws.mergeCells("E5:E8");
      ws.getCell("E5").value = "JABATAN";
      ws.getCell("E5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("E5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("E5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("E5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge F5:F8 for DEPARTEMEN
      ws.mergeCells("F5:F8");
      ws.getCell("F5").value = "DEPARTEMEN";
      ws.getCell("F5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("F5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("F5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("F5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge G5:AC5 for KEHADIRAN (main header)
      ws.mergeCells("G5:AA5");
      ws.getCell("G5").value = "KEHADIRAN";
      ws.getCell("G5").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("G5").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("G5").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("G5").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Row 6: Sub-headers (REKAPITULASI, TERLAMBAT, Pulang Awal, TIDAK Scan)
      // Merge G6:N6 for REKAPITULASI
      ws.mergeCells("G6:O6");
      ws.getCell("G6").value = "REKAPITULASI";
      ws.getCell("G6").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("G6").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("G6").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("G6").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge O6:W6 for TERLAMBAT
      ws.mergeCells("P6:W6");
      ws.getCell("P6").value = "TERLAMBAT";
      ws.getCell("P6").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("P6").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("P6").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("P6").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge X6:Y6 for Pulang Awal
      ws.mergeCells("X6:Y6");
      ws.getCell("X6").value = "Pulang Awal";
      ws.getCell("X6").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("X6").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("X6").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("X6").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Merge Z6:AC6 for TIDAK SCAN
      ws.mergeCells("Z6:AA6");
      ws.getCell("Z6").value = "TIDAK SCAN";
      ws.getCell("Z6").font = { name: "Calibri", size: 9, bold: true, italic: true };
      ws.getCell("Z6").alignment = { horizontal: "center", vertical:"middle" };
      ws.getCell("Z6").border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
      ws.getCell("Z6").fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };

      // Row 7: Sub-sub-headers (H, OFF, S, I, A, EO, CUTI, DINAS LUAR, TOTAL HARI, 1'-5', 5'-10, ≥10', ∑ Dgn Izin, ∑ Tanpa Izin, Dgn Izin, Tanpa Izin, DATANG, PULANG, TIDAK SUPPORT)
      const subHeaders7 = [
        { col: "G", mergeRange: "G7:G8", text: "HADIR" },
        { col: "H", mergeRange: "H7:H8", text: "OFF" },
        { col: "I", mergeRange: "I7:I8", text: "SAKIT" },
        { col: "J", mergeRange: "J7:J8", text: "IZIN" },
        { col: "K", mergeRange: "K7:K8", text: "ALPA" },
        { col: "L", mergeRange: "L7:L8", text: "EO (EXTRA OFF)" },
        { col: "M", mergeRange: "M7:M8", text: "CUTI" },
        { col: "N", mergeRange: "N7:N8", text: "DINAS LUAR" },
        { col: "O", mergeRange: "O7:O8", text: "TOTAL HARI" },
        { col: "P", mergeRange: "P7:Q7", text: "1'-5'" },
        { col: "R", mergeRange: "R7:S7", text: "5'-10'" },
        { col: "T", mergeRange: "T7:U7", text: "≥10'" },
        { col: "V", mergeRange: "V7:V8", text: "∑ Dgn Izin" },
        { col: "W", mergeRange: "W7:W8", text: "∑ Tanpa Izin" },
        { col: "X", mergeRange: "X7:X8", text: "Dgn Izin" },
        { col: "Y", mergeRange: "Y7:Y8", text: "Tanpa Izin" },
        { col: "Z", mergeRange: "Z7:Z8", text: "DATANG" },
        { col: "AA", mergeRange: "AA7:AA8", text: "PULANG" }
      ];

      subHeaders7.forEach(header => {
        ws.mergeCells(header.mergeRange);
        ws.getCell(`${header.col}7`).value = header.text;
        ws.getCell(`${header.col}7`).font = { name: "Calibri", size: 9, bold: true, italic: true };
        ws.getCell(`${header.col}7`).alignment = { horizontal: "center", vertical:"middle" };
        ws.getCell(`${header.col}7`).border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
        ws.getCell(`${header.col}7`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
      });

      // Row 8: Sub-sub-sub-headers (untuk kategori dengan 2 sub-kolom)
      const row8Headers = [
        { col: "P", text: "Dgn Izin" },
        { col: "Q", text: "Tanpa Izin" },
        { col: "R", text: "Dgn Izin" },
        { col: "S", text: "Tanpa Izin" },
        { col: "T", text: "Dgn Izin" },
        { col: "U", text: "Tanpa Izin" }
      ];

      row8Headers.forEach(header => {
        ws.getCell(`${header.col}8`).value = header.text;
        ws.getCell(`${header.col}8`).font = { name: "Calibri", size: 9, bold: true, italic: true };
        ws.getCell(`${header.col}8`).alignment = { horizontal: "center", vertical:"middle" };
        ws.getCell(`${header.col}8`).border = { top: { style: "thin" }, left: { style: "thin" }, bottom: { style: "thin" }, right: { style: "thin" } };
        ws.getCell(`${header.col}8`).fill = { type:"pattern", pattern:"solid", fgColor:{argb:"FFD9D9D9"} };
      });

      // ===== FILL DATA ROWS (FIXED, REKAP PER KARYAWAN) =====
      let currentRow = 9;

      // --- Group + SUM per Karyawan ---
      function groupAndSumByEmployee(data) {
        const result = {};

        data.forEach(r => {
          const nik = r.NIK || r.NIP || r.nip || "";
          if (!result[nik]) {
            result[nik] = {
              NIK: nik,
              Nama: r.Nama || "",
              Jabatan: r.Jabatan || "",
              Departemen: r.Departemen || "",
              hadir: 0,
              off: 0,
              sakit: 0,
              izin: 0,
              alpa: 0,
              eo: 0,
              cuti: 0,
              dinas: 0,
              total_hari: 0,
              tl1_5_izin: 0,
              tl1_5_tanpa: 0,
              tl5_10_izin: 0,
              tl5_10_tanpa: 0,
              tl10_izin: 0,
              tl10_tanpa: 0,
              pa_izin: 0,
              pa_tanpa: 0,
              tidak_posting_datang: 0,
              tidak_posting_pulang: 0,
              tidak_support: 0
            };
          }

          const emp = result[nik];

          // ==== STATUS KEHADIRAN ====
          // const st = (r.Status_Kehadiran || "").toUpperCase();
          const st = (r.Status_Kehadiran || "").trim().toUpperCase();
          // if (!st || st === "TIDAK HADIR") {
          //   emp.alpa++;
          // }


          // if (st === "HADIR" || st === "LIBUR SETELAH MASUK DOBLE SHIFT") emp.hadir++;
          if (st === "HADIR") emp.hadir++;
          else if (st === "LIBUR") emp.off++;
          else if (st === "SAKIT") emp.sakit++;
          else if (st === "IZIN") emp.izin++;
          else if (st === "ALPA") emp.alpa++;
          else if (st === "EXTRAOFF" || st === "LIBUR SETELAH MASUK DOBLE SHIFT") emp.eo++;
          else if (st === "CUTI TAHUNAN" || st === "CUTI ISTIMEWA" ||st === "CUTI BERSAMA" ) emp.cuti++;
          else if (st === "DINAS LUAR") emp.dinas++;

          // emp.total_hari++;
          // hitung total hari berdasarkan kategori sah
          for (const nik in result) {
            const emp = result[nik];
            emp.total_hari =
              emp.hadir +
              emp.off +
              emp.sakit +
              emp.izin +
              emp.alpa +
              emp.eo +
              emp.cuti +
              emp.dinas;
          }

          // ==== TERLAMBAT ====
          const tl = r.TL_Code || "";

          switch (tl) {
            case "TL_1_5_D": emp.tl1_5_izin++; break;
            case "TL_1_5_T": emp.tl1_5_tanpa++; break;

            case "TL_5_10_D": emp.tl5_10_izin++; break;
            case "TL_5_10_T": emp.tl5_10_tanpa++; break;

            case "TL_10_D": emp.tl10_izin++; break;
            case "TL_10_T": emp.tl10_tanpa++; break;
          }

          // total telat per kategori
          emp.total_tl_izin =
            emp.tl1_5_izin +
            emp.tl5_10_izin +
            emp.tl10_izin;

          emp.total_tl_tanpa =
            emp.tl1_5_tanpa +
            emp.tl5_10_tanpa +
            emp.tl10_tanpa;   // ✔️ sudah benar




          // // ==== PULANG AWAL ====
          // const pulang = (r.Status_Pulang || "").toUpperCase();
          // if (pulang.includes("IZIN")) emp.pa_izin++;
          // else if (pulang.includes("PULANG AWAL")) emp.pa_tanpa++;
          // ==== PULANG AWAL (SUMBER TUNGGAL) ====
          if (r.PA_Code === "PA_D") emp.pa_izin++;
          else if (r.PA_Code === "PA_T") emp.pa_tanpa++;

          
          
          // ==== TIDAK SCAN DARI STATUS ====
          // if (r.TidakPostingDatang === 1) emp.tidak_posting_datang++;
          // if (r.TidakPostingPulang === 1) emp.tidak_posting_pulang++;

          // // ==== PULANG AWAL ====
          // const pa = r.Status_Pulang || "";
          // if (pa === "PULANG AWAL IZIN") emp.pa_izin++;
          // else if (pa === "PULANG AWAL TANPA IZIN") emp.pa_tanpa++;


          // ==== TIDAK POSTING ====
          if (r.TidakPostingDatang === 1) emp.tidak_posting_datang++;
          if (r.TidakPostingPulang === 1) emp.tidak_posting_pulang++;
          if (r.TidakSupport === 1) emp.tidak_support++;
        });
        Object.values(result).forEach(emp => {
          emp.total_hari =
            emp.hadir +
            emp.off +
            emp.sakit +
            emp.izin +
            emp.alpa +
            emp.eo +
            emp.cuti +
            emp.dinas;
        });


        return Object.values(result);
      }

      // gabungkan perubahan dari modal!
      const appliedData = applyReasonMap(filteredData, reasonMap);

      // sekarang rekap pakai data yang sudah disesuaikan
      const grouped = groupAndSumByEmployee(appliedData);

      function groupByDepartemen(data) {
        const map = {};

        data.forEach(emp => {
          const dept = emp.Departemen || "TANPA DEPARTEMEN";
          if (!map[dept]) map[dept] = [];
          map[dept].push(emp);
        });

        return map;
      }

      const groupedByDept = groupByDepartemen(grouped);

      function sumDepartemen(list) {
        const total = {
          hadir: 0, off: 0, sakit: 0, izin: 0, alpa: 0,
          eo: 0, cuti: 0, dinas: 0, total_hari: 0,
          tl1_5_izin: 0, tl1_5_tanpa: 0,
          tl5_10_izin: 0, tl5_10_tanpa: 0,
          tl10_izin: 0, tl10_tanpa: 0,
          total_tl_izin: 0,
          total_tl_tanpa: 0,
          pa_izin: 0,
          pa_tanpa: 0,
          tidak_posting_datang: 0,
          tidak_posting_pulang: 0
        };

        list.forEach(e => {
          Object.keys(total).forEach(k => {
            total[k] += e[k] || 0;
          });
        });

        return total;
      }

      // const grouped = groupAndSumByEmployee(filteredData);

      // grouped.forEach((emp, index) => {
      //   ws.getCell(`A${currentRow}`).value = index + 1;
      //   ws.getCell(`B${currentRow}`).value = index + 1;
      //   ws.getCell(`C${currentRow}`).value = emp.Nama;
      //   ws.getCell(`D${currentRow}`).value = emp.NIK;
      //   ws.getCell(`E${currentRow}`).value = emp.Jabatan;
      //   ws.getCell(`F${currentRow}`).value = emp.Departemen;

      //   ws.getCell(`G${currentRow}`).value = emp.hadir;
      //   ws.getCell(`H${currentRow}`).value = emp.off;
      //   ws.getCell(`I${currentRow}`).value = emp.sakit;
      //   ws.getCell(`J${currentRow}`).value = emp.izin;
      //   ws.getCell(`K${currentRow}`).value = emp.alpa;
      //   ws.getCell(`L${currentRow}`).value = emp.eo;
      //   ws.getCell(`M${currentRow}`).value = emp.cuti;
      //   ws.getCell(`N${currentRow}`).value = emp.dinas;

      //   ws.getCell(`O${currentRow}`).value = emp.total_hari;

      //   ws.getCell(`P${currentRow}`).value = emp.tl1_5_izin;
      //   ws.getCell(`Q${currentRow}`).value = emp.tl1_5_tanpa;
      //   ws.getCell(`R${currentRow}`).value = emp.tl5_10_izin;
      //   ws.getCell(`S${currentRow}`).value = emp.tl5_10_tanpa;
      //   ws.getCell(`T${currentRow}`).value = emp.tl10_izin;
      //   ws.getCell(`U${currentRow}`).value = emp.tl10_tanpa;

      //   // ∑ DENGAN IZIN (TOTAL TELAT DENGAN IZIN)
      //   ws.getCell(`V${currentRow}`).value = emp.total_tl_izin;

      //   // ∑ TANPA IZIN (TOTAL TELAT TANPA IZIN)
      //   ws.getCell(`W${currentRow}`).value = emp.total_tl_tanpa;

      //   // PULANG AWAL
      //   ws.getCell(`X${currentRow}`).value = emp.pa_izin;
      //   ws.getCell(`Y${currentRow}`).value = emp.pa_tanpa;

      //   // TIDAK SCAN
      //   ws.getCell(`Z${currentRow}`).value = emp.tidak_posting_datang;
      //   ws.getCell(`AA${currentRow}`).value = emp.tidak_posting_pulang;



      //   // Borders
      //   for (let c = 1; c <= 27; c++) {
      //     const col = getColumnLetter(c);
      //     ws.getCell(`${col}${currentRow}`).border = { 
      //       top: { style: "thin" }, 
      //       left: { style: "thin" }, 
      //       bottom: { style: "thin" }, 
      //       right: { style: "thin" } 
      //     };
      //     ws.getCell(`${col}${currentRow}`).alignment = { horizontal: "center", vertical:"middle" };
      //     ws.getCell(`${col}${currentRow}`).font = { name: "Calibri", size: 9 };
      //   }

      //   currentRow++;
      // });
      let noGlobal = 1;

      Object.entries(groupedByDept).forEach(([dept, employees]) => {

        let noDept = 1;
        const subtotal = sumDepartemen(employees);

        // === DATA PER KARYAWAN ===
        employees.forEach(emp => {
          ws.getCell(`A${currentRow}`).value = noGlobal++;
          ws.getCell(`B${currentRow}`).value = noDept++;
          ws.getCell(`C${currentRow}`).value = emp.Nama;
          ws.getCell(`D${currentRow}`).value = emp.NIK;
          ws.getCell(`E${currentRow}`).value = emp.Jabatan;
          ws.getCell(`F${currentRow}`).value = dept;

          ws.getCell(`G${currentRow}`).value = emp.hadir;
          ws.getCell(`H${currentRow}`).value = emp.off;
          ws.getCell(`I${currentRow}`).value = emp.sakit;
          ws.getCell(`J${currentRow}`).value = emp.izin;
          ws.getCell(`K${currentRow}`).value = emp.alpa;
          ws.getCell(`L${currentRow}`).value = emp.eo;
          ws.getCell(`M${currentRow}`).value = emp.cuti;
          ws.getCell(`N${currentRow}`).value = emp.dinas;
          ws.getCell(`O${currentRow}`).value = emp.total_hari;

          ws.getCell(`P${currentRow}`).value = emp.tl1_5_izin;
          ws.getCell(`Q${currentRow}`).value = emp.tl1_5_tanpa;
          ws.getCell(`R${currentRow}`).value = emp.tl5_10_izin;
          ws.getCell(`S${currentRow}`).value = emp.tl5_10_tanpa;
          ws.getCell(`T${currentRow}`).value = emp.tl10_izin;
          ws.getCell(`U${currentRow}`).value = emp.tl10_tanpa;
          ws.getCell(`V${currentRow}`).value = emp.total_tl_izin;
          ws.getCell(`W${currentRow}`).value = emp.total_tl_tanpa;
          ws.getCell(`X${currentRow}`).value = emp.pa_izin;
          ws.getCell(`Y${currentRow}`).value = emp.pa_tanpa;
          ws.getCell(`Z${currentRow}`).value = emp.tidak_posting_datang;
          ws.getCell(`AA${currentRow}`).value = emp.tidak_posting_pulang;

          // Borders
          for (let c = 1; c <= 27; c++) {
            const col = getColumnLetter(c);
            ws.getCell(`${col}${currentRow}`).border = { 
              top: { style: "thin" }, 
              left: { style: "thin" }, 
              bottom: { style: "thin" }, 
              right: { style: "thin" } 
            };
            ws.getCell(`${col}${currentRow}`).alignment = { horizontal: "center", vertical:"middle" };
            ws.getCell(`${col}${currentRow}`).font = { name: "Calibri", size: 9 };
          }
          currentRow++;
        });

        // === SUBTOTAL DIVISI ===
        ws.getCell(`C${currentRow}`).value = `TOTAL ${dept}`;
        ws.mergeCells(`C${currentRow}:F${currentRow}`);
        ws.getCell(`C${currentRow}`).font = { bold: true };

        ws.getCell(`G${currentRow}`).value = subtotal.hadir;
        ws.getCell(`H${currentRow}`).value = subtotal.off;
        ws.getCell(`I${currentRow}`).value = subtotal.sakit;
        ws.getCell(`J${currentRow}`).value = subtotal.izin;
        ws.getCell(`K${currentRow}`).value = subtotal.alpa;
        ws.getCell(`L${currentRow}`).value = subtotal.eo;
        ws.getCell(`M${currentRow}`).value = subtotal.cuti;
        ws.getCell(`N${currentRow}`).value = subtotal.dinas;
        ws.getCell(`O${currentRow}`).value = subtotal.total_hari;

        ws.getCell(`P${currentRow}`).value = subtotal.tl1_5_izin;
        ws.getCell(`Q${currentRow}`).value = subtotal.tl1_5_tanpa;
        ws.getCell(`R${currentRow}`).value = subtotal.tl5_10_izin;
        ws.getCell(`S${currentRow}`).value = subtotal.tl5_10_tanpa;
        ws.getCell(`T${currentRow}`).value = subtotal.tl10_izin;
        ws.getCell(`U${currentRow}`).value = subtotal.tl10_tanpa;
        ws.getCell(`V${currentRow}`).value = subtotal.total_tl_izin;
        ws.getCell(`W${currentRow}`).value = subtotal.total_tl_tanpa;
        ws.getCell(`X${currentRow}`).value = subtotal.pa_izin;
        ws.getCell(`Y${currentRow}`).value = subtotal.pa_tanpa;
        ws.getCell(`Z${currentRow}`).value = subtotal.tidak_posting_datang;
        ws.getCell(`AA${currentRow}`).value = subtotal.tidak_posting_pulang;

        currentRow++;

        // === 2 BARIS KOSONG ===
        currentRow += 2;
      });



      const buffer = await wb.xlsx.writeBuffer();
      saveAs(new Blob([buffer]), `rekap_kehadiran_${monthNames[monthIdx]}_${year}.xlsx`);
      alert("Export Rekap Kehadiran selesai.");
    } catch (err) {
      console.error("Export failed:", err);
      alert("Gagal export: " + (err.message || err));
    }
  }

  function parseTimeToMinutes(timeStr) {
    if (!timeStr) return null;

    const clean = timeStr.trim();

    // cek format minimal "H:M:S"
    const parts = clean.split(":");
    if (parts.length < 2) return null;

    const h = parseInt(parts[0], 10) || 0;
    const m = parseInt(parts[1], 10) || 0;
    const s = parseInt(parts[2], 10) || 0;

    return h * 60 + m + s / 60;
  }

  function diffMinutes(actual, schedule, reverse = false) {
    const a = parseTimeToMinutes(actual);
    const s = parseTimeToMinutes(schedule);
    if (a === null || s === null) return null;
    return reverse ? s - a : a - s;
  }

  function diffMinutesPulang(actual, jadwal) {
    const a = parseTimeToMinutes(actual);
    const s = parseTimeToMinutes(jadwal);
    if (a === null || s === null) return null;
    return s - a; // pulang cepat = positif
  }









  // -----------------------------------------
  // RENDER
  // -----------------------------------------
  return (
    <div className="w-full">
      {/* HEADER */}
      <div className="bg-white p-5 md:p-7 rounded-2xl shadow-md flex flex-col md:flex-row md:items-center gap-5">
        <img src={sariAter} className="w-20 md:w-28" alt="logo" />
        <div>
          <h1 className="text-2xl font-bold">Croscek Kehadiran</h1>
          <p className="text-gray-600">
            Upload jadwal & kehadiran, lalu lakukan proses croscek.
          </p>
        </div>
      </div>

      {/* UPLOAD JADWAL */}
      <div className="mt-6 flex flex-col md:flex-row gap-4">
        <label className="block w-full border-2 border-dashed border-blue-500 hover:bg-blue-50 cursor-pointer rounded-xl p-10 text-center transition">
          <UploadCloud size={45} className="text-blue-600 mx-auto" />
          <p className="text-gray-700 font-medium mt-3">Upload File Jadwal</p>
          <input type="file" onChange={handleUploadJadwal} className="hidden" />
        </label>
        <div className="flex flex-col gap-2">
          <select
            value={selectedMonth}
            onChange={handleMonthChange}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value={0}>Januari</option>
            <option value={1}>Februari</option>
            <option value={2}>Maret</option>
            <option value={3}>April</option>
            <option value={4}>Mei</option>
            <option value={5}>Juni</option>
            <option value={6}>Juli</option>
            <option value={7}>Agustus</option>
            <option value={8}>September</option>
            <option value={9}>Oktober</option>
            <option value={10}>November</option>
            <option value={11}>Desember</option>
          </select>
          <button
            onClick={exportTemplateJadwal}
            className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
          >
            <Download size={20} />
            Download Template Excel
          </button>
        </div>
      </div>


      {loadingJadwal && (
        <p className="mt-3 text-center text-gray-600">Memproses file jadwal...</p>
      )}

      {jadwalPreview && (
        <div className="bg-white mt-6 p-5 rounded-2xl shadow-md">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <FileSpreadsheet className="text-blue-700" /> Preview Jadwal
            </h2>
            <button
              onClick={saveJadwal}
              disabled={savingJadwal}
              className="bg-green-600 text-white px-4 py-2 rounded-lg shadow hover:bg-green-700"
            >
              {savingJadwal ? "Menyimpan..." : "Simpan Jadwal"}
            </button>
          </div>
          <div
            className="overflow-auto max-h-[500px] border rounded-xl p-3 text-xs"
            dangerouslySetInnerHTML={{ __html: jadwalPreview }}
          />
        </div>
      )}

      {/* TAMBAHAN: TABEL CRUD JADWAL KARYAWAN */}
      <div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-3">
          <h2 className="text-xl font-bold">Data Jadwal Karyawan</h2>
          <select
            value={`${selectedMonthJadwal}-${selectedYearJadwal}`}
            onChange={(e) => {
              const [bulan, tahun] = e.target.value.split("-").map(Number);
              setSelectedMonthJadwal(bulan);
              setSelectedYearJadwal(tahun);
            }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {availablePeriodsJadwal.length > 0 ? (
              availablePeriodsJadwal.map((period, index) => (
                <option key={index} value={`${period.bulan}-${period.tahun}`}>
                  {new Date(0, period.bulan - 1).toLocaleString("id-ID", {
                    month: "long",
                  })}{" "}
                  {period.tahun}
                </option>
              ))
            ) : (
              <option disabled>Tidak ada periode tersedia</option>
            )}
          </select>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Cari data jadwal..."
              className="border p-2 rounded-lg text-sm"
              value={searchJadwal}
              onChange={(e) => {
                setSearchJadwal(e.target.value);
                setPageJadwal(1);
              }}
            />
            <button
              className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded-lg"
              onClick={() => setShowModalTambah(true)}
            >
              <Plus size={16} /> Tambah
            </button>
            {/* 🔥 Tombol Kosongkan Jadwal */}
            <button
              className="flex items-center gap-1 bg-red-600 text-white px-3 py-1 rounded-lg"
              onClick={handleKosongkanJadwal}
            >
              🗑 Kosongkan
            </button>
          </div>
        </div>

        <div className="overflow-auto">
          <table className="min-w-full border text-xs md:text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-2">No</th>
                {colsJadwal.map(c => (
                  <th key={c} className="border p-2">{c.replace("_", " ")}</th>
                ))}
                <th className="border p-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {paginatedJadwal.map((item, index) => (
                <tr key={item.no}>
                  <td className="border p-2 text-center">{(pageJadwal - 1) * rowsPerPageJadwal + index + 1}</td>
                  {colsJadwal.map(col => (
                  <td className="border p-2" key={col}>
                    {editingId === item.no ? (
                      col === "kode_shift" ? (
                        <select
                          className="border px-2 py-1 w-full"
                          value={item[col] || ""}
                          onChange={e => handleEditChange(item.no, col, e.target.value)}
                        >
                          <option value="">Pilih Shift</option>
                          {kodeShiftOptions.map(k => (
                            <option key={k} value={k}>{k}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={col === "tanggal" ? "date" : "text"}
                          className="border px-2 py-1 w-full"
                          value={item[col] || ""}
                          onChange={e => handleEditChange(item.no, col, e.target.value)}
                          disabled={col === "nik" || col === "nama"} // nik & nama tidak bisa diedit
                        />
                      )
                    ) : item[col]}
                  </td>
                ))}

                  <td className="border p-2 flex gap-2">
                    {editingId === item.no ? (
                      <button
                        onClick={() => handleUpdate(item.no)}
                        disabled={loadingCRUD}
                        className="bg-blue-600 text-white px-2 py-1 rounded"
                      >
                        Update
                      </button>
                    ) : (
                      <button
                        onClick={() => setEditingId(item.no)}
                        className="bg-yellow-500 text-white px-2 py-1 rounded"
                      >
                        Edit
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(item.no)}
                      className="bg-red-600 text-white px-2 py-1 rounded flex items-center gap-1"
                    >
                      <Trash2 size={14} /> Hapus
                    </button>
                  </td>
                </tr>
              ))}

              {filteredJadwal.length === 0 && (
                <tr>
                  <td className="border p-4 text-center" colSpan={colsJadwal.length + 2}>
                    Tidak ada data ditemukan.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPagesJadwal > 1 && (
          <div className="flex justify-center mt-4 gap-2">
            {/* Prev button */}
            <button
              className="px-3 py-1 border rounded disabled:opacity-50"
              onClick={() => setPageJadwal(prev => Math.max(prev - 1, 1))}
              disabled={pageJadwal === 1}
            >
              Prev
            </button>

            {/* Number buttons maksimal 5 */}
            {(() => {
              const buttons = [];
              let start = 1;
              let end = Math.min(5, totalPagesJadwal); // tampilkan maksimal 5 tombol dari awal

              for (let i = start; i <= end; i++) {
                buttons.push(
                  <button
                    key={i}
                    className={`px-3 py-1 rounded border ${
                      pageJadwal === i ? "bg-green-600 text-white" : ""
                    }`}
                    onClick={() => setPageJadwal(i)}
                  >
                    {i}
                  </button>
                );
              }

              // Jika totalPages > 5, tampilkan tombol terakhir
              if (totalPagesJadwal > 5) {
                if (pageJadwal > 5 && pageJadwal < totalPagesJadwal) {
                  // highlight current page saat > 5
                  buttons.push(<span key="dots1" className="px-2">...</span>);
                }
                buttons.push(
                  <button
                    key={totalPagesJadwal}
                    className={`px-3 py-1 rounded border ${
                      pageJadwal === totalPagesJadwal ? "bg-green-600 text-white" : ""
                    }`}
                    onClick={() => setPageJadwal(totalPagesJadwal)}
                  >
                    {totalPagesJadwal}
                  </button>
                );
              }

              return buttons;
            })()}

            {/* Next button */}
            <button
              className="px-3 py-1 border rounded disabled:opacity-50"
              onClick={() => setPageJadwal(prev => Math.min(prev + 1, totalPagesJadwal))}
              disabled={pageJadwal === totalPagesJadwal}
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* MODAL TAMBAH JADWAL KARYAWAN */}
      {showModalTambah && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl w-full max-w-md">
            <h3 className="text-xl font-bold mb-4">Tambah Jadwal Karyawan</h3>

            {/* SEARCH & SELECT NAMA */}
            {/* INPUT NAMA */}
            <div className="relative w-full">
              <input
                type="text"
                className="nama-input w-full border rounded p-2"
                placeholder="Ketik nama..."
                value={newData.nama}
                onChange={(e) => {
                  setNewData({ ...newData, nama: e.target.value });
                  setShowNamaDropdown(true);
                }}
                onFocus={() => setShowNamaDropdown(true)}
              />

              {showNamaDropdown && (
                <div
                  className="nama-dropdown absolute z-50 bg-white border rounded shadow-lg max-h-72 overflow-y-auto w-full"
                >
                  {uniqueKaryawan
                    .filter(k =>
                      k.nama?.toLowerCase().includes(newData.nama.toLowerCase())
                    )
                    .sort((a, b) => a.nama.localeCompare(b.nama)) // bonus: urut A–Z
                    .map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2 hover:bg-blue-100 cursor-pointer"
                        onClick={() => {
                          setNewData({ ...newData, nama: item.nama, nik: item.nik });
                          setShowNamaDropdown(false);
                        }}
                      >
                        {item.nama} - {item.nik}
                      </div>
                    ))}
                </div>
              )}
            </div>


            {/* tampilkan nama terpilih */}
            {newData.nama && (
              <p className="text-sm text-green-600 mb-3">
                Dipilih: <b>{newData.nama}</b>
              </p>
            )}

            {/* INPUT TANGGAL */}
            <label className="text-sm font-medium">Tanggal</label>
            <input
              type="date"
              className="border rounded-lg px-3 py-2 w-full mb-3"
              value={newData.tanggal}
              onChange={(e) => setNewData({ ...newData, tanggal: e.target.value })}
            />

            {/* SEARCH & SELECT KODE SHIFT */}
            <div className="relative">
              <label className="block text-sm font-medium">Kode Shift</label>
              <input
                type="text"
                placeholder="Cari kode shift..."
                value={newData.kode_shift}
                onFocus={() => setShowShiftDropdown(true)}
                onChange={(e) => setSearchShift(e.target.value)}
                className="border w-full p-2 rounded-lg shift-input"
              />

              <div className={`absolute z-50 bg-white border rounded-lg mt-1 w-full max-h-48 overflow-y-auto shadow-lg shift-dropdown ${showShiftDropdown ? '' : 'hidden'}`}>
                {filteredShiftOptions
                  .filter(s => s.toLowerCase().includes(searchShift.toLowerCase()))
                  .map(s => (
                    <div
                      key={s}
                      onClick={() => {
                        setNewData({ ...newData, kode_shift: s });
                        setShowShiftDropdown(false);
                        setSearchShift("");
                      }}
                      className="p-2 hover:bg-blue-100 cursor-pointer"
                    >
                      {s}
                    </div>
                  ))}
                {filteredShiftOptions.filter(s =>
                  s.toLowerCase().includes(searchShift.toLowerCase())
                ).length === 0 && (
                  <div className="p-2 text-center text-gray-500">Shift tidak ditemukan</div>
                )}
              </div>
            </div>

            {/* tombol ACTION */}
            <div className="flex justify-end gap-3 mt-4">
              <button
                className="px-4 py-2 bg-gray-300 rounded-lg"
                onClick={() => setShowModalTambah(false)}
              >
                Batal
              </button>
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded-lg"
                onClick={handleCreate}
                disabled={loadingCRUD}
              >
                Simpan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* UPLOAD KEHADIRAN */}
      <div className="mt-10 flex flex-col md:flex-row gap-4">
        <label className="block w-full border-2 border-dashed border-green-500 hover:bg-green-50 cursor-pointer rounded-xl p-10 text-center transition">
          <UploadCloud size={45} className="text-green-600 mx-auto" />
          <p className="text-gray-700 font-medium mt-3">Upload File Kehadiran</p>
          <input type="file" onChange={handleUploadKehadiran} className="hidden" />
        </label>
        <div className="flex flex-col gap-2">
        {/* TAMBAHAN: SELECT BULAN (DINAMIS DARI DATA) */}
        <select
          value={`${selectedMonthKehadiran}-${selectedYearKehadiran}`}
          onChange={(e) => {
            const [bulan, tahun] = e.target.value.split("-").map(Number);
            setSelectedMonthKehadiran(bulan);
            setSelectedYearKehadiran(tahun);
          }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          disabled={loadingPeriods}
        >
          {availablePeriods.length > 0 ? (
            availablePeriods.map((period, index) => (
              <option
                key={index}
                value={`${period.bulan}-${period.tahun}`}
              >
                {new Date(0, period.bulan - 1).toLocaleString("id-ID", {
                  month: "long",
                })}{" "}
                {period.tahun}
              </option>
            ))
          ) : (
            <option disabled>Tidak ada data periode</option>
          )}
        </select>

        {/* TAMBAHAN: SELECT TAHUN (DINAMIS DARI DATA) - Opsional, jika bulan sudah mencakup tahun */}
        {/* Jika perlu select tahun terpisah, tambahkan di sini, tapi untuk sekarang cukup bulan yang mencakup tahun */}
        
        {/* TAMBAHAN: BUTTON DOWNLOAD TEMPLATE */}
        <button
          onClick={exportTemplateKehadiran}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} />
          Download Template Excel
        </button>
        
        {/* TAMBAHAN: BUTTON HAPUS PERIODE */}
        <button
          onClick={handleDeleteKehadiranPeriod}
          disabled={availablePeriods.length === 0}
          className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base disabled:opacity-50"
        >
          🗑 Hapus Data Periode
        </button>
      </div>
        {/* <button
          onClick={exportTemplateKehadiran}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} />
          Download Template Excel
        </button> */}
      </div>

      {loadingKehadiran && (
        <p className="mt-3 text-center text-gray-600">Memproses file kehadiran...</p>
      )}

      {kehadiranPreview && (
        <div className="bg-white mt-6 p-5 rounded-2xl shadow-md">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <FileSpreadsheet className="text-green-700" /> Preview Kehadiran
            </h2>
            <button
              onClick={saveKehadiran}
              disabled={savingKehadiran}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow hover:bg-blue-700"
            >
              {savingKehadiran ? "Menyimpan..." : "Simpan Kehadiran"}
            </button>
          </div>
          <div
            className="overflow-auto max-h-[500px] border rounded-xl p-3 text-xs"
            dangerouslySetInnerHTML={{ __html: kehadiranPreview }}
          />
        </div>
      )}

      {/* PROSES CROSCEK */}
      <div className="mt-10 text-center">
        <button
                    disabled={processing}
          onClick={prosesCroscek}
          className="bg-purple-600 text-white px-6 py-3 rounded-xl shadow hover:bg-purple-700 disabled:opacity-50 flex items-center mx-auto gap-2"
        >
          Proses Croscek <ArrowRight size={20} />
        </button>
      </div>


      {/* MODAL PROGRESS BAR */}
      {showProgressModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-xl w-96 text-center">
            <h3 className="text-lg font-bold mb-4">Memproses Croscek...</h3>
            <p className="text-gray-600 mb-4">Mengambil data dari database, mohon tunggu.</p>
            <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
              <div
                className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-500">{progress}% selesai</p>
          </div>
        </div>
      )}


      {/* ======================================================= */}
      {/* 📌 MODAL PREVIEW CROSCEK (dengan tambahan filter tanggal dan export) */}
      {/* ======================================================= */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white w-full max-w-5xl max-h-[90vh] rounded-xl shadow-lg overflow-hidden flex flex-col">
            {/* HEADER */}
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-bold">Preview Hasil Croscek</h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-200 rounded-full"
              >
                <X />
              </button>
            </div>

            {/* SEARCH DAN FILTER TANGGAL */}
            <div className="p-4 flex items-center gap-2 border-b">
              <Search />
              <input
                type="text"
                placeholder="Cari nama / tanggal..."
                className="border p-2 rounded w-full"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
              {/* Tambahan: Input Tanggal Awal */}
              <label className="ml-4">Tanggal Awal:</label>
              <input
                type="date"
                className="border p-2 rounded"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                }}
              />
              {/* Tambahan: Input Tanggal Akhir */}
              <label className="ml-2">Tanggal Akhir:</label>
              <input
                type="date"
                className="border p-2 rounded"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                }}
              />
            </div>

            {/* TABLE */}
            <div className="overflow-auto p-4 flex-1">
              <table className="min-w-full text-sm border">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="border p-2">Nama</th>
                    <th className="border p-2">Tanggal</th>
                    <th className="border p-2">Kode Shift</th>
                    <th className="border p-2">Jabatan</th>
                    <th className="border p-2">Departemen</th>
                    <th className="border p-2">Jadwal Masuk</th>
                    <th className="border p-2">Jadwal Pulang</th>
                    <th className="border p-2">Aktual Masuk</th>
                    <th className="border p-2">Aktual Pulang</th>
                    <th className="border p-2">Status Kehadiran</th>
                    <th className="border p-2">Status Masuk</th>
                    <th className="border p-2">Status Pulang</th>
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-100">
                      <td className="border p-2">{row.Nama}</td>
                      <td className="border p-2">{row.Tanggal}</td>
                      <td className="border p-2">{row.Kode_Shift}</td>
                      <td className="border p-2">{row.Jabatan}</td>
                      <td className="border p-2">{row.Departemen}</td>
                      <td className="border p-2">{row.Jadwal_Masuk}</td>
                      <td className="border p-2">{row.Jadwal_Pulang}</td>
                      <td className="border p-2">{formatJam(row.Actual_Masuk)}</td>
                      <td className="border p-2">{formatJam(row.Actual_Pulang)}</td>
                      <td className="border p-2">
                        {row.Status_Kehadiran !== "Tidak Hadir" ? (
                          row.Status_Kehadiran
                        ) : (
                          // <select
                          //   className="border p-1 rounded"
                          //   value={reasonMap[i] || ""}
                          //     onChange={(e) => setReasonMap({ ...reasonMap, [i]: e.target.value })}
                          // >
                          //   <option value="">Pilih Keterangan</option>
                          //   <option value="ALPA">ALPA</option>
                          //   <option value="SAKIT">SAKIT</option>
                          //   <option value="IZIN">IZIN</option>
                          // </select>
                          <select
                            className="border p-1 rounded"
                            value={reasonMap[row.__uid] || ""}
                            onChange={(e) => setReasonMap({ ...reasonMap, [row.__uid]: e.target.value })}
                          >
                            <option value="TIDAK HADIR">Pilih Keterangan</option>
                            <option value="ALPA">ALPA</option>
                            <option value="SAKIT">SAKIT</option>
                            <option value="IZIN">IZIN</option>
                            <option value="DINAS LUAR">DINAS LUAR</option>
                          </select>

                        )}
                      </td>
                      {/* <td className="border p-2">{row.Status_Masuk}</td> */}
                      {/* === STATUS MASUK (BENAR) === */}
                      <td className="border p-2">
                      {row.Status_Masuk !== "Masuk Telat" ? (
                          row.Status_Masuk
                        ) : ((() => {
                          const jadwal = row.Jadwal_Masuk;
                          const actual = row.Actual_Masuk;

                          if (!actual) return "Tidak Scan Masuk";
                          if (!jadwal) return "Masuk Tepat Waktu";

                          const diff = diffMinutes(actual, jadwal);
                          if (diff <= 0) return "Masuk Tepat Waktu";

                          let kategori = "";
                          if (diff <= 5) kategori = "1_5";
                          else if (diff <= 10) kategori = "5_10";
                          else kategori = "10";

                          const saved = reasonMap[row.__uid]?.TL_Code || "";

                          if (saved) {
                            return saved.replaceAll("_", " ");
                          }

                          return (
                            <select
                              className="border p-1 rounded"
                              onChange={(e) =>
                                setReasonMap({
                                  ...reasonMap,
                                  [row.__uid]: {
                                    ...(reasonMap[row.__uid] || {}),
                                    TL_Code: e.target.value
                                  }
                                })
                              }
                            >
                              <option value="">Pilih Keterangan</option>

                              {kategori === "1_5" && (
                                <>
                                  <option value="TL_1_5_D">1–5 Menit — Dengan Izin</option>
                                  <option value="TL_1_5_T">1–5 Menit — Tanpa Izin</option>
                                </>
                              )}

                              {kategori === "5_10" && (
                                <>
                                  <option value="TL_5_10_D">5–10 Menit — Dengan Izin</option>
                                  <option value="TL_5_10_T">5–10 Menit — Tanpa Izin</option>
                                </>
                              )}

                              {kategori === "10" && (
                                <>
                                  <option value="TL_10_D">≥10 Menit — Dengan Izin</option>
                                  <option value="TL_10_T">≥10 Menit — Tanpa Izin</option>
                                </>
                              )}
                            </select>
                          );
                      })())}
                      </td>

                  
                      {/* <td className="border p-2">{row.Status_Pulang}</td> */}
                      <td className="border p-2">
                        {row.Status_Pulang !== "Pulang Terlalu Cepat" ? (
                          row.Status_Pulang
                        ) : ((() => {
                          const jadwal = row.Jadwal_Pulang;
                          const actual = row.Actual_Pulang;

                          // === BUKAN HARI KERJA ===
                          if (isEmptyTime(jadwal)) return "Pulang Tepat Waktu";

                          // === TIDAK SCAN ===
                          if (isEmptyTime(actual)) return "Tidak Scan Pulang";

                          const diff = diffMinutesPulang(actual, jadwal);

                          // === TEPAT / LEBIH LAMA ===
                          if (diff >= 0) return "Pulang Tepat Waktu";

                          // === PULANG AWAL ===
                          const saved = reasonMap[row.__uid]?.PA_Code || "";
                          if (saved) {
                            return saved === "PA_D"
                              ? "Pulang Awal Dengan Izin"
                              : "Pulang Awal Tanpa Izin";
                          }

                          return (
                            <select
                              className="border p-1 rounded"
                              onChange={(e) =>
                                setReasonMap({
                                  ...reasonMap,
                                  [row.__uid]: {
                                    ...(reasonMap[row.__uid] || {}),
                                    PA_Code: e.target.value
                                  }
                                })
                              }
                            >
                              <option value="">Pilih Keterangan</option>
                              <option value="PA_D">Pulang Awal — Dengan Izin</option>
                              <option value="PA_T">Pulang Awal — Tanpa Izin</option>
                            </select>
                          );
                        })())}
                      </td>




                    </tr>
                  ))}

                  {paginated.length === 0 && (
                    <tr>
                      <td colSpan="10" className="text-center p-4">
                        Tidak ada data
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* EXPORT BUTTON DAN PAGINATION */}
            <div className="p-4 border-t flex justify-between items-center">
              {/* Grup tombol kiri */}
              <div className="flex items-center gap-2">
                <button
                  onClick={exportFilteredData}
                  className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center gap-1"
                >
                  <FileSpreadsheet size={16} /> Export to Excel
                </button>

                <button
                  onClick={exportRekapPerhari}
                  className="px-4 py-2 bg-green-600 text-white rounded flex items-center gap-1"
                >
                  <FileSpreadsheet size={16} /> Rekap Perhari
                </button>
                <button
                  onClick={exportRekapKehadiran}
                  className="px-4 py-2 bg-green-600 text-white rounded flex items-center gap-1"
                >
                  <FileSpreadsheet size={16} /> Rekap Periode
                </button>
              </div>

              {/* Navigasi halaman */}
              <div className="flex items-center gap-4">
                <button
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                  className="px-4 py-2 bg-gray-200 rounded disabled:opacity-40"
                >
                  Prev
                </button>

                <span className="font-semibold">
                  {page} / {totalPages}
                </span>

                <button
                  disabled={page === totalPages}
                  onClick={() => setPage(page + 1)}
                  className="px-4 py-2 bg-gray-200 rounded disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}