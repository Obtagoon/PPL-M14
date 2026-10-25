# Struktur Database PPL-M14 (SQLite)

Dokumentasi rancangan basis data untuk aplikasi **Pengelolaan Komponen Gaji Karyawan (Employee Payroll Management)** pada proyek PPL-M14. Database disimpan pada file: `backend/database/database.sqlite`.

---

## Ringkasan Tabel

Terdapat 5 tabel utama:
1. **`employees`**: Data master profil karyawan.
2. **`salary_components`**: Dasar perhitungan komponen gaji utama per karyawan (AC1).
3. **`salary_items`**: Rincian item tunjangan tetap dan potongan terpisah dengan nama dan nominal (AC4).
4. **`salary_history`**: Audit trail / riwayat log perubahan komponen gaji.
5. **`users`**: Data akun pengguna beserta role otorisasi (RBAC).

---

## 1. Tabel `employees` (Data Karyawan)
Menyimpan identitas master setiap karyawan perusahaan.

| Kolom | Tipe Data | Constraint | Keterangan |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | ID unik karyawan |
| `name` | `TEXT` | `NOT NULL` | Nama lengkap karyawan (misal: "Andi Pratama") |
| `nik` | `TEXT` | `NOT NULL UNIQUE` | Nomor Induk Karyawan unik (misal: "2026001") |
| `department` | `TEXT` | `NOT NULL` | Departemen (misal: "Operasional", "Keuangan", "IT") |
| `position` | `TEXT` | `NOT NULL` | Jabatan/Posisi (misal: "Staf IT", "Supervisor") |
| `created_at` | `TEXT` | `NOT NULL` | Waktu data dibuat (format ISO 8601) |

---

## 2. Tabel `salary_components` (Komponen Gaji Utama - AC1)
Menyimpan dasar perhitungan gaji per karyawan. Sesuai Acceptance Criteria 1 (AC1):
- Gaji Bersih = Gaji Pokok + Total Tunjangan - Total Potongan

| Kolom | Tipe Data | Constraint | Keterangan |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | ID unik komponen gaji |
| `employee_id` | `INTEGER` | `NOT NULL UNIQUE, FK -> employees(id) ON DELETE CASCADE` | Relasi ke karyawan (1 karyawan memiliki 1 komponen aktif) |
| `basic_salary` | `INTEGER` | `NOT NULL` | **Gaji Pokok** dalam Rupiah (AC1) |
| `fixed_allowance` | `INTEGER` | `NOT NULL DEFAULT 0` | **Total Tunjangan Tetap** (penjumlahan dari semua tunjangan) |
| `deduction` | `INTEGER` | `NOT NULL DEFAULT 0` | **Total Potongan Gaji** (penjumlahan dari semua potongan) |
| `effective_from` | `TEXT` | `NOT NULL` | Tanggal mulai berlakunya gaji (format: YYYY-MM-DD) |
| `updated_at` | `TEXT` | `NOT NULL` | Waktu pembaruan terakhir |

---

## 3. Tabel `salary_items` (Rincian Tunjangan & Potongan - AC4)
Menyimpan rincian item tunjangan tetap dan potongan secara terpisah. Sesuai Acceptance Criteria 4 (AC4):
- Setiap komponen tersimpan terpisah lengkap dengan **nama komponen** dan **nominalnya**.
- Dapat ditambah atau dihapus secara dinamis.

| Kolom | Tipe Data | Constraint | Keterangan |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | ID item unik (misal: `"al-1-1"`, `"de-1-1"`) |
| `salary_component_id` | `INTEGER` | `NOT NULL, FK -> salary_components(id) ON DELETE CASCADE` | Relasi ke komponen gaji karyawan terkait |
| `type` | `TEXT` | `NOT NULL` | Jenis komponen: `"allowance"` (tunjangan) atau `"deduction"` (potongan) |
| `name` | `TEXT` | `NOT NULL` | **Nama komponen** (misal: "Tunjangan Transport", "BPJS Kesehatan") |
| `amount` | `INTEGER` | `NOT NULL` | **Nominal uang** dalam Rupiah (misal: `500000`, `100000`) |

---

## 4. Tabel `salary_history` (Audit Log Riwayat Perubahan)
Mencatat jejak riwayat setiap kali terjadi penambahan atau pengubahan komponen gaji karyawan oleh Admin HR.

| Kolom | Tipe Data | Constraint | Keterangan |
|---|---|---|---|
| `id` | `TEXT` | `PRIMARY KEY` | ID riwayat unik (misal: `"hist-1"`) |
| `employee_id` | `INTEGER` | `NOT NULL, FK -> employees(id) ON DELETE CASCADE` | Relasi ke karyawan terkait |
| `old_value` | `TEXT` | `NULLABLE` | Snapshot nilai lama dalam format JSON |
| `new_value` | `TEXT` | `NOT NULL` | Snapshot nilai baru dalam format JSON |
| `changed_by` | `TEXT` | `NOT NULL` | Nama dan role pelaku perubahan (misal: "Rani K. (Admin HR)") |
| `changed_at` | `TEXT` | `NOT NULL` | Waktu perubahan dilakukan |

---

## 5. Tabel `users` (Pengguna & Role RBAC)
Menyimpan akun pengguna sistem untuk verifikasi izin otorisasi Role-Based Access Control (RBAC).

| Kolom | Tipe Data | Constraint | Keterangan |
|---|---|---|---|
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | ID unik akun pengguna |
| `name` | `TEXT` | `NOT NULL` | Nama pengguna (misal: "Rani K.", "Andi Pratama") |
| `email` | `TEXT` | `NOT NULL UNIQUE` | Alamat email unik |
| `role` | `TEXT` | `NOT NULL DEFAULT 'Employee'` | Role akses: `'Admin HR'` (Izin penuh) atau `'Employee'` (Hanya lihat) |
| `created_at` | `TEXT` | `NOT NULL` | Waktu pembuatan akun |

---

## Diagram Relasi Antar Tabel (Entity Relationship)

```text
+------------------+          1:1          +--------------------+
|    employees     | <-------------------> | salary_components  |
+------------------+                       +--------------------+
| id (PK)          |                                 |
| name             |                                 | 1:N
| nik              |                                 v
| department       |                       +--------------------+
| position         |                       |    salary_items    |
| created_at       |                       +--------------------+
+------------------+                       | id (PK)            |
        |                                  | salary_comp_id(FK) |
        | 1:N                              | type               |
        v                                  | name               |
+------------------+                       | amount             |
|  salary_history  |                       +--------------------+
+------------------+
| id (PK)          |
| employee_id (FK) |
| old_value        |
| new_value        |
| changed_by       |
| changed_at       |
+------------------+
```
