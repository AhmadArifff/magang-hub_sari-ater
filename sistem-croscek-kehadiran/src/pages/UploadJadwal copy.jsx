// frontend/src/pages/UploadJadwal.jsx
import { useState, useEffect } from "react";
import { UploadCloud, FileSpreadsheet, Trash2 } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

// API backend
import {
  apiFetchSchedules,
  apiUploadSchedule,
  apiActivateSchedule,
  apiDeleteSchedule,
  apiDownloadSchedule
} from "../utils/api";

export default function UploadJadwal() {
  const [htmlTable, setHtmlTable] = useState("");
  const [currentFile, setCurrentFile] = useState(null);
  const [scheduleList, setScheduleList] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSchedules();
  }, []);

  const loadSchedules = async () => {
    try {
      setLoading(true);
      const data = await apiFetchSchedules();
      setScheduleList(data || []);
    } catch (e) {
      console.error("Failed to load schedules:", e);
      setScheduleList([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setCurrentFile(file);

    // preview using SheetJS
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: "array" });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];

    let html = XLSX.utils.sheet_to_html(sheet);

    html = html
      .replace(/<table/g, `<table class='min-w-full border border-gray-300 text-xs md:text-sm bg-white'`)
      .replace(/<td/g, `<td class='border border-gray-300 px-2 md:px-3 py-2 whitespace-nowrap'`)
      .replace(/<th/g, `<th class='border border-gray-300 bg-gray-100 px-2 md:px-3 py-2 text-center font-semibold'`);

    setHtmlTable(html);
  };

  const handleSave = async () => {
    if (!currentFile) return alert("Tidak ada file untuk disimpan!");

    try {
      setLoading(true);
      await apiUploadSchedule(currentFile);
      await loadSchedules();
      alert("Data berhasil di-upload ke server!");
      setCurrentFile(null);
      setHtmlTable("");
    } catch (err) {
      console.error(err);
      alert("Gagal upload file: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="bg-white p-4 md:p-6 rounded-2xl shadow-md flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
        <img src={sariAter} alt="Sari Ater" className="w-20 md:w-28 object-contain" />

        <div>
          <h1 className="text-xl md:text-2xl font-bold">Upload Informasi Jadwal</h1>
          <p className="text-gray-600">Upload file Excel untuk melihat dan menyimpan jadwal.</p>
        </div>
      </div>

      {/* UPLOAD */}
      <label className="mt-6 block w-full border-2 border-dashed border-[#1BA39C] bg-white hover:bg-[#e9f7f7] transition cursor-pointer rounded-xl p-10 md:p-14 text-center">
        <UploadCloud size={40} className="text-[#1BA39C] mx-auto" />
        <p className="text-gray-700 font-medium mt-3 text-sm md:text-base">Klik untuk Upload File Excel</p>

        <input type="file" onChange={handleFileUpload} accept=".xls,.xlsx" className="hidden" />
      </label>

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

      {/* TABLE LIST */}
      <div className="bg-white mt-10 p-4 md:p-6 rounded-2xl shadow-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Data Informasi Jadwal Tersimpan</h2>
          <div className="text-sm text-gray-600">{loading ? "Loading..." : `${scheduleList.length} item`}</div>
        </div>

        <div className="overflow-auto">
          <table className="min-w-full border text-xs md:text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="border p-2">No</th>
                <th className="border p-2">Nama Informasi Jadwal</th>
                <th className="border p-2">File Jadwal</th>
                <th className="border p-2">Tanggal Upload</th>
                <th className="border p-2">Status</th>
                <th className="border p-2">Action</th>
              </tr>
            </thead>

            <tbody>
              {scheduleList.map((item, index) => (
                <tr key={item.id}>
                  <td className="border p-2 text-center">{index + 1}</td>

                  <td className="border p-2">{item.name}</td>

                  <td
                    className="border p-2 text-blue-700 underline cursor-pointer"
                    onClick={() => apiDownloadSchedule(item)}
                  >
                    {item.originalName || item.fileName}
                  </td>

                  <td className="border p-2">{new Date(item.uploadedAt).toLocaleString()}</td>

                  <td className="border p-2 text-center">
                    <span className={`px-3 py-1 rounded-full text-white text-xs ${item.status === "active" ? "bg-green-600" : "bg-gray-500"}`}>{item.status}</span>
                  </td>

                  <td className="border p-2 flex flex-col md:flex-row gap-2 justify-center">
                    <button
                      onClick={async () => {
                        try {
                          setLoading(true);
                          await apiActivateSchedule(item.id);
                          await loadSchedules();
                        } catch (e) {
                          console.error(e);
                          alert("Gagal set active");
                        } finally {
                          setLoading(false);
                        }
                      }}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-xs md:text-sm"
                    >
                      Jadikan Active
                    </button>

                    <button
                      onClick={async () => {
                        if (!confirm("Hapus file ini?")) return;
                        try {
                          setLoading(true);
                          await apiDeleteSchedule(item.id);
                          await loadSchedules();
                        } catch (e) {
                          console.error(e);
                          alert("Gagal hapus file");
                        } finally {
                          setLoading(false);
                        }
                      }}
                      className="bg-red-600 text-white px-3 py-1 rounded flex items-center gap-1 text-xs md:text-sm"
                    >
                      <Trash2 size={14} /> Hapus
                    </button>
                  </td>
                </tr>
              ))}

              {scheduleList.length === 0 && (
                <tr>
                  <td className="border p-4 text-center" colSpan={6}>Belum ada data jadwal.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
