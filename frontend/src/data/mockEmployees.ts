import type { Employee } from "../types/employee";

// Data sementara untuk pengembangan frontend sebelum API backend tersedia.
// Ganti sumber data ini saat kontrak API T7 sudah disepakati.
export const mockEmployees: Employee[] = [
  {
    id: 1,
    name: "Andi Pratama",
    nik: "2026001",
    department: "Operasional",
    position: "Staf Operasional",
    salaryComponent: {
      basicSalary: 5_000_000,
      fixedAllowance: 750_000,
      deduction: 100_000,
      allowances: [
        { id: "al-1-1", name: "Tunjangan Transport", amount: 500_000 },
        { id: "al-1-2", name: "Tunjangan Makan", amount: 250_000 },
      ],
      deductions: [
        { id: "de-1-1", name: "BPJS Ketenagakerjaan", amount: 100_000 },
      ],
    },
  },
  {
    id: 2,
    name: "Siti Rahma",
    nik: "2026002",
    department: "Keuangan",
    position: "Staf Keuangan",
  },
  {
    id: 3,
    name: "Budi Santoso",
    nik: "2026003",
    department: "Sumber Daya Manusia",
    position: "Staf HR",
    salaryComponent: {
      basicSalary: 4_800_000,
      fixedAllowance: 500_000,
      deduction: 0,
      allowances: [
        { id: "al-3-1", name: "Tunjangan Kehadiran", amount: 500_000 },
      ],
      deductions: [],
    },
  },
  {
    id: 4,
    name: "Dewi Lestari",
    nik: "2026004",
    department: "Operasional",
    position: "Supervisor",
  },
  {
    id: 5,
    name: "Rizky Firmansyah",
    nik: "2026005",
    department: "Teknologi Informasi",
    position: "Staf IT",
  },
];
