import { Link, useLocation } from "react-router-dom";
import {
  FileSpreadsheet,
  CheckSquare,
  Menu,
  X,
  Users,
  ChevronDown,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import sariAter from "../assets/sari-ater.png";

export default function Sidebar() {
  const { pathname } = useLocation();
  const isDesktop = window.innerWidth >= 768;

  const [open, setOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  // state expand parent menu
  const [expanded, setExpanded] = useState({
    karyawan: true,
    dw: true,
  });

  const sidebarRef = useRef(null);
  const containerRef = useRef(null);

  /* ================= MOBILE GESTURE (UNCHANGED) ================= */
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

      if (mobileOpen) {
        el.style.transform = `translateX(${Math.min(0, diff)}px)`;
      }
    };

    const touchEnd = () => {
      if (!dragging) return;
      dragging = false;

      if (currentX - startX < -80) setMobileOpen(false);
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

  useEffect(() => {
    if (isDesktop || !containerRef.current) return;

    const el = containerRef.current;
    let startX = 0;
    let currentX = 0;
    let dragging = false;

    const touchStart = (e) => {
      startX = e.touches[0].clientX;
      if (startX > 50) return;
      dragging = true;
    };

    const touchMove = (e) => {
      if (!dragging) return;
      currentX = e.touches[0].clientX;

      if (!mobileOpen && currentX - startX > 0) {
        sidebarRef.current.style.transform = `translateX(${Math.max(
          -256,
          -256 + (currentX - startX)
        )}px)`;
      }
    };

    const touchEnd = () => {
      if (!dragging) return;
      dragging = false;

      if (currentX - startX > 80) setMobileOpen(true);
      sidebarRef.current.style.transform = "";
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

  const handleMouseEnter = () => isDesktop && setOpen(true);
  const handleMouseLeave = () => isDesktop && setOpen(false);

  /* ================= MENU TREE ================= */
  const menuTree = [
    {
      key: "karyawan",
      label: "Croscek Karyawan",
      icon: Users,
      children: [
        {
          label: "Croscek Jadwal Karyawan",
          icon: CheckSquare,
          path: "/croscek-karyawan",
        },
        {
          label: "Data Karyawan",
          icon: Users,
          path: "/karyawan",
        },
      ],
    },
    {
      key: "dw",
      label: "Croscek Daily Worker (DW)",
      icon: Users,
      children: [
        {
          label: "Croscek Jadwal DW",
          icon: CheckSquare,
          path: "/croscek-dw",
        },
        {
          label: "Data Daily Worker (DW)",
          icon: Users,
          path: "/dw",
        },
      ],
    },
  ];

  return (
    <div ref={containerRef} className="relative min-h-screen">
      <button
        className="md:hidden fixed top-4 left-4 z-50 bg-[#0f6160] text-white p-2 rounded-full"
        onClick={() => setMobileOpen(true)}
      >
        <Menu size={24} />
      </button>

      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        ref={sidebarRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={`fixed md:static top-0 left-0 z-50 min-h-screen 
        bg-gradient-to-b from-[#0f6160] via-[#0d4f48] to-[#0a3a34]
        text-white flex flex-col transition-all duration-300 overflow-hidden
        ${open ? "md:w-64" : "md:w-20"}
        ${mobileOpen ? "w-64" : "-translate-x-full md:translate-x-0"}`}
        style={{
          backgroundImage: `
            radial-gradient(circle at 20% 50%, rgba(15, 97, 96, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(13, 79, 72, 0.3) 0%, transparent 50%),
            linear-gradient(135deg, #0f6160 0%, #0a3a34 100%)
          `,
        }}
      >
        {/* Animated background elements */}
        <div className="absolute inset-0 opacity-5 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-white rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white rounded-full blur-3xl animate-pulse" style={{animationDelay: '1s'}}></div>
        </div>

        <div className="relative z-10 flex flex-col items-center py-8">
          <div className="bg-white/10 backdrop-blur-md p-3 rounded-2xl border border-white/20 hover:bg-white/20 transition-all">
            <img
              src={sariAter}
              className={`${open ? "w-28 h-28" : "w-10 h-10"} transition-all`}
              alt="logo"
            />
          </div>
          {open && (
            <h1 className="text-xl font-bold mt-4 text-center bg-gradient-to-r from-white via-blue-200 to-cyan-200 bg-clip-text text-transparent">
              Sari Ater Hot Spring
            </h1>
          )}
        </div>

        <nav className="px-3 space-y-3 relative z-10">
          {menuTree.map((group) => {
            const Icon = group.icon;
            return (
              <div key={group.key}>
                {/* PARENT */}
                <button
                  onClick={() =>
                    setExpanded((prev) => ({
                      ...prev,
                      [group.key]: !prev[group.key],
                    }))
                  }
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl hover:bg-white/20 backdrop-blur-sm border border-white/10 hover:border-white/30 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <Icon size={20} />
                    {open && <span className="font-medium">{group.label}</span>}
                  </div>
                  {open && (
                    <ChevronDown
                      size={18}
                      className={`transition ${
                        expanded[group.key] ? "rotate-180" : ""
                      }`}
                    />
                  )}
                </button>

                {/* CHILD */}
                {expanded[group.key] &&
                  group.children.map((item) => {
                    const ActiveIcon = item.icon;
                    const active = pathname === item.path;

                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setMobileOpen(false)}
                        className={`ml-6 mt-1 flex items-center gap-3 px-4 py-2 rounded-xl text-sm
                        backdrop-blur-sm border transition-all
                        ${
                          active
                            ? "bg-gradient-to-r from-white to-blue-100 text-[#0f6160] border-white shadow-lg"
                            : "hover:bg-white/20 border-white/10 hover:border-white/30"
                        }`}
                      >
                        <ActiveIcon size={16} />
                        {open && item.label}
                      </Link>
                    );
                  })}
              </div>
            );
          })}

          {/* MENU KE-3 */}
          <Link
            to="/"
            onClick={() => setMobileOpen(false)}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl backdrop-blur-sm border transition-all
              ${
                pathname === "/"
                  ? "bg-gradient-to-r from-white to-blue-100 text-[#0f6160] border-white shadow-lg"
                  : "hover:bg-white/20 border-white/10 hover:border-white/30"
              }`}
          >
            <FileSpreadsheet size={20} />
            {open && "Upload Jadwal"}
          </Link>
        </nav>
      </aside>
    </div>
  );
}
