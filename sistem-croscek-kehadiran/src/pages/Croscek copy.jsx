// src/pages/Croscek.jsx
import { useState, useEffect, useRef } from "react";
import { UploadCloud, Search } from "lucide-react";
import * as XLSX from "xlsx";
import sariAter from "../assets/sari-ater.png";

import { apiFetchSchedules, apiFetchFileBlob } from "../utils/api";

export default function Croscek() {
  const [infoList, setInfoList] = useState([]);
  const [selectedInfo, setSelectedInfo] = useState(null);
  const [infoMap, setInfoMap] = useState({});

  const [rosterHtml, setRosterHtml] = useState("");
  const [rosterTableRaw, setRosterTableRaw] = useState(null);
  const [attendanceRows, setAttendanceRows] = useState([]);
  const [hasilHtml, setHasilHtml] = useState("");
  const [filterNama, setFilterNama] = useState("");
  const [loading, setLoading] = useState(false);

  const rosterInputRef = useRef();
  const hadirInputRef = useRef();

  // Load info jadwal dari server
  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetchSchedules();
        setInfoList(data || []);
      } catch (e) {
        console.error("Gagal ambil info jadwal:", e);
      }
    })();
  }, []);

  // Saat info jadwal dipilih, fetch file dan buat map kode->jam
  useEffect(() => {
    if (!selectedInfo) return setInfoMap({});
    (async () => {
      try {
        setLoading(true);
        const blob = await apiFetchFileBlob(selectedInfo.fileName);
        const arrayBuffer = await blob.arrayBuffer();
        const wb = XLSX.read(arrayBuffer, { type: "array" });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        const raw = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });

        // Cari kolom Kode, Masuk, Pulang, Nama
        const headerRows = raw.slice(0, 3);
        let kodeCol = -1, masukCol = -1, pulangCol = -1, namaCol = -1;

        for (let r = 0; r < headerRows.length; r++) {
          const row = headerRows[r];
          if (!row) continue;
          for (let c = 0; c < row.length; c++) {
            const v = String(row[c] || "").toLowerCase().trim();
            if (!v) continue;
            if (v.includes("kode") && kodeCol === -1) kodeCol = c;
            if ((v.includes("masuk") || v === "masuk") && masukCol === -1) masukCol = c;
            if ((v.includes("pulang") || v === "pulang") && pulangCol === -1) pulangCol = c;
            if ((v.includes("nama") || v.includes("lokasi kerja")) && namaCol === -1) namaCol = c;
            if (v.includes("jam") && headerRows[r + 1]) {
              const nextRow = headerRows[r + 1];
              for (let cc = 0; cc < nextRow.length; cc++) {
                const vv = String(nextRow[cc] || "").toLowerCase().trim();
                if (vv.includes("masuk")) masukCol = cc;
                if (vv.includes("pulang")) pulangCol = cc;
              }
            }
          }
        }

        // Fallback jika tidak ketemu
        if (kodeCol === -1) kodeCol = 0;
        if (namaCol === -1) namaCol = 1;

        // Data dimulai setelah headerRows
        let dataStart = 3;
        while (dataStart < raw.length && !String(raw[dataStart][kodeCol] || "").trim()) dataStart++;

        const map = {};
        for (let r = dataStart; r < raw.length; r++) {
          const row = raw[r];
          if (!row) continue;
          const code = String(row[kodeCol] || "").trim();
          if (!code) continue;
          map[code] = {
            code,
            nama: String(row[namaCol] || "").trim(),
            masuk: String(row[masukCol] || "").trim(),
            pulang: String(row[pulangCol] || "").trim(),
          };
        }

        setInfoMap(map);
      } catch (e) {
        console.error("Gagal parse info jadwal:", e);
        setInfoMap({});
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedInfo]);

  // Parse attendance Excel
  const parseAttendanceRows = async (file) => {
    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer, { type: "array" });
    const sheet = wb.Sheets[wb.SheetNames[0]];
    const json = XLSX.utils.sheet_to_json(sheet, { defval: "" });

    return json.map((r) => {
      const normalized = {};
      for (const k of Object.keys(r)) normalized[k.trim()] = r[k];
      return normalized;
    });
  };

  const buildAttendanceMap = (rows) => {
    const keys = rows.length ? Object.keys(rows[0]) : [];
    const keyDate = keys.find((k) => /tanggal/i.test(k)) || "Tanggal";
    const keyTime = keys.find((k) => /jam/i.test(k)) || "Jam";
    const keyNama = keys.find((k) => /nama/i.test(k)) || "Nama";

    const map = {};
    for (const r of rows) {
      const rawDate = r[keyDate];
      const rawTime = r[keyTime];
      const nama = String(r[keyNama] || "").trim();
      if (!nama || !rawDate) continue;

      let dateObj;
      if (rawDate instanceof Date) dateObj = rawDate;
      else {
        const s = String(rawDate).trim();
        if (/^\d{1,2}[-\/]\d{1,2}[-\/]\d{4}$/.test(s)) {
          const parts = s.split(/[-\/]/);
          dateObj = new Date(`${parts[2]}-${parts[1]}-${parts[0]}T00:00:00`);
        } else {
          const tryDate = new Date(s);
          if (!isNaN(tryDate)) dateObj = tryDate;
        }
      }
      if (!dateObj) continue;
      const ymd = dateObj.toISOString().slice(0, 10);

      let timeStr = "";
      if (rawTime instanceof Date) timeStr = rawTime.toTimeString().slice(0, 8);
      else {
        const m = String(rawTime).trim().match(/(\d{1,2}:\d{2})(:\d{2})?/);
        if (m) timeStr = m[1] + (m[2] || ":00");
      }
      if (!timeStr) continue;

      const key = `${nama}|${ymd}`;
      if (!map[key]) map[key] = { checkins: [], checkouts: [], nama, date: ymd };
      map[key].checkins.push(timeStr);
      map[key].checkouts.push(timeStr);
    }
    return map;
  };

  const handleUploadRoster = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer, { type: "array" });
    const sheet = wb.Sheets[wb.SheetNames[0]];
    setRosterHtml(XLSX.utils.sheet_to_html(sheet));
    setRosterTableRaw(XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" }));
  };

  const handleUploadAttendance = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const rows = await parseAttendanceRows(file);
    setAttendanceRows(rows);
  };

  const handleProses = async () => {
    if (!rosterTableRaw) return alert("Upload roster terlebih dahulu.");
    if (!selectedInfo) return alert("Pilih info jadwal yang valid.");
    if (!attendanceRows.length) return alert("Upload kehadiran terlebih dahulu.");

    setLoading(true);
    try {
      const attendanceMap = buildAttendanceMap(attendanceRows);

      // Proses roster
      const dayHeaderRowIdx = rosterTableRaw.findIndex(row => row.some(c => /^\d{1,2}$/.test(String(c || ""))));
      const nameCol = rosterTableRaw[dayHeaderRowIdx - 1]?.findIndex(c => String(c).toLowerCase().includes("nama")) ?? 1;
      const dayCols = rosterTableRaw[dayHeaderRowIdx]
        .map((v, i) => (/^\d{1,2}$/.test(String(v)) ? i : -1))
        .filter(i => i >= 0);
      const dataStart = dayHeaderRowIdx + 1;

      const hasil = [];
      for (let r = dataStart; r < rosterTableRaw.length; r++) {
        const row = rosterTableRaw[r];
        if (!row) continue;
        const nama = String(row[nameCol] || "").trim();
        if (!nama) continue;

        for (const col of dayCols) {
          const kode = String(row[col] || "").trim();
          if (!kode) continue;
          let year = new Date().getFullYear();
          let month = new Date().getMonth() + 1;
          for (let rr = 0; rr < 3; rr++) {
            const txt = (rosterTableRaw[rr] || []).join(" ");
            const m = txt.match(/([A-Za-z]+)\s+(\d{4})/);
            if (m) {
              const monthNames = { january:1,february:2,march:3,april:4,may:5,june:6,july:7,august:8,september:9,october:10,november:11,december:12,
                                  januari:1,februari:2,maret:3,april:4,mei:5,juni:6,juli:7,agustus:8,september:9,oktober:10,november:11,desember:12};
              const key = m[1].toLowerCase();
              if (monthNames[key]) { month = monthNames[key]; year = Number(m[2]); }
              break;
            }
          }
          const ymd = `${year}-${String(month).padStart(2,"0")}-${String(rowHeaderDay(col,dayHeaderRowIdx)).padStart(2,"0")}`;
          const info = infoMap[kode] || {};
          const key = `${nama}|${ymd}`;
          const att = attendanceMap[key];

          let actualMasuk = "", actualPulang = "", status = "Tidak Hadir";
          const expectedMasuk = info.masuk || "";
          const expectedPulang = info.pulang || "";

          if (att) {
            const min = att.checkins.reduce((a,b)=>a<b?a:b, att.checkins[0]);
            const max = att.checkouts.reduce((a,b)=>a>b?a:b, att.checkouts[0]);
            actualMasuk = min;
            actualPulang = max;

            const toSec = t => {
              if (!t) return 0;
              const [hh,mm,ss] = String(t).split(":").map(Number);
              return hh*3600+mm*60+(ss||0);
            };

            const emSec = toSec(expectedMasuk);
            const epSec = toSec(expectedPulang);
            const amSec = toSec(actualMasuk);
            const apSec = toSec(actualPulang);

            if (amSec <= emSec && apSec >= epSec) status = "Tepat Waktu";
            else if (amSec <= emSec && apSec < epSec) status = "Masuk Tepat, Pulang Cepat";
            else if (amSec > emSec && apSec >= epSec) status = "Telat, Pulang Tepat";
            else if (amSec > emSec && apSec < epSec) status = "Telat, Pulang Cepat";
          }

          hasil.push({
            Nama: nama,
            Tanggal: ymd,
            Kode: kode,
            "Jadwal Masuk": expectedMasuk,
            "Jadwal Pulang": expectedPulang,
            "Actual Masuk": actualMasuk || "-",
            "Actual Pulang": actualPulang || "-",
            Status: status,
          });
        }
      }

      // Filter nama
      const filtered = filterNama ? hasil.filter(h => h.Nama.toLowerCase().includes(filterNama.toLowerCase())) : hasil;

      // Build HTML
      let tableHtml = `<table class="min-w-full border border-gray-300 text-sm"><thead class="bg-gray-100"><tr>
        <th class="border px-3 py-2">Nama</th>
        <th class="border px-3 py-2">Tanggal</th>
        <th class="border px-3 py-2">Kode</th>
        <th class="border px-3 py-2">Jadwal Masuk</th>
        <th class="border px-3 py-2">Jadwal Pulang</th>
        <th class="border px-3 py-2">Actual Masuk</th>
        <th class="border px-3 py-2">Actual Pulang</th>
        <th class="border px-3 py-2">Status</th>
      </tr></thead><tbody>`;

      for (const row of filtered) {
        const badge = row.Status.includes("Tepat Waktu") ? "bg-green-100 text-green-700" :
                      row.Status.includes("Telat") ? "bg-red-100 text-red-700" :
                      "bg-yellow-100 text-yellow-700";
        tableHtml += `<tr>
          <td class="border px-3 py-2">${row.Nama}</td>
          <td class="border px-3 py-2">${row.Tanggal}</td>
          <td class="border px-3 py-2">${row.Kode}</td>
          <td class="border px-3 py-2">${row["Jadwal Masuk"]}</td>
          <td class="border px-3 py-2">${row["Jadwal Pulang"]}</td>
          <td class="border px-3 py-2">${row["Actual Masuk"]}</td>
          <td class="border px-3 py-2">${row["Actual Pulang"]}</td>
          <td class="border px-3 py-2"><span class="${badge} px-2 py-1 rounded">${row.Status}</span></td>
        </tr>`;
      }

      tableHtml += "</tbody></table>";
      setHasilHtml(tableHtml);

    } catch (e) {
      console.error(e);
      alert("Gagal memproses croscek");
    } finally {
      setLoading(false);
    }
  };

  // Helper: dapatkan hari dari header
  const rowHeaderDay = (colIdx, dayHeaderRowIdx) => {
    return Number(rosterTableRaw[dayHeaderRowIdx][colIdx] || 1);
  };

  return (
    <div className="w-full space-y-6 p-4">
      <div className="bg-white p-6 rounded-2xl shadow-md flex items-center gap-6">
        <img src={sariAter} alt="Sari Ater" className="w-28 object-contain" />
        <div>
          <h1 className="text-2xl font-bold">Croscek Jadwal Karyawan</h1>
          <p className="text-gray-600">Upload file roster & kehadiran, lalu pilih informasi jadwal.</p>
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl shadow flex items-center gap-4">
        <label className="text-sm font-medium">Pilih Informasi Jadwal</label>
        <select
          className="border p-2 rounded ml-2"
          value={selectedInfo?.id || ""}
          onChange={e => setSelectedInfo(infoList.find(x=>x.id===e.target.value)||null)}
        >
          <option value="">-- pilih info jadwal --</option>
          {infoList.map(it=>(
            <option key={it.id} value={it.id}>{it.name} ({new Date(it.uploadedAt).toLocaleDateString()})</option>
          ))}
        </select>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-md">
          <h2 className="text-lg font-semibold mb-3">Upload Roster Bulanan</h2>
          <label className="w-full border-2 border-dashed border-[#1BA39C] p-6 rounded-xl flex flex-col items-center cursor-pointer">
            <UploadCloud size={36} className="text-[#1BA39C]" />
            <p className="mt-2 text-sm">Pilih file roster Excel</p>
            <input ref={rosterInputRef} type="file" accept=".xls,.xlsx" onChange={handleUploadRoster} className="hidden" />
          </label>
          {rosterHtml && <div className="mt-4 border rounded p-2 overflow-auto max-h-48" dangerouslySetInnerHTML={{ __html: rosterHtml }} />}
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-md">
          <h2 className="text-lg font-semibold mb-3">Upload Kehadiran</h2>
          <label className="w-full border-2 border-dashed border-[#1BA39C] p-6 rounded-xl flex flex-col items-center cursor-pointer">
            <UploadCloud size={36} className="text-[#1BA39C]" />
            <p className="mt-2 text-sm">Pilih file absensi Excel</p>
            <input ref={hadirInputRef} type="file" accept=".xls,.xlsx" onChange={handleUploadAttendance} className="hidden" />
          </label>
          <div className="mt-4 text-sm text-gray-600">{attendanceRows.length ? `${attendanceRows.length} record kehadiran ter-upload` : "Belum upload kehadiran"}</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button onClick={handleProses} className="px-6 py-2 bg-[#1BA39C] text-white rounded-xl" disabled={loading}>Proses Croscek</button>
        <div className="flex items-center gap-2 bg-white p-2 rounded shadow ml-4">
          <Search />
          <input value={filterNama} onChange={e=>setFilterNama(e.target.value)} placeholder="Filter nama (opsional)" className="border-none outline-none" />
        </div>
      </div>

      <div>
        {hasilHtml ? (
          <div className="bg-white p-4 rounded-xl shadow overflow-auto" dangerouslySetInnerHTML={{ __html: hasilHtml }} />
        ) : <div className="text-gray-500">Hasil akan muncul di sini setelah proses.</div>}
      </div>
    </div>
  );
}
