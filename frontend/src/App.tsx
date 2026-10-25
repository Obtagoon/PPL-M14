import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Banknote, Bell, ChevronDown, CircleHelp, FileText, LayoutDashboard,
  Menu, Search, Settings, Users, X, ArrowUpRight, Info, CheckCircle2,
  Pencil, Plus, Save, ArrowLeft, History, Clock3, UserRound, Trash2,
  Calculator, PlusCircle, Tag, Wallet, Receipt, Lock, Eye
} from "lucide-react";
import type { Employee, SalaryComponent, SalaryItem } from "./types/employee";
import {
  getEmployeesForSalary, getSalaryComponent, saveSalaryComponent,
  USE_MOCK_DATA, getActiveRole, setActiveRole,
} from "./services/salaryComponentService";
import {
  getSalaryHistory, getStoredMockHistory, saveStoredMockHistory
} from "./services/salaryHistoryService";
import type { SalaryHistoryRecord } from "./types/salaryHistory";

type ItemFormValue = {
  id: string;
  name: string;
  amount: string;
};

type SalaryFormValues = {
  basicSalary: string;
  allowances: ItemFormValue[];
  deductions: ItemFormValue[];
};

type ItemError = {
  name?: string;
  amount?: string;
};

type SalaryFormErrors = {
  basicSalary?: string;
  allowances?: Record<number, ItemError>;
  deductions?: Record<number, ItemError>;
};

const emptyForm: SalaryFormValues = {
  basicSalary: "",
  allowances: [],
  deductions: [],
};

const allowancePresets = ["Transport", "Makan", "Kehadiran", "Komunikasi"];
const deductionPresets = ["BPJS Ketenagakerjaan", "BPJS Kesehatan", "Koperasi", "PPh 21"];

function formatRupiah(value: number) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency", currency: "IDR", maximumFractionDigits: 0,
  }).format(value).replace(/\u00a0/g, " ");
}

function initials(name: string) {
  return name.split(" ").slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Jakarta",
  }).format(new Date(value));
}

function formatSalarySnapshot(value: SalaryComponent | null) {
  if (!value) return "Belum diatur";
  const allowancePart = value.allowances && value.allowances.length > 0
    ? `Tunjangan [${value.allowances.map((a) => `${a.name}: ${formatRupiah(a.amount)}`).join(", ")}]`
    : `Tunjangan ${formatRupiah(value.fixedAllowance)}`;
  const deductionPart = value.deductions && value.deductions.length > 0
    ? `Potongan [${value.deductions.map((d) => `${d.name}: ${formatRupiah(d.amount)}`).join(", ")}]`
    : `Potongan ${formatRupiah(value.deduction)}`;
  const net = value.basicSalary + value.fixedAllowance - value.deduction;
  return `Pokok ${formatRupiah(value.basicSalary)} · ${allowancePart} · ${deductionPart} · Total Bersih ${formatRupiah(net)}`;
}

