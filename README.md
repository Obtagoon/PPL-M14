<<<<<<< HEAD
# M14-US1 Frontend — T11 + T12

React + TypeScript + Vite frontend prototipe untuk pengaturan komponen gaji per karyawan.

## Menjalankan
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
```

## T12 yang tersedia
- Form tambah komponen gaji untuk karyawan yang belum memiliki komponen.
- Form edit untuk karyawan yang sudah memiliki komponen.
- Validasi: gaji pokok wajib dan > 0; tunjangan/potongan tidak negatif; input kosong pada tunjangan/potongan dianggap 0.
- Simpan memperbarui state frontend untuk sesi prototipe saja.
- Data belum tersimpan permanen dan belum terhubung ke API/backend.


## T13 — Validasi form client & pesan error per field

- Gaji pokok wajib diisi, harus berupa angka valid, lebih besar dari nol, dan bilangan bulat rupiah.
- Tunjangan tetap dan potongan boleh kosong (dianggap nol), tetapi jika diisi harus berupa angka valid, tidak negatif, dan bilangan bulat rupiah.
- Pesan validasi ditampilkan pada field terkait; form tidak disimpan jika ada error.
- Input menggunakan tipe teks dengan input mode numerik agar validasi dapat menampilkan pesan saat pengguna menempelkan input non-numerik.
- Data masih berupa state frontend/mock dan belum divalidasi oleh backend.


## T13 — Pengujian penerimaan validasi

Lakukan pengujian manual berikut sebelum menandai T13 selesai:

1. Buka form komponen gaji dan kosongkan gaji pokok; setelah blur atau submit, pesan wajib diisi harus muncul di bawah field.
2. Isi gaji pokok dengan `0` atau angka negatif; pesan harus menjelaskan bahwa nilainya harus lebih besar dari nol.
3. Isi tunjangan tetap dengan angka negatif; pesan error harus muncul pada field tunjangan.
4. Isi potongan dengan angka negatif; pesan error harus muncul pada field potongan.
5. Tempelkan teks nonangka pada setiap field; validasi harus menolak nilai yang bukan angka.
6. Pastikan submit tidak memperbarui data selama masih ada error.
7. Koreksi nilai yang salah dan pastikan pesan pada field tersebut hilang setelah nilainya valid.
8. Masukkan nominal valid, simpan, dan pastikan detail karyawan menampilkan nilai yang baru.

Batasan: data simpanan masih berada di state frontend/mock dan tidak bertahan setelah refresh. Validasi backend belum termasuk T13 frontend.


## T14 — Tampilan riwayat perubahan komponen gaji

- Tambahkan tombol untuk menampilkan/menyembunyikan riwayat dari detail karyawan.
- Riwayat menampilkan nilai lama, nilai baru, admin pengubah, dan tanggal/waktu.
- Jika belum ada catatan, tampilkan empty state yang informatif.
- Setelah form komponen gaji disimpan pada prototipe, satu catatan riwayat ditambahkan ke state frontend.
- Riwayat awal dan perubahan lokal adalah data simulasi; belum persisten dan belum mengambil data dari backend.
- Dependensi backlog: T9 (pencatatan riwayat otomatis). Setelah endpoint T9 siap, `src/services/salaryHistoryService.ts` perlu diganti agar mengambil riwayat dari API.


## T15 — Integrasi form dengan API (create, update, read)

### Implementasi frontend
- `src/services/salaryComponentService.ts` memisahkan akses API dari UI.
- Read daftar karyawan: `GET /api/employees`.
- Read komponen per karyawan: `GET /api/employees/:id/salary-components`.
- Create komponen: `POST /api/employees/:id/salary-components`.
- Update komponen: `PUT /api/employees/:id/salary-components`.
- Payload simpan berisi `basicSalary`, `fixedAllowance`, `deduction`, dan `effectiveFrom`.
- UI menangani status menyimpan dan menampilkan error API.
- Mode mock tetap aktif secara default selama backend belum siap.

### Mengaktifkan API
Buat `.env` berdasarkan `.env.example`:
- `VITE_USE_MOCK_DATA=false`
- `VITE_API_BASE_URL=http://localhost:PORT` (ganti PORT sesuai backend).
Restart Vite setelah mengubah `.env`.

### Kontrak REST sementara (wajib disepakati dengan backend)
1. `GET /api/employees` mengembalikan array karyawan atau `{ "data": [...] }`.
2. `GET /api/employees/:id/salary-components` mengembalikan komponen gaji atau `{ "data": { "salaryComponent": {...} } }`; HTTP 404 berarti belum diatur.
3. `POST` dan `PUT` pada endpoint yang sama menerima `{ basicSalary, fixedAllowance, deduction, effectiveFrom }` dan mengembalikan komponen gaji.
4. `effectiveFrom` diasumsikan tanggal pertama bulan kalender berikutnya. Konfirmasi aturan periode penggajian dengan backend.
5. Sesuaikan service bila backend memakai route, format respons, atau tipe ID berbeda.

### Batasan
- Belum bisa diuji end-to-end sebelum endpoint T5/T6/T7 tersedia dan kontraknya disepakati.
- Riwayat masih simulasi; API T9 belum dihubungkan.
- Hak akses Admin HR harus ditegakkan melalui autentikasi dan backend.


## Perbaikan JSX lanjutan
Blok `<tbody>` di `src/App.tsx` ditulis ulang dengan conditional rendering yang eksplisit untuk kondisi loading, error, hasil pencarian kosong, dan daftar karyawan. Jika VS Code masih menampilkan isi lama, simpan/backup perubahan lokal lalu tutup dan buka kembali `src/App.tsx` setelah ekstraksi.
=======
# M14 - PPL

Employee Payroll Management.

## Development

Coming soon.
>>>>>>> origin/main
