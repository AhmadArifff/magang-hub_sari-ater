// utils/fileStorage.js

export async function saveExcel(file) {
  const root = await navigator.storage.getDirectory();
  const folder = await root.getDirectoryHandle("jadwal-info", { create: true });

  const fileHandle = await folder.getFileHandle("informasi-jadwal.xlsx", { create: true });

  const writable = await fileHandle.createWritable();
  await writable.write(await file.arrayBuffer());
  await writable.close();

  localStorage.setItem("jadwal_uploaded_at", Date.now());
}

export async function loadExcel() {
  try {
    const root = await navigator.storage.getDirectory();
    const folder = await root.getDirectoryHandle("jadwal-info");
    const fileHandle = await folder.getFileHandle("informasi-jadwal.xlsx");

    return await fileHandle.getFile();
  } catch {
    return null;
  }
}

export async function autoDeleteOld() {
  const t = localStorage.getItem("jadwal_uploaded_at");
  if (!t) return;

  const days = (Date.now() - Number(t)) / (1000 * 60 * 60 * 24);

  if (days > 30) {
    const root = await navigator.storage.getDirectory();
    const folder = await root.getDirectoryHandle("jadwal-info");

    try {
      await folder.removeEntry("informasi-jadwal.xlsx");
    } catch {}

    localStorage.removeItem("jadwal_uploaded_at");
  }
}
