import type { SalaryComponent } from "./employee";

export type SalaryHistoryRecord = {
  id: string;
  employeeId: number;
  oldValue: SalaryComponent | null;
  newValue: SalaryComponent;
  changedBy: string;
  changedAt: string;
};
