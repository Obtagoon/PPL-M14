# PPL-M14 Backend (PHP 8.4)

Backend REST API untuk pengelolaan komponen gaji per karyawan sesuai spesifikasi:
- **AC1**: Dasar perhitungan gaji (Gaji Pokok, Tunjangan, Potongan, Take-Home Pay).
- **AC4**: Penambahan beberapa tunjangan tetap atau potongan (mis. transport, makan, BPJS) yang tersimpan terpisah dengan nama dan nominalnya.

## Persyaratan
- PHP >= 8.4 (ekstensi `pdo_sqlite` aktif)

## Menjalankan Server
Jalankan development server PHP bawaan pada port 8000:

```bash
# Dari root repositori
npm run backend

# Atau dari dalam folder backend
php -S localhost:8000 -t public
```

Server API akan aktif di `http://localhost:8000`.

## Endpoints API

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/` atau `/api/health` | Health check & verifikasi PHP 8.4 |
| `GET` | `/api/employees` | Mengambil seluruh daftar karyawan beserta komponen gaji |
| `GET` | `/api/employees/{id}/salary-components` | Mengambil komponen gaji karyawan tertentu beserta rincian tunjangan dan potongan |
| `POST` / `PUT` | `/api/employees/{id}/salary-components` | Menyimpan / memperbarui komponen gaji (Gaji Pokok, Tunjangan, Potongan) |
| `GET` | `/api/employees/{id}/salary-history` | Mengambil riwayat log perubahan komponen gaji karyawan |

## Format Payload Simpan Komponen Gaji (`POST`/`PUT`)
```json
{
  "basicSalary": 5000000,
  "fixedAllowance": 750000,
  "deduction": 100000,
  "effectiveFrom": "2026-11-01",
  "allowances": [
    { "id": "al-1", "name": "Tunjangan Transport", "amount": 500000 },
    { "id": "al-2", "name": "Tunjangan Makan", "amount": 250000 }
  ],
  "deductions": [
    { "id": "de-1", "name": "BPJS Ketenagakerjaan", "amount": 100000 }
  ]
}
```
