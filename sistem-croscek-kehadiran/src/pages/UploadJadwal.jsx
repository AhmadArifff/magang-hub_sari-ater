// UploadJadwal.jsx
import { useState, useEffect } from "react";
import { UploadCloud, FileSpreadsheet, Trash2, Plus, Download } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

export default function UploadJadwal() {
  const API_URL = "http://127.0.0.1:5000/api";

  const [htmlTable, setHtmlTable] = useState("");
  const [currentFile, setCurrentFile] = useState(null);
  const [scheduleList, setScheduleList] = useState([]);
  const [loading, setLoading] = useState(false);

  const [editingKode, setEditingKode] = useState(null);
  const [newData, setNewData] = useState({
    kode: "", lokasi_kerja: "", nama_shift: "",
    jam_masuk: "", jam_pulang: "", keterangan: "",
    group: "", status: "", kontrol: ""
  });

  const [showModal, setShowModal] = useState(false);

  useEffect(() => { loadSchedules(); }, []);

  const loadSchedules = async () => {
    try {
      const res = await fetch(`${API_URL}/list`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setScheduleList(data);
    } catch (e) {
      alert("Gagal load data: " + e.message);
    }
  };

  const handleFileUpload = async (e) => {
    const f = e.target.files[0];
    if (!f) return;

    setCurrentFile(f);

    const buffer = await f.arrayBuffer();
    const wb = XLSX.read(buffer);
    const sheet = wb.Sheets[wb.SheetNames[0]];

    let html = XLSX.utils.sheet_to_html(sheet);
    html = html
      .replace(/<table/g, `<table class='min-w-full border border-gray-300 text-sm bg-white'`)
      .replace(/<td/g, `<td class='border border-gray-300 px-2 py-2'`)
      .replace(/<th/g, `<th class='border border-gray-300 bg-gray-100 px-2 py-2 text-center font-bold'`);

    setHtmlTable(html);
  };

  const handleSave = async () => {
    if (!currentFile) return alert("Tidak ada file");

    try {
      setLoading(true);

      const form = new FormData();
      form.append("file", currentFile);

      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: form
      });

      const json = await res.json();

      if (!res.ok) {
        alert("Error backend: " + (json.error || res.statusText));
        return;
      }

      alert("Upload sukses!");
      setHtmlTable("");
      setCurrentFile(null);
      loadSchedules();
    } catch (e) {
      alert("Upload gagal: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  // ------------------- CRUD -------------------
  const handleCreate = async () => {
    try {
      await fetch(`${API_URL}/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newData),
      });
      setShowModal(false);
      setNewData({ kode: "", lokasi_kerja: "", nama_shift: "", jam_masuk: "", jam_pulang: "",
        keterangan: "", group: "", status: "", kontrol: "" });
      await loadSchedules();
    } catch (e) { console.error(e); }
  };

  // local edit change updates the scheduleList state (so UI updates)
  const handleEditChange = (kode, field, value) => {
    setScheduleList(prev => prev.map(item => (item.kode === kode ? { ...item, [field]: value } : item)));
  };

  // Normalize time string: if "HH:MM" -> "HH:MM:00". If already contains seconds, keep it.
  function normalizeTimeForBackend(t) {
    if (t === null || t === undefined) return null;
    const s = String(t).trim();
    if (s === "") return null;
    // If format like "07:00" => add :00
    if (/^\d{1,2}:\d{2}$/.test(s)) {
      return s.length === 4 ? ("0" + s + ":00") : (s + ":00");
    }
    // If "7:00" or "07:00:00" or "07:00:00.000000" -> try to extract HH:MM:SS
    if (/^\d{1,2}:\d{2}:\d{2}/.test(s)) {
      // take first 8 chars
      return s.slice(0,8);
    }
    // fallback: return original (let backend handle parse)
    return s;
  }

  // UPDATE action — improved: send normalized time, wait response, show error
  const handleUpdate = async (kode) => {
    const data = scheduleList.find(item => item.kode === kode);
    if (!data) {
      alert("Data tidak ditemukan untuk diupdate");
      return;
    }

    // Prepare payload: clone and normalize times
    const payload = {
      lokasi_kerja: data.lokasi_kerja || "",
      nama_shift: data.nama_shift || "",
      jam_masuk: normalizeTimeForBackend(data.jam_masuk),
      jam_pulang: normalizeTimeForBackend(data.jam_pulang),
      keterangan: data.keterangan || "",
      group: data.group || "",
      status: data.status || "non-active",
      kontrol: data.kontrol || ""
    };

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/update/${encodeURIComponent(kode)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const json = await res.json();
      if (!res.ok) {
        const msg = json.error || json.message || res.statusText;
        alert("Gagal update: " + msg);
        return;
      }

      // Success: exit edit mode and reload data
      setEditingKode(null);
      await loadSchedules();
      // small success notification
      // (optional) alert("Update berhasil");
    } catch (e) {
      console.error("Update error:", e);
      alert("Update gagal: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (kode) => {
    if (!confirm("Hapus data ini?")) return;
    try {
      const res = await fetch(`${API_URL}/delete/${kode}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json();
        alert("Gagal hapus: " + (json.error || res.statusText));
        return;
      }
      await loadSchedules();
    } catch (e) { console.error(e); }
  };

  const cols = ["kode","lokasi_kerja","nama_shift","jam_masuk","jam_pulang","keterangan","group","status","kontrol"];

  // FILTER DATA SEARCH
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  const filteredData = scheduleList.filter(item => {
    const keyword = search.toLowerCase();
    return Object.values(item).some(val =>
      String(val).toLowerCase().includes(keyword)
    );
  });

  // PAGINATION
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  const startIndex = (currentPage - 1) * rowsPerPage;
  const currentRows = filteredData.slice(startIndex, startIndex + rowsPerPage);

  // EXPORT TEMPLATE EXCEL (tidak diubah)
  const exportTemplate = () => {
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([
      ["No.", "Lokasi Kerja", "Nama", "Kode", "Jam", "", "Keterangan", "Group", "Status", "Kontrol"],
      ["", "", "", "", "Masuk", "Pulang", "", "", "", ""]
    ]);

    ws['!merges'] = [
      { s: { r: 0, c: 0 }, e: { r: 1, c: 0 } },
      { s: { r: 0, c: 1 }, e: { r: 1, c: 1 } },
      { s: { r: 0, c: 2 }, e: { r: 1, c: 2 } },
      { s: { r: 0, c: 3 }, e: { r: 1, c: 3 } },
      { s: { r: 0, c: 4 }, e: { r: 0, c: 5 } },
      { s: { r: 0, c: 6 }, e: { r: 1, c: 6 } },
      { s: { r: 0, c: 7 }, e: { r: 1, c: 7 } },
      { s: { r: 0, c: 8 }, e: { r: 1, c: 8 } },
      { s: { r: 0, c: 9 }, e: { r: 1, c: 9 } }
    ];

    const headerStyle = {
      fill: { fgColor: { rgb: "808080" } },
      font: { color: { rgb: "FFFFFF" }, bold: true },
      alignment: { horizontal: "center", vertical: "center" }
    };

    ['A1','B1','C1','D1','E1','F1','G1','H1','I1','J1','E2','F2'].forEach(cell => {
      if (ws[cell]) ws[cell].s = headerStyle;
    });

    ws['!cols'] = [
      { wch: 5 }, { wch: 15 }, { wch: 15 }, { wch: 10 },
      { wch: 10 }, { wch: 10 }, { wch: 15 }, { wch: 10 }, { wch: 10 }, { wch: 10 }
    ];

    XLSX.utils.book_append_sheet(wb, ws, "Template Jadwal");
    XLSX.writeFile(wb, "template_jadwal.xlsx");
  };

  return (
    <div className="w-full">
      {/* HEADER */}
      <div className="bg-white p-4 md:p-6 rounded-2xl shadow-md flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
        <img src={sariAter} alt="Sari Ater" className="w-20 md:w-28 object-contain" />
        <div>
          <h1 className="text-xl md:text-2xl font-bold">Upload Informasi Jadwal</h1>
          <p className="text-gray-600">Upload file Excel untuk melihat dan menyimpan jadwal.</p>
        </div>
      </div>

      {/* UPLOAD */}
      <div className="mt-6 flex flex-col md:flex-row gap-4">
        <label className="block w-full border-2 border-dashed border-[#1BA39C] bg-white hover:bg-[#e9f7f7] transition cursor-pointer rounded-xl p-10 md:p-14 text-center">
          <UploadCloud size={40} className="text-[#1BA39C] mx-auto" />
          <p className="text-gray-700 font-medium mt-3 text-sm md:text-base">Klik untuk Upload File Excel</p>
          <input type="file" onChange={handleFileUpload} accept=".xls,.xlsx" className="hidden" />
        </label>
        <button
          onClick={exportTemplate}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} />
          Download Template Excel
        </button>
      </div>

      {/* PREVIEW */}
      {htmlTable && (
        <div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md relative">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-4 gap-3">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="text-green-700" size={28} />
              <h2 className="text-xl font-bold">Preview Data</h2>
            </div>
            <button
              onClick={handleSave}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg shadow text-sm md:text-base"
            >
              Simpan
            </button>
          </div>
          <div className="overflow-auto max-h-[400px] md:max-h-[600px] border rounded-xl p-3 text-xs md:text-sm">
            <div dangerouslySetInnerHTML={{ __html: htmlTable }} />
          </div>
        </div>
      )}

      {/* TABLE + CRUD */}
<div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md">

  {/* HEADER + SEARCH */}
  <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-3">
    <h2 className="text-xl font-bold">Data Informasi Jadwal</h2>

    <div className="flex items-center gap-2">
      <input
        type="text"
        placeholder="Cari data..."
        className="border p-2 rounded-lg text-sm"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setCurrentPage(1); // reset halaman
        }}
      />
      <button
        className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded-lg"
        onClick={() => setShowModal(true)}
      >
        <Plus size={16} /> Tambah
      </button>
    </div>
  </div>

    {/* TABEL */}
      <div className="overflow-auto">
        <table className="min-w-full border text-xs md:text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="border p-2">No</th>
              {cols.map(c => (
                <th key={c} className="border p-2">{c.replace("_", " ")}</th>
              ))}
              <th className="border p-2">Action</th>
            </tr>
          </thead>

          <tbody>
            {currentRows.map((item, index) => (
              <tr key={item.kode}>
                <td className="border p-2 text-center">{startIndex + index + 1}</td>

                {cols.map(col => (
                  <td className="border p-2" key={col}>
                    {editingKode === item.kode ? (
                      <input
                        type={
                          col === "jam_masuk" || col === "jam_pulang"
                            ? "time"
                            : "text"
                        }
                        className={`border px-2 py-1 w-full ${col === "kode" ? "bg-gray-200 cursor-not-allowed" : ""}`}
                        value={item[col] || ""}
                        onChange={e =>
                          col === "kode" 
                            ? null                           // ❌ jangan izinkan edit
                            : handleEditChange(item.kode, col, e.target.value)
                        }
                        disabled={col === "kode"}            // 🔒 INILAH KUNCI UTAMA
                      />
                    ) : item[col]}
                  </td>
                ))}

                <td className="border p-2 flex gap-2">
                  {editingKode === item.kode ? (
                    <button
                      onClick={() => handleUpdate(item.kode)}
                      className="bg-blue-600 text-white px-2 py-1 rounded"
                    >
                      Update
                    </button>
                  ) : (
                    <button
                      onClick={() => setEditingKode(item.kode)}
                      className="bg-yellow-500 text-white px-2 py-1 rounded"
                    >
                      Edit
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(item.kode)}
                    className="bg-red-600 text-white px-2 py-1 rounded flex items-center gap-1"
                  >
                    <Trash2 size={14} /> Hapus
                  </button>
                </td>
              </tr>
            ))}

            {filteredData.length === 0 && (
              <tr>
                <td className="border p-4 text-center" colSpan={cols.length + 2}>
                  Tidak ada data ditemukan.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* PAGINATION */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-4 gap-2">
          <button
            className="px-3 py-1 border rounded disabled:opacity-50"
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
          >
            Prev
          </button>

          {/* Number buttons */}
          {[...Array(totalPages)].map((_, i) => (
            <button
              key={i}
              className={`px-3 py-1 rounded border ${
                currentPage === i + 1 ? "bg-green-600 text-white" : ""
              }`}
              onClick={() => setCurrentPage(i + 1)}
            >
              {i + 1}
            </button>
          ))}

          <button
            className="px-3 py-1 border rounded disabled:opacity-50"
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>


      {/* MODAL TAMBAH */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
          <div className="bg-white p-6 rounded-xl w-96">
            <h3 className="text-lg font-bold mb-4">Tambah Informasi Jadwal</h3>
            {cols.map(col => {
              // Gunakan input type="time" untuk jam_masuk dan jam_pulang
              if (col === "jam_masuk" || col === "jam_pulang") {
                return (
                  <input
                    key={col}
                    type="time"
                    placeholder={col.replace("_"," ")}
                    className="border p-2 w-full mb-2"
                    value={newData[col] || ""}
                    onChange={e => setNewData({...newData, [col]: e.target.value})}
                  />
                );
              }

              // input biasa untuk kolom lainnya
              return (
                <input
                  key={col}
                  placeholder={col.replace("_"," ")}
                  className="border p-2 w-full mb-2"
                  value={newData[col] || ""}
                  onChange={e => setNewData({...newData, [col]: e.target.value})}
                />
              );
            })}

            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowModal(false)} className="px-3 py-1 rounded border">Batal</button>
              <button onClick={handleCreate} className="px-3 py-1 rounded bg-green-600 text-white">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
