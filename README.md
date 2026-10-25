# M14-US1 Pengaturan Komponen Gaji per Karyawan

Aplikasi pengelolaan komponen gaji per karyawan (Employee Payroll Management) yang dikembangkan dengan:
- **Frontend**: React 19 + TypeScript + Vite (`/frontend`)
- **Backend**: PHP 8.4 REST API + SQLite PDO (`/backend`)

---

## Struktur Folder Proyek

```text
PPL-M14/
├── frontend/             # Aplikasi web React + TypeScript + Vite
│   ├── src/
│   │   ├── types/        # Type definitions (Employee, SalaryComponent, SalaryItem)
│   │   ├── services/     # API services & HTTP handlers
│   │   ├── data/         # Mock data
│   │   ├── App.tsx       # Komponen utama UI
│   │   ├── styles.css    # Desain sistem & styling
│   │   └── main.tsx      # Entrypoint React
│   ├── .env              # Konfigurasi environment frontend
│   └── package.json      # Dependensi frontend
│
├── backend/              # REST API PHP 8.4
│   ├── public/
│   │   └── index.php     # Front controller, Router, CORS
│   ├── src/
│   │   ├── Controllers/  # EmployeeController & SalaryComponentController
│   │   ├── Models/       # SalaryComponent & SalaryItem (PHP 8.4)
│   │   └── Database.php  # SQLite PDO Database auto-init & seed
│   ├── database/         # Penyimpanan database SQLite
│   └── composer.json     # Konfigurasi Composer PHP 8.4
│
├── package.json          # Root scripts runner untuk dev & build
└── README.md
```

---

## Fitur & Acceptance Criteria Terpenuhi

### 1. AC1 — Dasar Perhitungan Gaji
- Admin mengisi **Gaji Pokok**, **Tunjangan Tetap**, dan **Potongan**.
- Komponen tersimpan dan secara otomatis dihitung menjadi **Estimasi Gaji Bersih (Take-Home Pay)**:
  $$\text{Gaji Bersih} = \text{Gaji Pokok} + \text{Total Tunjangan} - \text{Total Potongan}$$
- Kalkulasi ditampilkan secara real-time pada formulir maupun ringkasan detail karyawan.

### 2. AC4 — Rincian Tunjangan & Potongan Terpisah (Nama & Nominal)
- Admin dapat menambah beberapa tunjangan tetap (mis. **Transport**, **Makan**, **Kehadiran**, **Komunikasi**).
- Admin dapat menambah beberapa potongan (mis. **BPJS Ketenagakerjaan**, **BPJS Kesehatan**, **Koperasi**, **PPh 21**).
- Setiap komponen tersimpan terpisah lengkap dengan **nama komponen** dan **nominalnya**, serta dapat ditambah/dihapus secara dinamis.

---

## Cara Menjalankan

### 1. Menjalankan Backend (PHP 8.4)
Buka terminal dan jalankan:
```bash
# Opsi A: Dari root folder
npm run backend

# Opsi B: Dari folder backend langsung
cd backend
php -S localhost:8000 -t public
```
Backend akan aktif di `http://localhost:8000`.

### 2. Menjalankan Frontend (Vite)
Buka terminal kedua dan jalankan:
```bash
# Opsi A: Dari root folder
npm run dev

# Opsi B: Dari folder frontend langsung
cd frontend
npm run dev
```
Akses frontend di browser pada alamat: **http://localhost:5173**

---

## Mode Mock vs Backend API
Di dalam file `frontend/.env`:
- `VITE_USE_MOCK_DATA=false`: Terhubung langsung ke Backend PHP 8.4 di `http://localhost:8000`.
- `VITE_USE_MOCK_DATA=true`: Berjalan mandiri dengan data simulasi (tanpa memerlukan server backend).
