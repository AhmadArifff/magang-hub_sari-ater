import { Link, useLocation } from "react-router-dom";
import { FileSpreadsheet, CheckSquare, Menu, X, Users } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import sariAter from "../assets/sari-ater.png";

export default function Sidebar() {
  const { pathname } = useLocation();

  // Desktop detect
  const isDesktop = window.innerWidth >= 768;

  // Desktop collapse/expand (controlled by hover)
  const [open, setOpen] = useState(true);

  // Mobile drawer state
  const [mobileOpen, setMobileOpen] = useState(false);

  // Ref for touch control
  const sidebarRef = useRef(null);
  const containerRef = useRef(null); // Ref untuk container utama agar bisa deteksi swipe buka

  // Mobile drag gesture untuk geser tutup sidebar
  useEffect(() => {
    const el = sidebarRef.current;
    if (!el) return;

    let startX = 0;
    let currentX = 0;
    let dragging = false;

    const touchStart = (e) => {
      dragging = true;
      startX = e.touches[0].clientX;
    };

    const touchMove = (e) => {
      if (!dragging) return;

      currentX = e.touches[0].clientX;

      const diff = currentX - startX;

      // Geser hanya saat sidebar terbuka
      if (mobileOpen) {
        el.style.transform = `translateX(${Math.min(0, diff)}px)`;
      }
    };

    const touchEnd = () => {
      if (!dragging) return;
      dragging = false;

      const diff = currentX - startX;

      // Jika geser > 80 pixel ke kiri → tutup
      if (diff < -80) {
        setMobileOpen(false);
      }

      el.style.transform = "";
    };

    el.addEventListener("touchstart", touchStart);
    el.addEventListener("touchmove", touchMove);
    el.addEventListener("touchend", touchEnd);

    return () => {
      el.removeEventListener("touchstart", touchStart);
      el.removeEventListener("touchmove", touchMove);
      el.removeEventListener("touchend", touchEnd);
    };
  }, [mobileOpen]);

  // Mobile swipe gesture untuk buka drawer dari kiri (geser dari kiri)
  useEffect(() => {
    if (isDesktop || !containerRef.current) return;

    const el = containerRef.current;
    let startX = 0;
    let currentX = 0;
    let dragging = false;

    const touchStart = (e) => {
      startX = e.touches[0].clientX;
      if (startX > 50) return; // Hanya swipe dari kiri (x < 50)
      dragging = true;
    };

    const touchMove = (e) => {
      if (!dragging) return;
      currentX = e.touches[0].clientX;
      const diff = currentX - startX;

      if (!mobileOpen && diff > 0) {
        sidebarRef.current.style.transform = `translateX(${Math.max(-256, -256 + diff)}px)`; // Asumsi w-64 = 256px
      }
    };

    const touchEnd = () => {
      if (!dragging) return;
      dragging = false;

      const diff = currentX - startX;

      if (diff > 80) setMobileOpen(true);
      if (sidebarRef.current) sidebarRef.current.style.transform = "";
    };

    el.addEventListener("touchstart", touchStart);
    el.addEventListener("touchmove", touchMove);
    el.addEventListener("touchend", touchEnd);

    return () => {
      el.removeEventListener("touchstart", touchStart);
      el.removeEventListener("touchmove", touchMove);
      el.removeEventListener("touchend", touchEnd);
    };
  }, [mobileOpen, isDesktop]);

  // Detect desktop → auto collapse on hover
  const handleMouseEnter = () => {
    if (isDesktop) setOpen(true);
  };

  const handleMouseLeave = () => {
    if (isDesktop) setOpen(false);
  };

  const menu = [
    { label: "Upload Informasi Jadwal", icon: FileSpreadsheet, path: "/" },
    { label: "Croscek Jadwal", icon: CheckSquare, path: "/croscek" },
    { label: "Data Karyawan", icon: Users, path: "/karyawan" }
  ];

  return (
    <div ref={containerRef} className="relative min-h-screen">
      {/* MOBILE HAMBURGER ICON DI POJOK KIRI ATAS */}
      <button
        className="md:hidden fixed top-4 left-4 z-50 bg-[#0f6160] text-white p-2 rounded-full shadow-lg"
        onClick={() => setMobileOpen(true)}
      >
        <Menu size={24} />
      </button>

      {/* MOBILE OVERLAY */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* SIDEBAR */}
      <aside
        ref={sidebarRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={`
          fixed md:static top-0 left-0 z-50 min-h-screen 
          bg-[#0f6160] text-white flex flex-col shadow-xl
          transition-all duration-300

          ${open ? "md:w-64" : "md:w-20"}
          ${mobileOpen ? "w-64 translate-x-0" : "-translate-x-full w-64 md:translate-x-0"}
        `}
      >
        {/* MOBILE CLOSE BUTTON */}
        <button
          className="md:hidden absolute top-4 right-4 text-white"
          onClick={() => setMobileOpen(false)}
        >
          <X size={28} />
        </button>

        {/* LOGO */}
        <div className="flex flex-col items-center py-8">
          <img
            src={sariAter}
            className={`transition-all duration-300 ${
              open ? "w-28 h-28" : "w-10 h-10"
            }`}
            alt="Sari Ater"
          />

          {open && (
            <h1 className="text-xl font-bold mt-3 text-center">
              Sari Ater Hot Spring
            </h1>
          )}
        </div>

        {/* MENU */}
        <nav className="flex flex-col gap-2 px-3">
          {menu.map((m) => {
            const Icon = m.icon;
            const active = pathname === m.path;

            return (
              <Link
                key={m.path}
                to={m.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition font-medium
                  ${
                    active
                      ? "bg-white text-[#0f6160] shadow-md"
                      : "hover:bg-white/20"
                  }`}
              >
                <Icon size={20} />
                {open && <span>{m.label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>
    </div>
  );
}
