import { mockEmployees } from "../data/mockEmployees";
import type { Employee } from "../types/employee";

// Adapter sementara agar komponen UI tidak bergantung langsung pada data mock.
// Saat backend siap, fungsi ini bisa diganti dengan fetch() ke endpoint T7.
export async function getEmployees(): Promise<Employee[]> {
  return Promise.resolve(mockEmployees);
}
