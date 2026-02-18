import { BrowserRouter, Routes, Route } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import UploadJadwal from "./pages/UploadJadwal";
import Croscek from "./pages/Croscek";
import UploadKaryawan from "./pages/DataKaryawan";
import Croscek_DW from "./pages/Croscek-DW";
import UploadKaryawan_DW from "./pages/DataKaryawan-DW";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<UploadJadwal />} />
          <Route path="/croscek-karyawan" element={<Croscek />} />
          <Route path="/karyawan" element={<UploadKaryawan />} />
          <Route path="/croscek-dw" element={<Croscek_DW />} />
          <Route path="/dw" element={<UploadKaryawan_DW />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
