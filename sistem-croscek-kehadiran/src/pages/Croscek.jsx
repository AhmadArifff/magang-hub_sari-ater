// src/pages/Croscek.jsx
import { useState, useEffect } from "react";
import { UploadCloud, FileSpreadsheet, ArrowRight, Search, X, Plus, Trash2, Download } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

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

  // TAMBAHAN: STATE UNTUK CRUD JADWAL KARYAWAN (DISESUAIKAN DENGAN KOLOM BARU, ID_ABSEN MANUAL)
  const [jadwalKaryawanList, setJadwalKaryawanList] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [newData, setNewData] = useState({
    id_absen: "", nama: "", tanggal: "", kode_shift: ""  // Tambahkan id_absen
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

  // EXPORT TEMPLATE EXCEL UNTUK JADWAL (diperbaiki dengan aoa_to_sheet untuk memastikan data muncul)
  const exportTemplateJadwal = () => {
    const wb = XLSX.utils.book_new();

    // Ambil tanggal sekarang
    const today = new Date();
    const month = today.getMonth(); // 0-11
    const year = today.getFullYear();

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
    XLSX.writeFile(wb, `template_jadwal_${month + 1}-${year}.xlsx`);
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
      alert(data.message || "Berhasil menyimpan jadwal");
      loadJadwalKaryawan(); // Reload data setelah save
    } catch {
      alert("Error saat menyimpan jadwal");
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
    if (!kehadiranFile) return alert("Upload file dulu");

    setSavingKehadiran(true);
    try {
      const form = new FormData();
      form.append("file", kehadiranFile);

      const res = await fetch(`${API}/import-kehadiran`, {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      alert(data.message || "Kehadiran berhasil disimpan");
    } catch {
      alert("Error saat menyimpan kehadiran");
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
      alignment: { horizontal: "center", vertical: "center" }
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

    // -----------------------------------------
  // PROSES CROSCEK (SHOW MODAL)
  // -----------------------------------------
  async function prosesCroscek() {
    setProcessing(true);

    try {
      const res = await fetch(`${API}/croscek`);
      const data = await res.json();
      setCroscekData(data.data || []);
      setShowModal(true);
    } catch (err) {
      alert("Gagal memproses croscek");
    }

    setProcessing(false);
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

  // TAMBAHAN: CRUD HANDLERS UNTUK JADWAL KARYAWAN (DISESUAIKAN DENGAN ID_ABSEN MANUAL)
  const handleCreate = async () => {
    try {
      setLoadingCRUD(true);
      await fetch(`${API}/jadwal-karyawan/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newData),
      });
      setShowModalTambah(false);
      setNewData({ id_absen: "", nama: "", tanggal: "", kode_shift: "" });
      await loadJadwalKaryawan();
    } catch (e) {
      alert("Gagal tambah data: " + e.message);
    } finally {
      setLoadingCRUD(false);
    }
  };

  const handleEditChange = (id_absen, field, value) => {
    setJadwalKaryawanList(prev => prev.map(item => (item.id_absen === id_absen ? { ...item, [field]: value } : item)));
  };

  const handleUpdate = async (id_absen) => {
    const data = jadwalKaryawanList.find(item => item.id_absen === id_absen);
    if (!data) {
      alert("Data tidak ditemukan");
      return;
    }
    try {
      setLoadingCRUD(true);
      const res = await fetch(`${API}/jadwal-karyawan/update/${id_absen}`, {
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

  const handleDelete = async (id_absen) => {
    if (!confirm("Hapus data ini?")) return;
    try {
      const res = await fetch(`${API}/jadwal-karyawan/delete/${id_absen}`, { method: "DELETE" });
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

  const filteredJadwal = jadwalKaryawanList.filter(item => {
    const keyword = searchJadwal.toLowerCase();
    return Object.values(item).some(val => String(val).toLowerCase().includes(keyword));
  });

  const totalPagesJadwal = Math.ceil(filteredJadwal.length / rowsPerPageJadwal);
  const paginatedJadwal = filteredJadwal.slice((pageJadwal - 1) * rowsPerPageJadwal, pageJadwal * rowsPerPageJadwal);

  const colsJadwal = ["id_absen", "nama", "tanggal", "kode_shift"];

  // Export Crocek Absem (filtered data)
  const exportFilteredData = () => {
    const wb = XLSX.utils.book_new();
    const headers = ["Nama", "Tanggal", "Kode Shift", "Jadwal Masuk", "Jadwal Pulang", "Aktual Masuk", "Aktual Pulang", "Status Kehadiran", "Status Masuk", "Status Pulang"];
    const data = [headers, ...filteredData.map(row => [
      row.Nama, row.Tanggal, row.Kode_Shift, row.Jadwal_Masuk, row.Jadwal_Pulang, row.Actual_Masuk, row.Actual_Pulang, row.Status_Kehadiran, row.Status_Masuk, row.Status_Pulang
    ])];
    const ws = XLSX.utils.aoa_to_sheet(data);
    ws['!cols'] = headers.map(() => ({ wch: 15 }));
    XLSX.utils.book_append_sheet(wb, ws, "Hasil Croscek");
    XLSX.writeFile(wb, `hasil_croscek_${startDate || 'all'}_${endDate || 'all'}.xlsx`);
  };

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
        <button
          onClick={exportTemplateJadwal}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} />
          Download Template Excel
        </button>
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
                <tr key={item.id_absen}>
                  <td className="border p-2 text-center">{(pageJadwal - 1) * rowsPerPageJadwal + index + 1}</td>
                  {colsJadwal.map(col => (
                    <td className="border p-2" key={col}>
                      {editingId === item.id_absen ? (
                        <input
                          type={
                            col === "tanggal" ? "date" :
                            col === "nama" || col === "kode_shift" || col === "id_absen" ? "text" : "text"
                          }
                          className="border px-2 py-1 w-full"
                          value={item[col] || ""}
                          onChange={e => handleEditChange(item.id_absen, col, e.target.value)}
                          disabled={col === "id_absen"} // ❌ id_absen tidak bisa diedit
                        />
                      ) : item[col]}
                    </td>
                  ))}
                  <td className="border p-2 flex gap-2">
                    {editingId === item.id_absen ? (
                      <button
                        onClick={() => handleUpdate(item.id_absen)}
                        disabled={loadingCRUD}
                        className="bg-blue-600 text-white px-2 py-1 rounded"
                      >
                        Update
                      </button>
                    ) : (
                      <button
                        onClick={() => setEditingId(item.id_absen)}
                        className="bg-yellow-500 text-white px-2 py-1 rounded"
                      >
                        Edit
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(item.id_absen)}
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
          <div className="bg-white p-6 rounded-xl w-96">
            <h3 className="text-lg font-bold mb-4">Tambah Jadwal Karyawan</h3>
            {colsJadwal.map(col => (
              <input
                key={col}
                type={
                  col === "tanggal" ? "date" :
                  col === "nama" || col === "kode_shift" || col === "id_absen" ? "text" : "text"
                }
                placeholder={col.replace("_", " ")}
                className="border p-2 w-full mb-2"
                value={newData[col] || ""}
                onChange={e => setNewData({ ...newData, [col]: e.target.value })}
              />
            ))}
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModalTambah(false)} className="px-3 py-1 rounded border">Batal</button>
              <button onClick={handleCreate} disabled={loadingCRUD} className="px-3 py-1 rounded bg-green-600 text-white">
                {loadingCRUD ? "Menyimpan..." : "Simpan"}
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
        <button
          onClick={exportTemplateKehadiran}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} />
          Download Template Excel
        </button>
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
                      <td className="border p-2">{row.Jadwal_Masuk}</td>
                      <td className="border p-2">{row.Jadwal_Pulang}</td>
                      <td className="border p-2">{row.Actual_Masuk}</td>
                      <td className="border p-2">{row.Actual_Pulang}</td>
                      <td className="border p-2">{row.Status_Kehadiran}</td>
                      <td className="border p-2">{row.Status_Masuk}</td>
                      <td className="border p-2">{row.Status_Pulang}</td>
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
              {/* Tambahan: Tombol Export */}
              <button
                onClick={exportFilteredData}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Export to Excel
              </button>

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
