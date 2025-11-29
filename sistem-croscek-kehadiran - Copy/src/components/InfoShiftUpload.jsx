import { useState } from "react";
import { UploadCloud, FileSpreadsheet } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

export default function InfoShiftUpload() {
  const [htmlTable, setHtmlTable] = useState("");

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = file.name.split(".").pop().toLowerCase();

    if (["xls", "xlsx"].includes(ext)) {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];

      // Convert sheet Excel → HTML aslinya
      let html = XLSX.utils.sheet_to_html(sheet);

      // Bersihkan style default SheetJS agar Tailwind tidak bentrok
      html = html.replace(
        /<table/g,
        `<table class='min-w-full border border-gray-300 !w-full text-sm'`
      );

      html = html.replace(
        /<td/g,
        `<td class='border border-gray-300 px-3 py-2 whitespace-nowrap'`
      );

      html = html.replace(
        /<th/g,
        `<th class='border border-gray-300 bg-gray-100 px-3 py-2 text-center font-semibold'`
      );

      setHtmlTable(html);
      return;
    }

    alert("Format file tidak didukung (hanya Excel).");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f6160] to-[#1BA39C] py-10 px-4 flex flex-col items-center">
      
      {/* HEADER */}
      <div className="w-full max-w-5xl bg-white/90 p-8 rounded-2xl shadow-xl">
        <div className="flex items-center gap-6">
          <img src={sariAter} alt="Sari Ater" className="w-40 h-40 object-contain" />
          
          <div>
            <h1 className="text-3xl font-bold">Upload Informasi Jadwal</h1>
            <p className="text-gray-600 mt-1">Upload file Excel lalu lihat preview-nya.</p>
          </div>
        </div>

        <label className="mt-8 w-full border-2 border-dashed border-[#1BA39C] bg-white hover:bg-[#e9f7f7] transition cursor-pointer rounded-xl p-10 flex flex-col justify-center items-center">
          <UploadCloud size={50} className="text-[#1BA39C]" />
          <p className="text-gray-700 font-medium mt-3">Klik untuk Upload File Excel</p>

          <input type="file" onChange={handleFileUpload} accept=".xls,.xlsx" className="hidden" />
        </label>
      </div>

      {/* PREVIEW */}
      {htmlTable && (
        <div className="w-full max-w-5xl bg-white mt-10 p-8 rounded-2xl shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <FileSpreadsheet className="text-green-700" size={28} />
            <h2 className="text-2xl font-bold">Preview Data</h2>
          </div>

          <div className="overflow-auto max-h-[600px] border rounded-xl p-3">
            {/* Render HTML asli dari Excel */}
            <div
              dangerouslySetInnerHTML={{ __html: htmlTable }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
