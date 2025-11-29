import { useEffect, useState } from "react";
import * as XLSX from "xlsx";
import { loadExcel } from "../utils/fileStorage";
import { FileSpreadsheet } from "lucide-react";

export default function AdminJadwalView() {
  const [htmlTable, setHtmlTable] = useState("");

  useEffect(() => {
    const load = async () => {
      const file = await loadExcel();
      if (!file) {
        setHtmlTable("<p class='text-red-600'>Belum ada file jadwal diupload.</p>");
        return;
      }

      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];

      let html = XLSX.utils.sheet_to_html(sheet);

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
    };

    load();
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-10">
      <h1 className="text-3xl font-bold mb-5 flex gap-3 items-center">
        <FileSpreadsheet /> Informasi Jadwal Bulanan
      </h1>

      <div className="bg-white p-6 rounded-xl shadow">
        <div dangerouslySetInnerHTML={{ __html: htmlTable }} />
      </div>
    </div>
  );
}
