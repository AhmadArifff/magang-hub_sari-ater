import { BrowserRouter, Routes, Route } from "react-router-dom";
import DashboardLayout from "./layouts/DashboardLayout";
import UploadJadwal from "./pages/UploadJadwal";
import Croscek from "./pages/Croscek";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<UploadJadwal />} />
          <Route path="/croscek" element={<Croscek />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
