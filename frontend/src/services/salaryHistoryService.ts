import type { SalaryHistoryRecord } from "../types/salaryHistory";
import { USE_MOCK_DATA } from "./salaryComponentService";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

// Data riwayat simulasi untuk fallback saat mock mode
export function getMockSalaryHistory(): SalaryHistoryRecord[] {
  return [
    {
      id: "history-1",
      employeeId: 1,
      oldValue: {
        basicSalary: 4_500_000,
        fixedAllowance: 500_000,
        deduction: 100_000,
        allowances: [{ id: "h1-1", name: "Tunjangan Transport", amount: 500_000 }],
        deductions: [{ id: "h1-2", name: "BPJS Ketenagakerjaan", amount: 100_000 }],
      },
      newValue: {
        basicSalary: 5_000_000,
        fixedAllowance: 750_000,
        deduction: 100_000,
        allowances: [
          { id: "h1-3", name: "Tunjangan Transport", amount: 500_000 },
          { id: "h1-4", name: "Tunjangan Makan", amount: 250_000 },
        ],
        deductions: [{ id: "h1-5", name: "BPJS Ketenagakerjaan", amount: 100_000 }],
      },
      changedBy: "Rani K. (Admin HR)",
      changedAt: "2026-10-20T09:15:00+07:00",
    },
    {
      id: "history-2",
      employeeId: 3,
      oldValue: {
        basicSalary: 4_500_000,
        fixedAllowance: 400_000,
        deduction: 0,
        allowances: [{ id: "h2-1", name: "Tunjangan Kehadiran", amount: 400_000 }],
        deductions: [],
      },
      newValue: {
        basicSalary: 4_800_000,
        fixedAllowance: 500_000,
        deduction: 0,
        allowances: [{ id: "h2-2", name: "Tunjangan Kehadiran", amount: 500_000 }],
        deductions: [],
      },
      changedBy: "Rani K. (Admin HR)",
      changedAt: "2026-10-21T14:30:00+07:00",
    },
  ];
}

// Mengambil riwayat perubahan komponen gaji dari Backend PHP 8.4
export async function getSalaryHistory(employeeId: number): Promise<SalaryHistoryRecord[]> {
  if (USE_MOCK_DATA) {
    return Promise.resolve(getMockSalaryHistory().filter((r) => r.employeeId === employeeId));
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/employees/${employeeId}/salary-history`, {
      headers: {
        Accept: "application/json",
        "X-User-Role": "Admin HR",
      },
    });

    if (!response.ok) {
      return [];
    }

    const data = await response.json();
    return Array.isArray(data) ? (data as SalaryHistoryRecord[]) : [];
  } catch (error) {
    console.error("Gagal mengambil riwayat komponen gaji:", error);
    return [];
  }
}
