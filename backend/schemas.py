from typing import List, Optional, Any
from pydantic import BaseModel, Field

class SalaryItem(BaseModel):
    id: Optional[str] = None
    name: str
    amount: int = Field(ge=0, description="Nominal tunjangan atau potongan")

class SalaryComponentDetail(BaseModel):
    basicSalary: int
    fixedAllowance: int
    deduction: int
    effectiveFrom: str
    allowances: List[SalaryItem] = []
    deductions: List[SalaryItem] = []

class SalaryComponentPayload(BaseModel):
    basicSalary: int
    fixedAllowance: Optional[int] = 0
    deduction: Optional[int] = 0
    effectiveFrom: Optional[str] = None
    allowances: Optional[List[SalaryItem]] = []
    deductions: Optional[List[SalaryItem]] = []

class EmployeeItem(BaseModel):
    id: int
    name: str
    nik: str
    department: str
    position: str
    salaryComponent: Optional[SalaryComponentDetail] = None

class SalaryComponentContainer(BaseModel):
    data: SalaryComponentDetail

class SalaryHistoryItem(BaseModel):
    id: str
    employeeId: int
    oldValue: Optional[Any] = None
    newValue: Any
    changedBy: str
    changedAt: str
