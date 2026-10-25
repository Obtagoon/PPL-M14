import { mockEmployees } from "../data/mockEmployees";
import type { Employee, SalaryComponent } from "../types/employee";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA !== "false";

type SaveSalaryPayload = SalaryComponent & { effectiveFrom: string };

let currentRole = "Admin HR";
let currentUserName = "Rani K. (Admin HR)";

export function getActiveRole(): string {
  return currentRole;
}

export function setActiveRole(role: string): void {
  currentRole = role;
  if (role === "Admin HR") {
    currentUserName = "Rani K. (Admin HR)";
  } else {
    currentUserName = "Andi Pratama (Pegawai)";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "X-User-Role": currentRole,
      "X-User-Name": currentUserName,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const errorJson = await response.json().catch(() => null);
    const message = errorJson?.message || (await response.text().catch(() => ""));
    if (response.status === 403) {
      throw new Error(message || "Akses Ditolak (HTTP 403): Hanya Admin HR yang berwenang mengatur komponen gaji.");
    }
    if (response.status === 404) throw new Error("Data komponen gaji tidak ditemukan.");
    throw new Error(message || `Permintaan API gagal (HTTP ${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function unwrapSalaryResponse(value: unknown): SalaryComponent | null {
  if (!value || typeof value !== "object") return null;
  const root = value as Record<string, unknown>;
  const candidate = (root.data && typeof root.data === "object" ? root.data : root) as Record<string, unknown>;
  const salary = (candidate.salaryComponent && typeof candidate.salaryComponent === "object"
    ? candidate.salaryComponent : candidate) as Record<string, unknown>;
  if (typeof salary.basicSalary !== "number" ||
      typeof salary.fixedAllowance !== "number" ||
      typeof salary.deduction !== "number") {
    throw new Error("Format respons API komponen gaji belum sesuai kontrak frontend.");
  }
  const allowances = Array.isArray(salary.allowances)
    ? salary.allowances.map((item: any) => ({
        id: String(item.id ?? Math.random().toString(36).slice(2, 9)),
        name: String(item.name ?? ""),
        amount: Number(item.amount ?? 0),
      }))
    : undefined;

  const deductions = Array.isArray(salary.deductions)
    ? salary.deductions.map((item: any) => ({
        id: String(item.id ?? Math.random().toString(36).slice(2, 9)),
        name: String(item.name ?? ""),
        amount: Number(item.amount ?? 0),
      }))
    : undefined;

  return {
    basicSalary: salary.basicSalary,
    fixedAllowance: salary.fixedAllowance,
    deduction: salary.deduction,
    allowances,
    deductions,
  };
}

const STORAGE_KEY_MOCK_EMPLOYEES = "ppl_m14_mock_employees";

function getStoredMockEmployees(): Employee[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_MOCK_EMPLOYEES);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (e) {
    console.error("Gagal membaca mock employees dari localStorage", e);
  }
  return mockEmployees;
}

function saveStoredMockEmployees(list: Employee[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_MOCK_EMPLOYEES, JSON.stringify(list));
  } catch (e) {
    console.error("Gagal menyimpan mock employees ke localStorage", e);
  }
}

export async function getEmployeesForSalary(): Promise<Employee[]> {
  if (USE_MOCK_DATA) return getStoredMockEmployees();
  const response = await request<unknown>("/api/employees");
  const list = Array.isArray(response) ? response : (response as { data?: unknown })?.data;
  if (!Array.isArray(list)) throw new Error("Format respons daftar karyawan belum sesuai kontrak frontend.");
  return list as Employee[];
}

export async function getSalaryComponent(employeeId: number): Promise<SalaryComponent | null> {
  if (USE_MOCK_DATA) {
    return getStoredMockEmployees().find((employee) => employee.id === employeeId)?.salaryComponent ?? null;
  }
  try {
    return unwrapSalaryResponse(await request<unknown>(`/api/employees/${employeeId}/salary-components`));
  } catch (error) {
    if (error instanceof Error && error.message.includes("tidak ditemukan")) return null;
    throw error;
  }
}

export async function saveSalaryComponent(
  employeeId: number,
  payload: SaveSalaryPayload,
  isUpdate: boolean,
): Promise<SalaryComponent> {
  if (currentRole !== "Admin HR") {
    throw new Error("Akses Ditolak (HTTP 403): Hanya pengguna dengan role 'Admin HR' yang berwenang mengatur komponen gaji.");
  }
  if (USE_MOCK_DATA) {
    const { effectiveFrom: _effectiveFrom, ...salary } = payload;
    const currentList = getStoredMockEmployees();
    const updatedList = currentList.map((emp) =>
      emp.id === employeeId ? { ...emp, salaryComponent: salary } : emp
    );
    saveStoredMockEmployees(updatedList);
    return salary;
  }
  const response = await request<unknown>(`/api/employees/${employeeId}/salary-components`, {
    method: isUpdate ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  const saved = unwrapSalaryResponse(response);
  if (!saved) throw new Error("Respons API tidak berisi komponen gaji yang valid.");
  return saved;
}

