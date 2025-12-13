// Karyawan.jsx
import { useState, useEffect } from "react";
import { UploadCloud, FileSpreadsheet, Plus, Download, Trash2, Edit, Search } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

export default function Karyawan() {
  const API_URL = "http://127.0.0.1:5000/api";  // ✅ TAMBAHKAN INI: URL backend Flask

  const [showModal, setShowModal] = useState(false);
  const [data, setData] = useState([]);
  const [form, setForm] = useState({ nama: "", nik: "", jabatan: "", dept: "" });
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isEdit, setIsEdit] = useState(false);
  const [editingNik, setEditingNik] = useState(null);
  const [loading, setLoading] = useState(false);
  const [previewTable, setPreviewTable] = useState("");
  const [currentFile, setCurrentFile] = useState(null);

  const rowsPerPage = 10;
  const cols = ["nama", "nik", "jabatan", "dept"];

  const fetchData = async () => {
    const res = await fetch(`${API_URL}/karyawan/list?search=${search}&page=${currentPage}`);
    const json = await res.json();
    setData(json.data);
    setTotal(json.total);
  };

  useEffect(() => {
    fetchData();
  }, [currentPage, search]);

  const totalPages = Math.ceil(total / rowsPerPage);

  // UPLOAD EXCEL
  const uploadExcel = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setCurrentFile(file);

    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer);
    const sheet = wb.Sheets[wb.SheetNames[0]];

    let html = XLSX.utils.sheet_to_html(sheet);
    html = html
      .replace(/<table/g, `<table class='min-w-full border border-gray-300 text-sm bg-white'`)
      .replace(/<td/g, `<td class='border border-gray-300 px-2 py-2'`)
      .replace(/<th/g, `<th class='border border-gray-300 bg-gray-100 px-2 py-2 text-center font-bold'`);

    setPreviewTable(html);
  };

  const saveExcelToDB = async () => {
    if (!currentFile) return alert("Tidak ada file");

    const formData = new FormData();
    formData.append("file", currentFile);

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/karyawan/upload`, {  // ✅ GUNAKAN API_URL
        method: "POST",
        body: formData
      });

      let json = null;

      try {
        json = await res.json();
      } catch {
        json = null; // ❗ biarkan null jika backend tidak kirim JSON
      }

      if (!res.ok) {
        alert("Upload gagal: " + (json?.error || res.statusText || "Server Error"));
        return;
      }

      if (json?.updated_total > 0) {
        const updatedText = json.updated_data
          .map(u => `• ${u.nik} - ${u.nama} (${u.jabatan}, ${u.dept})`)
          .join("\n");

        alert(
          `${json.message}\n\n` +
          `Data terupdate (${json.updated_total}):\n` +
          `${updatedText}${json.updated_total > json.updated_data.length ? "\n\n*Lebih banyak data terupdate, cek log database.*" : ""}`
        );
      } else {
        alert(json?.message);
      }
      setPreviewTable("");
      setCurrentFile(null);
      fetchData();

    } catch (e) {
      alert("Upload gagal: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const saveData = async () => {
    try {
      setLoading(true);
      if (isEdit) {
        await fetch(`${API_URL}/karyawan/update/${editingNik}`, {  // ✅ GUNAKAN API_URL
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form)
        });
      } else {
        await fetch(`${API_URL}/karyawan/create`, {  // ✅ GUNAKAN API_URL
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form)
        });
      }
      setShowModal(false);
      setForm({ nama: "", nik: "", jabatan: "", dept: "" });
      setIsEdit(false);
      setEditingNik(null);
      fetchData();
    } catch (e) {
      alert("Gagal simpan: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const removeData = async (nik) => {
    if (!confirm("Hapus data ini?")) return;
    try {
      setLoading(true);
      await fetch(`${API_URL}/karyawan/delete/${nik}`, { method: "DELETE" });  // ✅ GUNAKAN API_URL
      fetchData();
    } catch (e) {
      alert("Gagal hapus: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const editData = (d) => {
    setForm(d);
    setEditingNik(d.nik);
    setIsEdit(true);
    setShowModal(true);
  };

  const downloadTemplate = () => {
    const sheetData = [
      ["NAMA", "NIK", "JABATAN", "DEPT"],
      ["IMAM RACHMAN NUGRAHA", "210010174", "DUTY MANAGER", "A & G"],
      ["TEDDY BUDIANA, S.PD", "205060271", "DUTY MANAGER", "A & G"],
      ["ARI HERMOWO FARISWANTO", "210180641", "GENERAL MANAGER", "A & G"],
      ["AANG HASYIM ASHARI A", "210220782", "OUTLET CASHIER", "ACCOUNTING"]
    ];
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(sheetData);
    XLSX.utils.book_append_sheet(wb, ws, "Template");
    XLSX.writeFile(wb, "Template_Data_Karyawan.xlsx");
  };

  return (
    <div className="w-full">
      {/* HEADER */}
      <div className="bg-white p-4 md:p-6 rounded-2xl shadow-md flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
        <img src={sariAter} alt="Logo" className="w-20 md:w-28 object-contain" />
        <div>
          <h1 className="text-xl md:text-2xl font-bold">Upload Data Karyawan</h1>
          <p className="text-gray-600">Unggah file excel atau tambah manual.</p>
        </div>
      </div>

      {/* UPLOAD & TEMPLATE */}
      <div className="mt-6 flex flex-col md:flex-row gap-4">
        <label className="block w-full border-2 border-dashed border-[#1BA39C] bg-white hover:bg-[#e9f7f7] transition cursor-pointer rounded-xl p-10 md:p-14 text-center">
          <UploadCloud size={40} className="text-[#1BA39C] mx-auto" />
          <p className="text-gray-700 font-medium mt-3 text-sm md:text-base">Klik untuk Upload File Excel</p>
          <input type="file" hidden accept=".xlsx,.xls" onChange={uploadExcel} />
        </label>
        <button
          onClick={downloadTemplate}
          className="flex items-center justify-center gap-2 bg-[#1BA39C] hover:bg-[#158f89] text-white px-6 py-4 rounded-xl shadow-md text-sm md:text-base"
        >
          <Download size={20} /> Download Template Excel
        </button>
      </div>

      {/* PREVIEW */}
      {previewTable && (
        <div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-4 gap-3">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="text-green-700" size={28} />
              <h2 className="text-xl font-bold">Preview Data Excel</h2>
            </div>
            <button
              onClick={saveExcelToDB}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg shadow text-sm md:text-base"
            >
              Simpan
            </button>
          </div>

          <div className="overflow-auto max-h-[400px] border rounded-xl p-3 text-xs md:text-sm">
            <div dangerouslySetInnerHTML={{ __html: previewTable }} />
          </div>
        </div>
      )}

      {/* TABLE + CRUD */}
      <div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md">
        {/* HEADER + SEARCH */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-3">
          <h2 className="text-xl font-bold">Data Karyawan</h2>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Cari data..."
              className="border p-2 rounded-lg text-sm"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
            />
            <button
              className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded-lg"
              onClick={() => {
                setShowModal(true);
                setIsEdit(false);
                setForm({ nama: "", nik: "", jabatan: "", dept: "" });
              }}
            >
              <Plus size={16} /> Tambah
            </button>
          </div>
        </div>

        {/* TABLE */}
        <div className="overflow-auto">
          <table className="min-w-full border text-xs md:text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-2">No</th>
                {cols.map(c => <th key={c} className="border p-2">{c.toUpperCase()}</th>)}
                <th className="border p-2">Action</th>
              </tr>
            </thead>

            <tbody>
              {data.map((d, i) => (
                <tr key={d.nik}>
                  <td className="border p-2 text-center">{(currentPage - 1) * rowsPerPage + i + 1}</td>
                  {cols.map(col => (
                    <td className="border p-2" key={col}>
                      {editingNik === d.nik ? (
                        <input
                          type="text"
                          className={`border px-2 py-1 w-full ${col === "nik" ? "bg-gray-200 cursor-not-allowed" : ""}`}
                          value={form[col] || ""}
                          onChange={e => col === "nik" ? null : setForm({ ...form, [col]: e.target.value })}
                          disabled={col === "nik"}
                        />
                      ) : d[col]}
                    </td>
                  ))}
                  <td className="border p-2 flex gap-2">
                    {editingNik === d.nik ? (
                      <button
                        onClick={() => saveData()}
                        className="bg-blue-600 text-white px-2 py-1 rounded text-xs"
                      >
                        Update
                      </button>
                    ) : (
                      <button
                        onClick={() => editData(d)}
                        className="bg-yellow-500 text-white px-2 py-1 rounded text-xs"
                      >
                        Edit
                      </button>
                    )}
                    <button
                      onClick={() => removeData(d.nik)}
                      className="bg-red-600 text-white px-2 py-1 rounded flex items-center gap-1 text-xs"
                    >
                      <Trash2 size={14} /> Hapus
                    </button>
                  </td>
                </tr>
              ))}

              {data.length === 0 && (
                <tr>
                  <td className="border p-4 text-center" colSpan={cols.length + 2}>
                    Tidak ada data ditemukan.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* SMART PAGINATION */}
        {totalPages > 1 && (
          <div className="flex justify-center mt-4 gap-2">
            <button
              className="px-3 py-1 border rounded disabled:opacity-50"
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Prev
            </button>

            {/* Page Logic */}
            {(() => {
              const pages = [];
              const maxPages = 5;

              // Always show first page
              if (currentPage > 3) {
                pages.push(1);
                if (currentPage !== 4) pages.push("...");
              }

              // Middle Pages
              const start = Math.max(1, currentPage - 1);
              const end = Math.min(totalPages, currentPage + 1);

              for (let i = start; i <= end; i++) {
                pages.push(i);
              }

              // Show last pages
              if (currentPage < totalPages - 2) {
                if (currentPage !== totalPages - 3) pages.push("...");
                pages.push(totalPages);
              }

              return pages.map((p, idx) =>
                p === "..." ? (
                  <span key={idx} className="px-3 py-1">...</span>
                ) : (
                  <button
                    key={idx}
                    className={`px-3 py-1 border rounded ${
                      currentPage === p ? "bg-green-600 text-white" : ""
                    }`}
                    onClick={() => setCurrentPage(p)}
                  >
                    {p}
                  </button>
                )
              );
            })()}

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

      {/* MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
          <div className="bg-white p-6 rounded-xl w-96">
            <h3 className="text-lg font-bold mb-4">{isEdit ? "Edit Data Karyawan" : "Tambah Data Karyawan"}</h3>

            {cols.map(col => (
              <input
                key={col}
                value={form[col]}
                onChange={e => setForm({ ...form, [col]: e.target.value })}
                placeholder={col.toUpperCase()}
                disabled={isEdit && col === "nik"}
                className={`border p-2 w-full mb-2 rounded ${isEdit && col === "nik" ? "bg-gray-200 cursor-not-allowed" : ""}`}
              />
            ))}

            <div className="flex justify-end gap-2 mt-4">
              <button 
                onClick={() => { 
                  setShowModal(false); 
                  setIsEdit(false);
                  setEditingNik(null);
                }} 
                className="px-3 py-1 border rounded"
              >
                Batal
              </button>
              <button 
                onClick={saveData} 
                disabled={loading}
                className="px-3 py-1 bg-green-600 text-white rounded disabled:opacity-60"
              >
                Simpan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}