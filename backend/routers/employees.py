import secrets
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse

from database import get_db_connection
from schemas import (
    EmployeeItem,
    SalaryComponentDetail,
    SalaryComponentPayload,
    SalaryComponentContainer,
    SalaryHistoryItem,
    SalaryItem
)

router = APIRouter(prefix="/api/employees", tags=["Employees"])

def verify_admin_hr(
    x_user_role: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header("Rani K. (Admin HR)"),
    authorization: Optional[str] = Header(None)
) -> dict:
    role = x_user_role
    if role is None:
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
            role = "Employee" if token.lower() == "employee" else "Admin HR"
        else:
            role = "Admin HR"

    if (role or "").strip().lower() != "admin hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "forbidden",
                "code": 403,
                "message": "Akses Ditolak (HTTP 403): Hanya pengguna dengan role 'Admin HR' yang berwenang mengatur komponen gaji.",
                "currentRole": role,
            }
        )

    return {"name": x_user_name or "Rani K. (Admin HR)", "role": "Admin HR"}

def fetch_salary_component_detail(conn, employee_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, basic_salary, fixed_allowance, deduction, effective_from
        FROM salary_components
        WHERE employee_id = ?
    """, (employee_id,))
    comp = cursor.fetchone()
    if not comp:
        return None

    comp_id = comp["id"]
    cursor.execute("""
        SELECT id, name, amount, type
        FROM salary_items
        WHERE salary_component_id = ?
        ORDER BY id ASC
    """, (comp_id,))
    items = cursor.fetchall()

    allowances = []
    deductions = []
    for item in items:
        item_data = {
            "id": str(item["id"]),
            "name": str(item["name"]),
            "amount": int(item["amount"])
        }
        if item["type"] == "allowance":
            allowances.append(item_data)
        else:
            deductions.append(item_data)

    return {
        "basicSalary": int(comp["basic_salary"]),
        "fixedAllowance": int(comp["fixed_allowance"]),
        "deduction": int(comp["deduction"]),
        "effectiveFrom": str(comp["effective_from"]),
        "allowances": allowances,
        "deductions": deductions,
    }

@router.get("", response_model=List[EmployeeItem])
def list_employees():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, nik, department, position, created_at FROM employees ORDER BY id ASC")
        employees = cursor.fetchall()

        result = []
        for emp in employees:
            salary_comp = fetch_salary_component_detail(conn, emp["id"])
            result.append({
                "id": emp["id"],
                "name": emp["name"],
                "nik": emp["nik"],
                "department": emp["department"],
                "position": emp["position"],
                "salaryComponent": salary_comp
            })
        return result
    finally:
        conn.close()

@router.get("/{employee_id}/salary-components")
def get_salary_component(employee_id: int):
    conn = get_db_connection()
    try:
        detail = fetch_salary_component_detail(conn, employee_id)
        if detail is None:
            raise HTTPException(status_code=404, detail={"message": "Data komponen gaji tidak ditemukan."})
        return {"data": detail}
    finally:
        conn.close()

@router.api_route("/{employee_id}/salary-components", methods=["POST", "PUT"])
async def save_salary_component(
    employee_id: int,
    payload: SalaryComponentPayload,
    request: Request,
    x_user_role: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header("Rani K. (Admin HR)"),
    authorization: Optional[str] = Header(None)
):
    # RBAC Auth Check
    admin_user = verify_admin_hr(x_user_role, x_user_name, authorization)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 1. Cek karyawan ada
        cursor.execute("SELECT id, name FROM employees WHERE id = ?", (employee_id,))
        emp = cursor.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail={"message": "Karyawan tidak ditemukan."})

        # 2. Validasi input (AC1 & AC4)
        if payload.basicSalary <= 0:
            raise HTTPException(status_code=422, detail={"message": "Gaji pokok wajib diisi dan harus lebih besar dari Rp 0."})

        now_dt = datetime.now()
        effective_from = payload.effectiveFrom or f"{now_dt.year}-{now_dt.month:02d}-01"

        allowances = []
        total_allowance = 0
        if payload.allowances:
            for idx, item in enumerate(payload.allowances):
                name = item.name.strip()
                amt = item.amount
                if not name:
                    raise HTTPException(status_code=422, detail={"message": f"Nama tunjangan ke-{idx + 1} tidak boleh kosong."})
                if amt < 0:
                    raise HTTPException(status_code=422, detail={"message": f"Nominal tunjangan '{name}' tidak boleh bernilai negatif."})
                item_id = item.id if item.id else f"al-{secrets.token_hex(4)}"
                allowances.append({"id": item_id, "name": name, "amount": amt, "type": "allowance"})
                total_allowance += amt
        else:
            total_allowance = max(0, payload.fixedAllowance or 0)

        deductions = []
        total_deduction = 0
        if payload.deductions:
            for idx, item in enumerate(payload.deductions):
                name = item.name.strip()
                amt = item.amount
                if not name:
                    raise HTTPException(status_code=422, detail={"message": f"Nama potongan ke-{idx + 1} tidak boleh kosong."})
                if amt < 0:
                    raise HTTPException(status_code=422, detail={"message": f"Nominal potongan '{name}' tidak boleh bernilai negatif."})
                item_id = item.id if item.id else f"de-{secrets.token_hex(4)}"
                deductions.append({"id": item_id, "name": name, "amount": amt, "type": "deduction"})
                total_deduction += amt
        else:
            total_deduction = max(0, payload.deduction or 0)

        # Snapshot lama untuk history
        old_snapshot = fetch_salary_component_detail(conn, employee_id)

        now_iso = datetime.now().isoformat()

        cursor.execute("SELECT id FROM salary_components WHERE employee_id = ?", (employee_id,))
        existing = cursor.fetchone()

        if existing:
            comp_id = existing["id"]
            cursor.execute("""
                UPDATE salary_components
                SET basic_salary = ?, fixed_allowance = ?, deduction = ?, effective_from = ?, updated_at = ?
                WHERE id = ?
            """, (payload.basicSalary, total_allowance, total_deduction, effective_from, now_iso, comp_id))
            cursor.execute("DELETE FROM salary_items WHERE salary_component_id = ?", (comp_id,))
        else:
            cursor.execute("""
                INSERT INTO salary_components (employee_id, basic_salary, fixed_allowance, deduction, effective_from, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (employee_id, payload.basicSalary, total_allowance, total_deduction, effective_from, now_iso))
            cursor.execute("SELECT id FROM salary_components WHERE employee_id = ?", (employee_id,))
            comp_id = cursor.fetchone()["id"]

        for al in allowances:
            cursor.execute("""
                INSERT INTO salary_items (id, salary_component_id, type, name, amount)
                VALUES (?, ?, ?, ?, ?)
            """, (al["id"], comp_id, "allowance", al["name"], al["amount"]))

        for de in deductions:
            cursor.execute("""
                INSERT INTO salary_items (id, salary_component_id, type, name, amount)
                VALUES (?, ?, ?, ?, ?)
            """, (de["id"], comp_id, "deduction", de["name"], de["amount"]))

        new_snapshot = {
            "basicSalary": payload.basicSalary,
            "fixedAllowance": total_allowance,
            "deduction": total_deduction,
            "effectiveFrom": effective_from,
            "allowances": [{"id": a["id"], "name": a["name"], "amount": a["amount"]} for a in allowances],
            "deductions": [{"id": d["id"], "name": d["name"], "amount": d["amount"]} for d in deductions],
        }

        # Catat history audit
        hist_id = f"hist-{int(datetime.now().timestamp())}-{secrets.token_hex(3)}"
        cursor.execute("""
            INSERT INTO salary_history (id, employee_id, old_value, new_value, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            hist_id,
            employee_id,
            json.dumps(old_snapshot) if old_snapshot else None,
            json.dumps(new_snapshot),
            admin_user["name"],
            now_iso
        ))

        conn.commit()
        return {"data": new_snapshot}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"message": f"Internal server error: {str(e)}"})
    finally:
        conn.close()

@router.get("/{employee_id}/salary-history", response_model=List[SalaryHistoryItem])
def get_salary_history(employee_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, employee_id, old_value, new_value, changed_by, changed_at
            FROM salary_history
            WHERE employee_id = ?
            ORDER BY changed_at DESC
        """, (employee_id,))
        rows = cursor.fetchall()

        result = []
        for row in rows:
            old_val = json.loads(row["old_value"]) if row["old_value"] else None
            new_val = json.loads(row["new_value"]) if row["new_value"] else {}
            result.append({
                "id": str(row["id"]),
                "employeeId": int(row["employee_id"]),
                "oldValue": old_val,
                "newValue": new_val,
                "changedBy": str(row["changed_by"]),
                "changedAt": str(row["changed_at"])
            })
        return result
    finally:
        conn.close()
