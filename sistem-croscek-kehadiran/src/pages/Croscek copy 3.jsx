// src/pages/Croscek.jsx
import { useState } from "react";
import { UploadCloud, FileSpreadsheet, ArrowRight, Search, X } from "lucide-react";
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
  const rowsPerPage = 15;

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
  // PAGINATION + SEARCH
  // -----------------------------------------
  const filtered = croscekData.filter((row) => {
    return (
      row.Nama.toLowerCase().includes(search.toLowerCase()) ||
      String(row.Tanggal).includes(search)
    );
  });

  const totalPages = Math.ceil(filtered.length / rowsPerPage);
  const paginated = filtered.slice((page - 1) * rowsPerPage, page * rowsPerPage);

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
      <label className="mt-10 block w-full border-2 border-dashed border-blue-500 hover:bg-blue-50 cursor-pointer rounded-xl p-10 text-center transition">
        <UploadCloud size={45} className="text-blue-600 mx-auto" />
        <p className="text-gray-700 font-medium mt-3">Upload File Jadwal</p>
        <input type="file" onChange={handleUploadJadwal} className="hidden" />
      </label>

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

      {/* UPLOAD KEHADIRAN */}
      <label className="mt-10 block w-full border-2 border-dashed border-green-500 hover:bg-green-50 cursor-pointer rounded-xl p-10 text-center transition">
        <UploadCloud size={45} className="text-green-600 mx-auto" />
        <p className="text-gray-700 font-medium mt-3">Upload File Kehadiran</p>
        <input type="file" onChange={handleUploadKehadiran} className="hidden" />
      </label>

      {loadingKehadiran && (
        <p className="mt-3 text-center text-gray-600">
          Memproses file kehadiran...
        </p>
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
      {/* 📌 MODAL PREVIEW CROSCEK */}
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

            {/* SEARCH */}
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
                      <td colSpan="8" className="text-center p-4">
                        Tidak ada data
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* PAGINATION */}
            <div className="p-4 border-t flex justify-between items-center">
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
      )}
    </div>
  );
}