function validateSalary(values: SalaryFormValues): SalaryFormErrors {
  const errors: SalaryFormErrors = {};
  const basicText = values.basicSalary.trim();
  const basic = basicText === "" ? NaN : Number(basicText);

  if (basicText === "") {
    errors.basicSalary = "Gaji pokok wajib diisi.";
  } else if (!Number.isFinite(basic)) {
    errors.basicSalary = "Gaji pokok harus berupa angka yang valid.";
  } else if (basic <= 0) {
    errors.basicSalary = "Gaji pokok harus lebih besar dari Rp 0.";
  } else if (!Number.isInteger(basic)) {
    errors.basicSalary = "Gaji pokok harus berupa angka bulat dalam rupiah.";
  }

  // Validate allowances
  const allowanceErrors: Record<number, ItemError> = {};
  values.allowances.forEach((item, index) => {
    const itemErr: ItemError = {};
    const nameTrim = item.name.trim();
    const amountTrim = item.amount.trim();
    const amt = amountTrim === "" ? 0 : Number(amountTrim);

    if (!nameTrim) {
      itemErr.name = "Nama tunjangan wajib diisi.";
    }
    if (amountTrim !== "" && !Number.isFinite(amt)) {
      itemErr.amount = "Nominal harus angka valid.";
    } else if (amt < 0) {
      itemErr.amount = "Nominal tidak boleh negatif.";
    } else if (!Number.isInteger(amt)) {
      itemErr.amount = "Nominal harus berupa angka bulat.";
    }

    if (Object.keys(itemErr).length > 0) {
      allowanceErrors[index] = itemErr;
    }
  });
  if (Object.keys(allowanceErrors).length > 0) {
    errors.allowances = allowanceErrors;
  }

  // Validate deductions
  const deductionErrors: Record<number, ItemError> = {};
  values.deductions.forEach((item, index) => {
    const itemErr: ItemError = {};
    const nameTrim = item.name.trim();
    const amountTrim = item.amount.trim();
    const amt = amountTrim === "" ? 0 : Number(amountTrim);

    if (!nameTrim) {
      itemErr.name = "Nama potongan wajib diisi.";
    }
    if (amountTrim !== "" && !Number.isFinite(amt)) {
      itemErr.amount = "Nominal harus angka valid.";
    } else if (amt < 0) {
      itemErr.amount = "Nominal tidak boleh negatif.";
    } else if (!Number.isInteger(amt)) {
      itemErr.amount = "Nominal harus berupa angka bulat.";
    }

    if (Object.keys(itemErr).length > 0) {
      deductionErrors[index] = itemErr;
    }
  });
  if (Object.keys(deductionErrors).length > 0) {
    errors.deductions = deductionErrors;
  }

  return errors;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isEditingSalary, setIsEditingSalary] = useState(false);
  const [formValues, setFormValues] = useState<SalaryFormValues>(emptyForm);
  const [formErrors, setFormErrors] = useState<SalaryFormErrors>({});
  const [saveMessage, setSaveMessage] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [isSavingSalary, setIsSavingSalary] = useState(false);
  const [historyRecords, setHistoryRecords] = useState<SalaryHistoryRecord[]>(() => getStoredMockHistory());
  const [currentRole, setCurrentRole] = useState<string>(() => getActiveRole());
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const isAdmin = currentRole === "Admin HR";

  // Enforce read-only mode for non-admin roles
  useEffect(() => {
    if (!isAdmin && isEditingSalary) {
      setIsEditingSalary(false);
      setSaveMessage("Mode Pegawai: Hak akses terbatas hanya untuk melihat (Read-only).");
    }
  }, [isAdmin, isEditingSalary]);

  useEffect(() => {
    let active = true;
    getEmployeesForSalary()
      .then((data) => { if (active) { setEmployees(data); setLoadError(false); } })
      .catch(() => { if (active) setLoadError(true); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, []);

  const filteredEmployees = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter((employee) =>
      employee.name.toLowerCase().includes(q) || employee.nik.toLowerCase().includes(q)
    );
  }, [employees, query]);

  const selectedEmployee = employees.find((employee) => employee.id === selectedId) ?? null;

  async function selectEmployee(id: number) {
    if (id === -1) {
      setSelectedId(null);
      setIsEditingSalary(false);
      setFormErrors({});
      setSaveMessage("");
      setShowHistory(false);
      return;
    }
    setSelectedId(id);
    setIsEditingSalary(false);
    setFormErrors({});
    setSaveMessage("");
    setShowHistory(false);
    if (!USE_MOCK_DATA) {
      try {
        const [salaryComponent, historyData] = await Promise.all([
          getSalaryComponent(id),
          getSalaryHistory(id),
        ]);
        setEmployees((current) => current.map((employee) =>
          employee.id === id ? { ...employee, salaryComponent: salaryComponent ?? undefined } : employee
        ));
        setHistoryRecords((prev) => {
          const others = prev.filter((r) => r.employeeId !== id);
          return [...historyData, ...others];
        });
      } catch (error) {
        setSaveMessage(error instanceof Error ? error.message : "Gagal memuat komponen gaji.");
      }
    }
  }

  function openSalaryForm(employee: Employee) {
    if (!isAdmin) {
      setSaveMessage("Akses Ditolak: Hanya pengguna dengan role 'Admin HR' yang berwenang mengatur komponen gaji.");
      return;
    }
    const salary = employee.salaryComponent;
    if (salary) {
      const allowances = salary.allowances && salary.allowances.length > 0
        ? salary.allowances.map((a) => ({ id: a.id, name: a.name, amount: String(a.amount) }))
        : salary.fixedAllowance > 0
          ? [{ id: `al-${Date.now()}-1`, name: "Tunjangan Tetap", amount: String(salary.fixedAllowance) }]
          : [];
      const deductions = salary.deductions && salary.deductions.length > 0
        ? salary.deductions.map((d) => ({ id: d.id, name: d.name, amount: String(d.amount) }))
        : salary.deduction > 0
          ? [{ id: `de-${Date.now()}-1`, name: "Potongan", amount: String(salary.deduction) }]
          : [];
      setFormValues({
        basicSalary: String(salary.basicSalary),
        allowances,
        deductions,
      });
    } else {
      setFormValues({
        basicSalary: "",
        allowances: [
          { id: `al-${Date.now()}-1`, name: "Tunjangan Transport", amount: "500000" },
          { id: `al-${Date.now()}-2`, name: "Tunjangan Makan", amount: "250000" },
        ],
        deductions: [
          { id: `de-${Date.now()}-1`, name: "BPJS Ketenagakerjaan", amount: "100000" },
        ],
      });
    }
    setFormErrors({});
    setSaveMessage("");
    setIsEditingSalary(true);
  }

  function cancelSalaryForm() {
    setIsEditingSalary(false);
    setFormErrors({});
    setSaveMessage("");
  }

  function updateBasicSalary(value: string) {
    const next = { ...formValues, basicSalary: value };
    setFormValues(next);
    if (formErrors.basicSalary) {
      const errs = validateSalary(next);
      setFormErrors((prev) => ({ ...prev, basicSalary: errs.basicSalary }));
    }
  }

  // Allowance handlers
  function addAllowance(presetName = "") {
    setFormValues((prev) => ({
      ...prev,
      allowances: [
        ...prev.allowances,
        {
          id: `al-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          name: presetName ? `Tunjangan ${presetName}` : "",
          amount: "",
        },
      ],
    }));
  }

  function removeAllowance(index: number) {
    setFormValues((prev) => ({
      ...prev,
      allowances: prev.allowances.filter((_, i) => i !== index),
    }));
    setFormErrors((prev) => {
      if (!prev.allowances) return prev;
      const nextErrs = { ...prev.allowances };
      delete nextErrs[index];
      return { ...prev, allowances: nextErrs };
    });
  }

  function updateAllowance(index: number, field: "name" | "amount", value: string) {
    setFormValues((prev) => {
      const nextAllowances = [...prev.allowances];
      nextAllowances[index] = { ...nextAllowances[index], [field]: value };
      return { ...prev, allowances: nextAllowances };
    });
    setFormErrors((prev) => {
      if (!prev.allowances || !prev.allowances[index]) return prev;
      const nextErrs = { ...prev.allowances };
      delete nextErrs[index][field];
      if (Object.keys(nextErrs[index]).length === 0) delete nextErrs[index];
      return { ...prev, allowances: Object.keys(nextErrs).length ? nextErrs : undefined };
    });
  }

  // Deduction handlers
  function addDeduction(presetName = "") {
    setFormValues((prev) => ({
      ...prev,
      deductions: [
        ...prev.deductions,
        {
          id: `de-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          name: presetName || "",
          amount: "",
        },
      ],
    }));
  }

  function removeDeduction(index: number) {
    setFormValues((prev) => ({
      ...prev,
      deductions: prev.deductions.filter((_, i) => i !== index),
    }));
    setFormErrors((prev) => {
      if (!prev.deductions) return prev;
      const nextErrs = { ...prev.deductions };
      delete nextErrs[index];
      return { ...prev, deductions: nextErrs };
    });
  }

  function updateDeduction(index: number, field: "name" | "amount", value: string) {
    setFormValues((prev) => {
      const nextDeductions = [...prev.deductions];
      nextDeductions[index] = { ...nextDeductions[index], [field]: value };
      return { ...prev, deductions: nextDeductions };
    });
    setFormErrors((prev) => {
      if (!prev.deductions || !prev.deductions[index]) return prev;
      const nextErrs = { ...prev.deductions };
      delete nextErrs[index][field];
      if (Object.keys(nextErrs[index]).length === 0) delete nextErrs[index];
      return { ...prev, deductions: Object.keys(nextErrs).length ? nextErrs : undefined };
    });
  }

  // Totals & Calculations (AC1)
  const calcBasicSalary = useMemo(() => {
    const val = Number(formValues.basicSalary);
    return Number.isFinite(val) && val > 0 ? Math.floor(val) : 0;
  }, [formValues.basicSalary]);

  const calcTotalAllowances = useMemo(() => {
    return formValues.allowances.reduce((acc, curr) => {
      const val = Number(curr.amount);
      return acc + (Number.isFinite(val) && val > 0 ? Math.floor(val) : 0);
    }, 0);
  }, [formValues.allowances]);

  const calcTotalDeductions = useMemo(() => {
    return formValues.deductions.reduce((acc, curr) => {
      const val = Number(curr.amount);
      return acc + (Number.isFinite(val) && val > 0 ? Math.floor(val) : 0);
    }, 0);
  }, [formValues.deductions]);

  const calcTakeHomePay = useMemo(() => {
    return Math.max(0, calcBasicSalary + calcTotalAllowances - calcTotalDeductions);
  }, [calcBasicSalary, calcTotalAllowances, calcTotalDeductions]);

  async function submitSalaryForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEmployee || isSavingSalary) return;
    if (!isAdmin) {
      setSaveMessage("Akses Ditolak: Hanya pengguna dengan role 'Admin HR' yang berwenang menyimpan komponen gaji.");
      return;
    }
    const errors = validateSalary(formValues);
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) return;

    // AC4: Store each component separately with its name and amount
    const allowancesData: SalaryItem[] = formValues.allowances.map((item, idx) => ({
      id: item.id || `al-${idx + 1}`,
      name: item.name.trim(),
      amount: item.amount.trim() === "" ? 0 : Number(item.amount),
    }));

    const deductionsData: SalaryItem[] = formValues.deductions.map((item, idx) => ({
      id: item.id || `de-${idx + 1}`,
      name: item.name.trim(),
      amount: item.amount.trim() === "" ? 0 : Number(item.amount),
    }));

    const sumAllowance = allowancesData.reduce((acc, curr) => acc + curr.amount, 0);
    const sumDeduction = deductionsData.reduce((acc, curr) => acc + curr.amount, 0);

    const requestedSalary: SalaryComponent = {
      basicSalary: Number(formValues.basicSalary),
      fixedAllowance: sumAllowance,
      deduction: sumDeduction,
      allowances: allowancesData,
      deductions: deductionsData,
    };

    const now = new Date();
    const nextPeriod = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    const effectiveFrom = `${nextPeriod.getFullYear()}-${String(nextPeriod.getMonth() + 1).padStart(2, "0")}-01`;

    setIsSavingSalary(true);
    setSaveMessage("");
    try {
      const savedSalary = await saveSalaryComponent(
        selectedEmployee.id,
        { ...requestedSalary, effectiveFrom },
        Boolean(selectedEmployee.salaryComponent),
      );
      const historyEntry: SalaryHistoryRecord = {
        id: `local-${Date.now()}`,
        employeeId: selectedEmployee.id,
        oldValue: selectedEmployee.salaryComponent ?? null,
        newValue: savedSalary,
        changedBy: "Rani K. (Admin HR)",
        changedAt: new Date().toISOString(),
      };
      setEmployees((old) => old.map((employee) =>
        employee.id === selectedEmployee.id ? { ...employee, salaryComponent: savedSalary } : employee
      ));
      if (USE_MOCK_DATA) {
        saveStoredMockHistory(historyEntry);
        setHistoryRecords((old) => [historyEntry, ...old]);
      } else {
        const freshHistory = await getSalaryHistory(selectedEmployee.id);
        setHistoryRecords((prev) => {
          const others = prev.filter((r) => r.employeeId !== selectedEmployee.id);
          return [...freshHistory, ...others];
        });
      }
      setShowHistory(false);
      setIsEditingSalary(false);
      setFormErrors({});
      setSaveMessage(USE_MOCK_DATA
        ? `Komponen gaji berhasil disimpan. Berlaku mulai ${effectiveFrom}.`
        : `Komponen gaji berhasil disimpan. Berlaku mulai ${effectiveFrom}.`);
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : "Komponen gaji gagal disimpan. Silakan coba lagi.");
    } finally {
      setIsSavingSalary(false);
    }
  }

  const hasFormErrors = Boolean(
    formErrors.basicSalary ||
    (formErrors.allowances && Object.keys(formErrors.allowances).length > 0) ||
    (formErrors.deductions && Object.keys(formErrors.deductions).length > 0)
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="icon-button mobile-menu-button" aria-label={mobileMenuOpen ? "Tutup menu" : "Buka menu"} onClick={() => setMobileMenuOpen((open) => !open)}>
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <a className="brand" href="#" aria-label="Araya Business Hub beranda"><span className="brand-mark"><Banknote size={19} /></span><span>Araya Business Hub</span></a>
        <div className="global-search"><Search size={17} aria-hidden="true" /><span>Cari menu atau halaman...</span><kbd>⌘ K</kbd></div>
        <div className="topbar-actions">
          <button className="icon-button" aria-label="Bantuan"><CircleHelp size={19} /></button>
          <button className="icon-button" aria-label="Notifikasi"><Bell size={19} /></button>

          <div className="profile-dropdown-container">
            <button
              type="button"
              className="profile-button"
              onClick={() => setProfileDropdownOpen((prev) => !prev)}
              aria-expanded={profileDropdownOpen}
              aria-haspopup="true"
              title="Klik untuk mengganti akun / role"
            >
              <span className={`avatar ${currentRole === "Admin HR" ? "" : "avatar-employee"}`}>
                {currentRole === "Admin HR" ? "RK" : "AP"}
              </span>
              <span className="profile-name">
                {currentRole === "Admin HR" ? "Rani K. (Admin HR)" : "Andi Pratama (Pegawai)"}
              </span>
              <ChevronDown
                size={15}
                style={{
                  transform: profileDropdownOpen ? "rotate(180deg)" : "none",
                  transition: "transform .2s ease",
                }}
              />
            </button>

            {profileDropdownOpen && (
              <>
                <div className="dropdown-backdrop" onClick={() => setProfileDropdownOpen(false)} />
                <div className="profile-dropdown-menu" role="menu">
                  <div className="dropdown-header">
                    <span>GANTI AKUN & ROLE</span>
                    <small>Uji otorisasi izin role Admin HR</small>
                  </div>

                  <button
                    type="button"
                    className={`dropdown-item ${currentRole === "Admin HR" ? "active" : ""}`}
                    onClick={() => {
                      setCurrentRole("Admin HR");
                      setActiveRole("Admin HR");
                      setProfileDropdownOpen(false);
                    }}
                    role="menuitem"
                  >
                    <span className="avatar">RK</span>
                    <div className="item-info">
                      <strong>Rani K.</strong>
                      <span className="item-role-badge badge-admin">Admin HR (Izin Penuh)</span>
                    </div>
                    {currentRole === "Admin HR" && <CheckCircle2 size={16} className="text-primary-strong" />}
                  </button>

                  <button
                    type="button"
                    className={`dropdown-item ${currentRole === "Employee" ? "active" : ""}`}
                    onClick={() => {
                      setCurrentRole("Employee");
                      setActiveRole("Employee");
                      setProfileDropdownOpen(false);
                    }}
                    role="menuitem"
                  >
                    <span className="avatar avatar-employee">AP</span>
                    <div className="item-info">
                      <strong>Andi Pratama</strong>
                      <span className="item-role-badge badge-employee">Employee (Bukan Admin)</span>
                    </div>
                    {currentRole === "Employee" && <CheckCircle2 size={16} className="text-primary-strong" />}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {mobileMenuOpen && <button className="mobile-overlay" aria-label="Tutup menu" onClick={() => setMobileMenuOpen(false)} />}
      <aside className={`sidebar ${mobileMenuOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-label">MODUL SDM</div>
        <nav aria-label="Navigasi modul SDM">
          <a className="nav-item" href="#dashboard"><LayoutDashboard size={18} /> Ringkasan</a>
          <a className="nav-item" href="#karyawan"><Users size={18} /> Data karyawan</a>
          <a className="nav-item active" href="#komponen-gaji" aria-current="page"><Banknote size={18} /> Komponen gaji</a>
          <a className="nav-item" href="#laporan"><FileText size={18} /> Laporan</a>
        </nav>
        <div className="sidebar-bottom"><a className="nav-item" href="#pengaturan"><Settings size={18} /> Pengaturan</a><div className="sidebar-note"><span className="status-dot" /><span>Backend: PHP 8.4</span></div></div>
      </aside>

      <main className="main-content" id="komponen-gaji">
        <div className="breadcrumb"><span>SDM</span><span className="crumb-separator">/</span><span>Penggajian</span><span className="crumb-separator">/</span><strong>Komponen gaji</strong></div>
        <div className="page-heading">
          <div>
            <h1>Pengaturan Komponen Gaji per Karyawan</h1>
            <p>Atur gaji pokok, rincian tunjangan tetap, dan potongan yang terpisah dengan nama dan nominalnya (AC1 & AC4).</p>
          </div>
          <span className="prototype-badge">Backend PHP 8.4 · AC1 & AC4</span>
        </div>

        <section className="content-card" aria-labelledby="employee-list-heading">
          <div className="card-heading"><div><h2 id="employee-list-heading">Daftar karyawan</h2><p>Pilih karyawan untuk melihat rincian komponen atau memperbarui nilai gaji.</p></div><span className="count-badge">{filteredEmployees.length} karyawan</span></div>
          <div className="table-toolbar">
            <label className="search-field"><Search size={18} aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari nama atau NIK..." aria-label="Cari nama atau NIK karyawan" />{query && <button className="clear-search" onClick={() => setQuery("")} aria-label="Hapus pencarian"><X size={16} /></button>}</label>
            <span className="toolbar-hint">Pencarian berdasarkan nama atau NIK</span>
          </div>
          <div className="table-scroll"><table>
            <thead><tr><th>Karyawan</th><th>NIK</th><th>Departemen</th><th>Status komponen gaji</th><th className="align-right">Aksi</th></tr></thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-search">
                      <strong>Memuat daftar karyawan...</strong>
                      <span>Mohon tunggu sebentar.</span>
                    </div>
                  </td>
                </tr>
              ) : loadError ? (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-search">
                      <strong>Daftar karyawan gagal dimuat</strong>
                      <span>Coba periksa server backend PHP 8.4 atau muat ulang halaman.</span>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => window.location.reload()}
                      >
                        Muat ulang
                      </button>
                    </div>
                  </td>
                </tr>
              ) : filteredEmployees.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <div className="empty-search">
                      <Search size={25} />
                      <strong>Karyawan tidak ditemukan</strong>
                      <span>Coba periksa kembali nama atau NIK yang kamu masukkan.</span>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => setQuery("")}
                      >
                        Hapus pencarian
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredEmployees.map((employee) => {
                  const selected = selectedId === employee.id;

                  return (
                    <tr
                      key={employee.id}
                      className={selected ? "selected-row" : ""}
                    >
                      <td>
                        <div className="employee-cell">
                          <span className="employee-avatar">
                            {initials(employee.name)}
                          </span>
                          <span className="employee-info">
                            <strong>{employee.name}</strong>
                            <small>{employee.position}</small>
                          </span>
                        </div>
                      </td>
                      <td className="numeric-text">{employee.nik}</td>
                      <td>{employee.department}</td>
                      <td>
                        {employee.salaryComponent ? (
                          <span className="status-badge status-success">
                            <CheckCircle2 size={14} /> Sudah diatur ({formatRupiah(employee.salaryComponent.basicSalary + employee.salaryComponent.fixedAllowance - employee.salaryComponent.deduction)})
                          </span>
                        ) : (
                          <span className="status-badge status-pending">
                            <span className="status-dot" /> Belum diatur
                          </span>
                        )}
                      </td>
                      <td className="align-right">
                        <button
                          type="button"
                          className={`text-button ${selected ? "text-button-selected" : ""}`}
                          onClick={() =>
                            selected
                              ? (setSelectedId(null), cancelSalaryForm())
                              : selectEmployee(employee.id)
                          }
                          aria-pressed={selected}
                        >
                          {selected ? "Tutup" : "Pilih"}
                          <ArrowUpRight size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table></div>
          <div className="table-footer"><span>Menampilkan {filteredEmployees.length} dari {employees.length} karyawan</span><span className="demo-note">Task T1: M14-US1 Pengaturan Komponen Gaji (AC1 & AC4)</span></div>
        </section>

        {selectedEmployee && <section className="detail-card" aria-live="polite">
          <div className="detail-heading">
            <div>
              <span className="eyebrow">KARYAWAN TERPILIH</span>
              <h2>{selectedEmployee.name}</h2>
              <p>{selectedEmployee.nik} · {selectedEmployee.department} · {selectedEmployee.position}</p>
            </div>
            <button className="icon-button" onClick={() => { setSelectedId(null); cancelSalaryForm(); }} aria-label="Tutup detail"><X size={18} /></button>
          </div>

          {!isAdmin && (
            <div className="role-indicator-banner">
              <Eye size={16} />
              <span>Mode Akses: <strong>Pegawai (Hanya Lihat)</strong> — Anda hanya dapat melihat rincian komponen gaji. Pengaturan dan pengubahan komponen gaji hanya dapat dilakukan oleh <strong>Admin HR</strong>.</span>
            </div>
          )}

          <div className="history-toolbar">
            <div className="history-toolbar-copy">
              <History size={18} />
              <div><strong>Riwayat perubahan</strong><small>Lihat jejak perubahan komponen gaji beserta rincian namanya</small></div>
            </div>
            <button
              type="button"
              className="button-secondary history-toggle"
              onClick={async () => {
                if (!showHistory && !USE_MOCK_DATA) {
                  try {
                    const fresh = await getSalaryHistory(selectedEmployee.id);
                    setHistoryRecords((prev) => {
                      const others = prev.filter((r) => r.employeeId !== selectedEmployee.id);
                      return [...fresh, ...others];
                    });
                  } catch (e) {
                    console.error("Gagal memuat riwayat:", e);
                  }
                }
                setShowHistory((visible) => !visible);
              }}
              aria-expanded={showHistory}
            >
              <History size={16} /> {showHistory ? "Sembunyikan riwayat" : "Lihat riwayat"}
            </button>
          </div>

          {showHistory && <section className="history-panel" aria-label="Riwayat perubahan komponen gaji">
            <div className="history-panel-heading">
              <div><h3>Riwayat komponen gaji</h3><p>{selectedEmployee.name} · NIK {selectedEmployee.nik}</p></div>
              <span className="history-count">{historyRecords.filter((record) => record.employeeId === selectedEmployee.id).length} catatan</span>
            </div>
            <p className="history-demo-note"><Info size={15} /> Riwayat mencatat perubahan nilai gaji pokok dan rincian komponen tunjangan/potongan.</p>
            {historyRecords.filter((record) => record.employeeId === selectedEmployee.id).length === 0 ? (
              <div className="history-empty"><History size={24} /><strong>Belum ada riwayat perubahan</strong><span>Riwayat akan muncul setelah komponen gaji diubah dan disimpan.</span></div>
            ) : (
              <div className="history-list">
                {historyRecords.filter((record) => record.employeeId === selectedEmployee.id).map((record) => (
                  <article className="history-record" key={record.id}>
                    <div className="history-record-top">
                      <span className="history-event"><Clock3 size={15} /> Perubahan komponen gaji</span>
                      <time dateTime={record.changedAt}>{formatDateTime(record.changedAt)} WIB</time>
                    </div>
                    <div className="history-values">
                      <div className="history-value old-value"><span>Nilai lama</span><p>{formatSalarySnapshot(record.oldValue)}</p></div>
                      <div className="history-value new-value"><span>Nilai baru</span><p>{formatSalarySnapshot(record.newValue)}</p></div>
                    </div>
                    <div className="history-actor"><UserRound size={15} /><span>Diubah oleh <strong>{record.changedBy}</strong></span></div>
                  </article>
                ))}
              </div>
            )}
          </section>}

          {isEditingSalary ? (
            <form className="salary-form" onSubmit={submitSalaryForm} noValidate>
              <div className="form-heading">
                <div>
                  <h3>{selectedEmployee.salaryComponent ? "Edit Komponen Gaji" : "Atur Komponen Gaji"}</h3>
                  <p>Mendukung gaji pokok serta penambahan beberapa tunjangan tetap dan potongan terpisah dengan nama dan nominalnya (AC1 & AC4).</p>
                </div>
                <span className="required-note">* Wajib diisi</span>
              </div>

              {/* 1. Gaji Pokok */}
              <div className="form-section-card">
                <div className="section-title-row">
                  <div className="section-title-label"><Wallet size={17} /><span>1. Gaji Pokok</span></div>
                  <span className="required-badge">* Wajib</span>
                </div>
                <div className="form-field">
                  <label htmlFor="basicSalary">Nominal Gaji Pokok (Rp) <span>*</span></label>
                  <input
                    id="basicSalary"
                    name="basicSalary"
                    type="text"
                    inputMode="numeric"
                    value={formValues.basicSalary}
                    onChange={(e) => updateBasicSalary(e.target.value)}
                    aria-invalid={Boolean(formErrors.basicSalary)}
                    placeholder="Contoh: 5000000"
                  />
                  {formErrors.basicSalary ? (
                    <small className="field-error" id="basicSalary-error">{formErrors.basicSalary}</small>
                  ) : (
                    <small className="field-help" id="basicSalary-help">Gaji pokok dasar karyawan (wajib lebih besar dari Rp 0).</small>
                  )}
                </div>
              </div>

              {/* 2. Tunjangan Tetap (AC4: Mendukung beberapa tunjangan terpisah) */}
              <div className="form-section-card">
                <div className="section-title-row">
                  <div className="section-title-label">
                    <PlusCircle size={17} />
                    <span>2. Tunjangan Tetap (AC4)</span>
                  </div>
                  <span className="subtotal-badge">
                    Subtotal: <strong>{formatRupiah(calcTotalAllowances)}</strong>
                  </span>
                </div>
                <p className="section-description">
                  Tambahkan satu atau beberapa jenis tunjangan tetap (mis. Transport, Makan, Kehadiran, Komunikasi) dengan nama dan nominalnya.
                </p>

                {/* Preset Chips */}
                <div className="preset-bar">
                  <span className="preset-label">Tambah cepat:</span>
                  {allowancePresets.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className="preset-chip"
                      onClick={() => addAllowance(preset)}
                    >
                      <Plus size={13} /> {preset}
                    </button>
                  ))}
                </div>

                {/* Allowance Item List */}
                {formValues.allowances.length === 0 ? (
                  <div className="empty-items-notice">
                    <Tag size={16} />
                    <span>Belum ada tunjangan tetap yang ditambahkan. Klik tombol di bawah untuk menambah.</span>
                  </div>
                ) : (
                  <div className="dynamic-item-list">
                    {formValues.allowances.map((item, idx) => {
                      const err = formErrors.allowances?.[idx];
                      return (
                        <div className="dynamic-item-row" key={item.id}>
                          <div className="item-field item-name-field">
                            <label htmlFor={`allowance-name-${idx}`}>Nama Tunjangan</label>
                            <input
                              id={`allowance-name-${idx}`}
                              type="text"
                              placeholder="mis. Tunjangan Transport"
                              value={item.name}
                              onChange={(e) => updateAllowance(idx, "name", e.target.value)}
                              aria-invalid={Boolean(err?.name)}
                            />
                            {err?.name && <small className="field-error">{err.name}</small>}
                          </div>
                          <div className="item-field item-amount-field">
                            <label htmlFor={`allowance-amt-${idx}`}>Nominal (Rp)</label>
                            <input
                              id={`allowance-amt-${idx}`}
                              type="text"
                              inputMode="numeric"
                              placeholder="Contoh: 500000"
                              value={item.amount}
                              onChange={(e) => updateAllowance(idx, "amount", e.target.value)}
                              aria-invalid={Boolean(err?.amount)}
                            />
                            {err?.amount && <small className="field-error">{err.amount}</small>}
                          </div>
                          <button
                            type="button"
                            className="btn-remove-item"
                            onClick={() => removeAllowance(idx)}
                            aria-label={`Hapus tunjangan ${item.name || idx + 1}`}
                            title="Hapus baris ini"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <button
                  type="button"
                  className="button-secondary btn-add-custom"
                  onClick={() => addAllowance("")}
                >
                  <Plus size={15} /> Tambah Tunjangan Tetap
                </button>
              </div>

              {/* 3. Potongan (AC4: Mendukung beberapa potongan terpisah) */}
              <div className="form-section-card">
                <div className="section-title-row">
                  <div className="section-title-label">
                    <Receipt size={17} />
                    <span>3. Potongan Gaji (AC4)</span>
                  </div>
                  <span className="subtotal-badge badge-deduction">
                    Subtotal: <strong>{formatRupiah(calcTotalDeductions)}</strong>
                  </span>
                </div>
                <p className="section-description">
                  Tambahkan satu atau beberapa jenis potongan (mis. BPJS Ketenagakerjaan, BPJS Kesehatan, Koperasi) dengan nama dan nominalnya.
                </p>

                {/* Preset Chips */}
                <div className="preset-bar">
                  <span className="preset-label">Tambah cepat:</span>
                  {deductionPresets.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className="preset-chip"
                      onClick={() => addDeduction(preset)}
                    >
                      <Plus size={13} /> {preset}
                    </button>
                  ))}
                </div>

                {/* Deduction Item List */}
                {formValues.deductions.length === 0 ? (
                  <div className="empty-items-notice">
                    <Receipt size={16} />
                    <span>Belum ada potongan gaji yang ditambahkan. Klik tombol di bawah untuk menambah.</span>
                  </div>
                ) : (
                  <div className="dynamic-item-list">
                    {formValues.deductions.map((item, idx) => {
                      const err = formErrors.deductions?.[idx];
                      return (
                        <div className="dynamic-item-row" key={item.id}>
                          <div className="item-field item-name-field">
                            <label htmlFor={`deduction-name-${idx}`}>Nama Potongan</label>
                            <input
                              id={`deduction-name-${idx}`}
                              type="text"
                              placeholder="mis. BPJS Ketenagakerjaan"
                              value={item.name}
                              onChange={(e) => updateDeduction(idx, "name", e.target.value)}
                              aria-invalid={Boolean(err?.name)}
                            />
                            {err?.name && <small className="field-error">{err.name}</small>}
                          </div>
                          <div className="item-field item-amount-field">
                            <label htmlFor={`deduction-amt-${idx}`}>Nominal (Rp)</label>
                            <input
                              id={`deduction-amt-${idx}`}
                              type="text"
                              inputMode="numeric"
                              placeholder="Contoh: 100000"
                              value={item.amount}
                              onChange={(e) => updateDeduction(idx, "amount", e.target.value)}
                              aria-invalid={Boolean(err?.amount)}
                            />
                            {err?.amount && <small className="field-error">{err.amount}</small>}
                          </div>
                          <button
                            type="button"
                            className="btn-remove-item"
                            onClick={() => removeDeduction(idx)}
                            aria-label={`Hapus potongan ${item.name || idx + 1}`}
                            title="Hapus baris ini"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <button
                  type="button"
                  className="button-secondary btn-add-custom"
                  onClick={() => addDeduction("")}
                >
                  <Plus size={15} /> Tambah Potongan
                </button>
              </div>

              {/* Live Dasar Perhitungan Gaji (AC1) */}
              <div className="salary-calc-box">
                <div className="calc-header">
                  <Calculator size={18} />
                  <span>Dasar Perhitungan Gaji Karyawan (AC1)</span>
                </div>
                <div className="calc-grid">
                  <div className="calc-col">
                    <span className="calc-sub">Gaji Pokok</span>
                    <strong>{formatRupiah(calcBasicSalary)}</strong>
                  </div>
                  <span className="calc-operator">+</span>
                  <div className="calc-col">
                    <span className="calc-sub">Total Tunjangan ({formValues.allowances.length} jenis)</span>
                    <strong className="text-success">{formatRupiah(calcTotalAllowances)}</strong>
                  </div>
                  <span className="calc-operator">-</span>
                  <div className="calc-col">
                    <span className="calc-sub">Total Potongan ({formValues.deductions.length} jenis)</span>
                    <strong className="text-danger">{formatRupiah(calcTotalDeductions)}</strong>
                  </div>
                  <span className="calc-operator">=</span>
                  <div className="calc-col calc-highlight">
                    <span className="calc-sub">Estimasi Gaji Bersih (Take-Home Pay)</span>
                    <strong>{formatRupiah(calcTakeHomePay)}</strong>
                  </div>
                </div>
              </div>

              {hasFormErrors && (
                <div className="inline-notice error-notice" role="alert">
                  <Info size={18} />
                  <span>Periksa kembali input yang ditandai merah sebelum menyimpan.</span>
                </div>
              )}
              {saveMessage && (
                <div className="inline-notice error-notice" role="alert">
                  <Info size={18} />
                  <span>{saveMessage}</span>
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="button-secondary" onClick={cancelSalaryForm}>
                  <ArrowLeft size={16} /> Batal
                </button>
                <button type="submit" className="button-primary" disabled={isSavingSalary}>
                  <Save size={16} /> {isSavingSalary ? "Menyimpan ke BE..." : "Simpan Komponen Gaji"}
                </button>
              </div>
            </form>
          ) : selectedEmployee.salaryComponent ? (
            <>
              {/* Summary Cards */}
              <div className="detail-summary detail-summary-4col">
                <div className="summary-item">
                  <span>Gaji pokok</span>
                  <strong>{formatRupiah(selectedEmployee.salaryComponent.basicSalary)}</strong>
                </div>
                <div className="summary-item">
                  <span>Total tunjangan tetap</span>
                  <strong className="text-success">{formatRupiah(selectedEmployee.salaryComponent.fixedAllowance)}</strong>
                  <small className="summary-caption">
                    {selectedEmployee.salaryComponent.allowances?.length ?? 0} jenis tunjangan
                  </small>
                </div>
                <div className="summary-item">
                  <span>Total potongan</span>
                  <strong className="text-danger">{formatRupiah(selectedEmployee.salaryComponent.deduction)}</strong>
                  <small className="summary-caption">
                    {selectedEmployee.salaryComponent.deductions?.length ?? 0} jenis potongan
                  </small>
                </div>
                <div className="summary-item summary-item-highlight">
                  <span>Dasar Perhitungan (Gaji Bersih - AC1)</span>
                  <strong className="text-primary-strong">
                    {formatRupiah(
                      selectedEmployee.salaryComponent.basicSalary +
                      selectedEmployee.salaryComponent.fixedAllowance -
                      selectedEmployee.salaryComponent.deduction
                    )}
                  </strong>
                  <small className="summary-caption">Gaji Pokok + Tunjangan - Potongan</small>
                </div>
              </div>

              {/* Rincian Komponen Terpisah (AC4) */}
              <div className="breakdown-grid">
                {/* Tunjangan Card */}
                <div className="breakdown-card">
                  <div className="breakdown-head">
                    <PlusCircle size={16} className="text-success" />
                    <h4>Rincian Tunjangan Tetap (AC4)</h4>
                  </div>
                  {selectedEmployee.salaryComponent.allowances && selectedEmployee.salaryComponent.allowances.length > 0 ? (
                    <ul className="breakdown-list">
                      {selectedEmployee.salaryComponent.allowances.map((item) => (
                        <li key={item.id} className="breakdown-row">
                          <span className="item-title">{item.name}</span>
                          <span className="item-val text-success">+{formatRupiah(item.amount)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : selectedEmployee.salaryComponent.fixedAllowance > 0 ? (
                    <ul className="breakdown-list">
                      <li className="breakdown-row">
                        <span className="item-title">Tunjangan Tetap Umum</span>
                        <span className="item-val text-success">+{formatRupiah(selectedEmployee.salaryComponent.fixedAllowance)}</span>
                      </li>
                    </ul>
                  ) : (
                    <p className="breakdown-empty">Tidak ada tunjangan tetap yang diatur.</p>
                  )}
                </div>

                {/* Potongan Card */}
                <div className="breakdown-card">
                  <div className="breakdown-head">
                    <Receipt size={16} className="text-danger" />
                    <h4>Rincian Potongan Gaji (AC4)</h4>
                  </div>
                  {selectedEmployee.salaryComponent.deductions && selectedEmployee.salaryComponent.deductions.length > 0 ? (
                    <ul className="breakdown-list">
                      {selectedEmployee.salaryComponent.deductions.map((item) => (
                        <li key={item.id} className="breakdown-row">
                          <span className="item-title">{item.name}</span>
                          <span className="item-val text-danger">-{formatRupiah(item.amount)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : selectedEmployee.salaryComponent.deduction > 0 ? (
                    <ul className="breakdown-list">
                      <li className="breakdown-row">
                        <span className="item-title">Potongan Umum</span>
                        <span className="item-val text-danger">-{formatRupiah(selectedEmployee.salaryComponent.deduction)}</span>
                      </li>
                    </ul>
                  ) : (
                    <p className="breakdown-empty">Tidak ada potongan yang diatur.</p>
                  )}
                </div>
              </div>

              <div className="detail-action-row">
                <div className={`inline-notice ${isAdmin ? "success-notice" : "info-notice"}`}>
                  {isAdmin ? <CheckCircle2 size={18} /> : <Eye size={18} />}
                  <span>{saveMessage || (isAdmin ? "Komponen gaji aktif dan terverifikasi untuk perhitungan penggajian." : "Komponen gaji aktif. Hak akses Pegawai dibatasi hanya untuk melihat (Read-only).")}</span>
                </div>
                {isAdmin ? (
                  <button className="button-primary" onClick={() => openSalaryForm(selectedEmployee)}>
                    <Pencil size={16} /> Edit komponen
                  </button>
                ) : (
                  <div className="role-readonly-badge" title="Pengeditan komponen gaji dinonaktifkan untuk role Pegawai">
                    <Lock size={15} /> Akses Edit Terkunci (Khusus Admin)
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-detail">
              <span className="empty-icon"><Info size={22} /></span>
              <div className="empty-detail-copy">
                <h3>Komponen gaji belum diatur</h3>
                <p>Karyawan ini belum memiliki komponen gaji. Atur gaji pokok serta tunjangan dan potongan agar dapat dipakai sebagai dasar perhitungan gaji.</p>
              </div>
              {isAdmin ? (
                <button className="button-primary empty-detail-action" onClick={() => openSalaryForm(selectedEmployee)}>
                  <Plus size={16} /> Atur komponen
                </button>
              ) : (
                <div className="role-readonly-badge empty-detail-action" title="Pengaturan komponen gaji hanya dapat dilakukan oleh Admin HR">
                  <Lock size={15} /> Khusus Admin HR
                </div>
              )}
            </div>
          )}
        </section>}
        <footer className="page-footer"><span>M14 · Pengaturan komponen gaji per karyawan (AC1 & AC4)</span><span>Backend: Python FastAPI · Frontend: Vite + React</span></footer>
      </main>
    </div>
  );
}
