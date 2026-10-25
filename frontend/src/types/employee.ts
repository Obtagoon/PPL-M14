export type SalaryItem = {
  id: string;
  name: string;
  amount: number;
};

export type SalaryComponent = {
  basicSalary: number;
  fixedAllowance: number;
  deduction: number;
  allowances?: SalaryItem[];
  deductions?: SalaryItem[];
};

export type Employee = {
  id: number;
  name: string;
  nik: string;
  department: string;
  position: string;
  salaryComponent?: SalaryComponent;
};
