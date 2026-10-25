import { useMemo, useState } from "react";
import {
  AlertTriangle, CalendarDays, Calculator, CheckCircle2, ChevronRight,
  Clock3, Info, RefreshCw, Search, ShieldAlert, Users, X,
} from "lucide-react";
import type { Employee } from "./types/employee";

type Props = { employees: Employee[] };

type PayrollRow = {
  employee: Employee;
  absenceDays: number;
  lateCount: number;
  absenceDeduction: number;
  latenessDeduction: number;
  netSalary: number | null;
  status: "ready" | "missing-component" | "negative";
};

const DEMO_ABSENCE_DEDUCTION_PER_DAY = 150_000;
const DEMO_LATENESS_DEDUCTION_PER_OCCURRENCE = 25_000;

function rupiah(value: number) {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value).replace(/\u00a0/g, " ");
}

function monthLabel(value: string) {
  if (!value) return "Pilih periode";
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("id-ID", {
    month: "long",
    year: "numeric",
    timeZone: "Asia/Jakarta",
  }).format(new Date(year, month - 1, 1));
}

// Simulated M13 attendance summary for UI development only.
function attendanceFor(employeeId: number) {
  const examples: Record<number, { absenceDays: number; lateCount: number }> = {
    1: { absenceDays: 1, lateCount: 3 },
    2: { absenceDays: 0, lateCount: 1 },
    3: { absenceDays: 2, lateCount: 0 },
    4: { absenceDays: 0, lateCount: 0 },
    5: { absenceDays: 0, lateCount: 2 },
  };
  return examples[employeeId] ?? { absenceDays: 0, lateCount: 0 };
}

function buildRows(employees: Employee[]): PayrollRow[] {
  return employees.map((employee): PayrollRow => {
    const attendance = attendanceFor(employee.id);
    if (!employee.salaryComponent) {
      return {
        employee,
        ...attendance,
        absenceDeduction: 0,
        latenessDeduction: 0,
        netSalary: null,
        status: "missing-component",
      };
    }

    const absenceDeduction = attendance.absenceDays * DEMO_ABSENCE_DEDUCTION_PER_DAY;
    const latenessDeduction = attendance.lateCount * DEMO_LATENESS_DEDUCTION_PER_OCCURRENCE;
    const salary = employee.salaryComponent;
    const netSalary =
      salary.basicSalary +
      salary.fixedAllowance -
      salary.deduction -
      absenceDeduction -
      latenessDeduction;

    return {
      employee,
      ...attendance,
      absenceDeduction,
      latenessDeduction,
      netSalary,
      status: netSalary < 0 ? "negative" : "ready",
    };
  });
}

export default function PayrollCalculationPage({ employees }: Props) {
  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const [period, setPeriod] = useState(currentMonth);
  const [hasCalculated, setHasCalculated] = useState(false);
  const [calculatedRows, setCalculatedRows] = useState<PayrollRow[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(null);
  const [calculatedAt, setCalculatedAt] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  const rows = calculatedRows;
  const selectedRow = rows.find((row) => row.employee.id === selectedEmployeeId) ?? null;
  const missingCount = rows.filter((row) => row.status === "missing-component").length;
  const negativeCount = rows.filter((row) => row.status === "negative").length;
  const readyCount = rows.filter((row) => row.status === "ready").length;
  const filteredRows = useMemo(() => {
    const query = searchTerm.trim().toLocaleLowerCase("id-ID");
    return rows.filter((row) => {
      const matchesSearch = !query || row.employee.name.toLocaleLowerCase("id-ID").includes(query) || row.employee.nik.toLocaleLowerCase("id-ID").includes(query);
      const matchesStatus = statusFilter === "all" || row.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [rows, searchTerm, statusFilter]);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const visibleRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  function runCalculation() {
    if (!period) {
      setNotice("Pilih periode gaji terlebih dahulu.");
      return;
    }
    setCalculatedRows(buildRows(employees));
    setHasCalculated(true);
    setCalculatedAt(new Date().toISOString());
    setSelectedEmployeeId(null);
    setSearchTerm("");
    setStatusFilter("all");
    setCurrentPage(1);
    setNotice("Simulasi selesai. Data kehadiran dan tarif potongan belum diambil dari API M13/backend.");
  }

  return (
    <>
      <div className="breadcrumb">
        <span>Keuangan / HR</span><span className="crumb-separator">/</span><strong>Perhitungan gaji</strong>
      </div>
      <div className="page-heading payroll-page-heading">
        <div>
          <h1>Perhitungan gaji</h1>
          <p>Hitung gaji berdasarkan komponen gaji dan rekap kehadiran karyawan.</p>
        </div>
        <span className="prototype-badge">Prototipe · Data simulasi</span>
      </div>

      <section className="content-card payroll-period-card" aria-labelledby="payroll-period-heading">
        <div className="card-heading">
          <div>
            <h2 id="payroll-period-heading">Periode penggajian</h2>
            <p>Pilih periode sebelum menjalankan perhitungan.</p>
          </div>
          <span className="period-status"><span className="status-dot status-dot-neutral" /> Status penguncian belum terhubung</span>
        </div>
        <div className="payroll-period-controls">
          <label className="form-field payroll-period-field" htmlFor="payroll-period">
            <span>Periode gaji</span>
            <span className="month-input-wrap"><CalendarDays size={18} /><input id="payroll-period" type="month" value={period} onChange={(event) => { setPeriod(event.target.value); setNotice(""); setHasCalculated(false); setCalculatedRows([]); setSelectedEmployeeId(null); setCurrentPage(1); }} /></span>
          </label>
          <div className="payroll-period-summary">
            <span>Periode terpilih</span>
            <strong>{monthLabel(period)}</strong>
            <small>Rekap kehadiran M13 akan digunakan setelah API terhubung.</small>
          </div>
          <button className="button-primary payroll-calculate-button" type="button" onClick={runCalculation} disabled={!period}>
            {hasCalculated ? <RefreshCw size={17} /> : <Calculator size={17} />}
            {hasCalculated ? "Hitung ulang" : "Hitung gaji"}
          </button>
        </div>
        {notice && <div className="inline-notice info-notice payroll-notice" role="status"><Info size={18} /><span>{notice}</span></div>}
      </section>

      <div className="payroll-disclaimer">
        <AlertTriangle size={18} />
        <div>
          <strong>Perhitungan masih berupa simulasi</strong>
          <p>Tarif potongan alpa dan keterlambatan di bawah hanya nilai contoh untuk menguji antarmuka, bukan aturan payroll final. Konfirmasi aturan dengan Divisi Keuangan sebelum digunakan untuk gaji sebenarnya.</p>
        </div>
      </div>

      {!hasCalculated ? (
        <section className="content-card payroll-empty-state">
          <span className="payroll-empty-icon"><Calculator size={26} /></span>
          <h2>Perhitungan belum dijalankan</h2>
          <p>Pilih periode, lalu klik <strong>Hitung gaji</strong> untuk melihat contoh tabel hasil dan penanda peringatan.</p>
        </section>
      ) : (
        <>
          <div className="payroll-summary-grid">
            <div className="payroll-summary-card"><span><Users size={17} /> Total karyawan</span><strong>{rows.length}</strong><small>Dalam daftar contoh</small></div>
            <div className="payroll-summary-card summary-ready"><span><CheckCircle2 size={17} /> Siap dihitung</span><strong>{readyCount}</strong><small>Memiliki komponen gaji</small></div>
            <div className="payroll-summary-card summary-warning"><span><AlertTriangle size={17} /> Belum bisa dihitung</span><strong>{missingCount}</strong><small>Komponen gaji belum diatur</small></div>
            <div className="payroll-summary-card summary-danger"><span><ShieldAlert size={17} /> Perlu ditinjau</span><strong>{negativeCount}</strong><small>Hasil bersih negatif</small></div>
          </div>

          <section className="content-card" aria-labelledby="payroll-results-heading">
            <div className="card-heading payroll-results-heading">
              <div><h2 id="payroll-results-heading">Hasil perhitungan gaji</h2><p>{monthLabel(period)} · {rows.length} karyawan pada data simulasi</p></div>
              <span className="count-badge">{filteredRows.length} hasil</span>
            </div>
            <div className="payroll-table-toolbar">
              <label className="payroll-search-field" htmlFor="payroll-search"><Search size={17} /><input id="payroll-search" value={searchTerm} onChange={(event) => { setSearchTerm(event.target.value); setCurrentPage(1); }} placeholder="Cari nama atau NIK" /><span className="sr-only">Cari nama atau NIK karyawan</span></label>
              <label className="payroll-filter-field" htmlFor="payroll-status-filter"><span>Filter status</span><select id="payroll-status-filter" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setCurrentPage(1); }}><option value="all">Semua status</option><option value="ready">Selesai</option><option value="missing-component">Belum bisa dihitung</option><option value="negative">Perlu ditinjau</option></select></label>
            </div>
            <div className="table-scroll">
              <table className="payroll-results-table">
                <thead><tr><th>Karyawan</th><th>Alpa</th><th>Terlambat</th><th>Gaji pokok</th><th>Gaji bersih</th><th>Status</th><th className="align-right">Detail</th></tr></thead>
                <tbody>
                  {visibleRows.map((row) => (
                    <tr key={row.employee.id}>
                      <td><div className="employee-cell"><span className="employee-avatar">{row.employee.name.split(" ").slice(0, 2).map((part) => part[0]).join("").toUpperCase()}</span><span className="employee-info"><strong>{row.employee.name}</strong><small>{row.employee.nik}</small></span></div></td>
                      <td>{row.absenceDays} hari</td>
                      <td>{row.lateCount} kali</td>
                      <td>{row.employee.salaryComponent ? rupiah(row.employee.salaryComponent.basicSalary) : "—"}</td>
                      <td className={row.status === "negative" ? "payroll-negative-value" : ""}>{row.netSalary === null ? "—" : rupiah(row.netSalary)}</td>
                      <td>
                        {row.status === "missing-component" ? <span className="status-badge status-pending"><span className="status-dot" /> Belum bisa dihitung</span> :
                          row.status === "negative" ? <span className="status-badge status-danger"><span className="status-dot status-dot-danger" /> Perlu ditinjau</span> :
                          <span className="status-badge status-success"><span className="status-dot status-dot-success" /> Selesai</span>}
                      </td>
                      <td className="align-right"><button type="button" className="text-button" onClick={() => setSelectedEmployeeId(row.employee.id)}><span>Rincian</span><ChevronRight size={15} /></button></td>
                    </tr>
                  ))}
                  {visibleRows.length === 0 && <tr><td colSpan={7}><div className="empty-search"><strong>Tidak ada hasil yang cocok</strong><span>Ubah kata pencarian atau filter status untuk melihat hasil lain.</span><button type="button" className="button-secondary" onClick={() => { setSearchTerm(""); setStatusFilter("all"); setCurrentPage(1); }}>Atur ulang pencarian</button></div></td></tr>}
                </tbody>
              </table>
            </div>
            <div className="payroll-table-footer">
              <span><Clock3 size={15} /> {calculatedAt ? `Simulasi dijalankan ${new Intl.DateTimeFormat("id-ID", { dateStyle: "medium", timeStyle: "short" }).format(new Date(calculatedAt))}` : ""}</span>
              <div className="payroll-pagination"><label htmlFor="payroll-page-size">Baris <select id="payroll-page-size" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label><span>{filteredRows.length === 0 ? "0 data" : `Menampilkan ${(currentPage - 1) * pageSize + 1}–${Math.min(currentPage * pageSize, filteredRows.length)} dari ${filteredRows.length}`}</span><button type="button" className="button-secondary payroll-page-button" disabled={currentPage <= 1} onClick={() => setCurrentPage((page) => page - 1)}>Sebelumnya</button><button type="button" className="button-secondary payroll-page-button" disabled={currentPage >= pageCount} onClick={() => setCurrentPage((page) => page + 1)}>Berikutnya</button></div>
            </div>
          </section>
        </>
      )}

      {selectedRow && (
        <div className="payroll-detail-backdrop" role="presentation" onClick={() => setSelectedEmployeeId(null)}>
          <section className="payroll-detail-panel" role="dialog" aria-modal="true" aria-labelledby="payroll-detail-title" onClick={(event) => event.stopPropagation()}>
            <div className="payroll-detail-header">
              <div><span className="detail-eyebrow">RINCIAN PENGGAJIAN</span><h2 id="payroll-detail-title">{selectedRow.employee.name}</h2><p>NIK {selectedRow.employee.nik} · {monthLabel(period)}</p></div>
              <button type="button" className="icon-button" aria-label="Tutup rincian" onClick={() => setSelectedEmployeeId(null)}><X size={20} /></button>
            </div>
            {selectedRow.status === "missing-component" ? (
              <div className="inline-notice warning-notice"><AlertTriangle size={18} /><span>Karyawan ini belum memiliki komponen gaji pada M14-US1, sehingga hasil gajinya dilewati.</span></div>
            ) : (
              <>
                <div className="payroll-detail-section"><h3>Pendapatan</h3><div className="payroll-detail-line"><span>Gaji pokok</span><strong>{rupiah(selectedRow.employee.salaryComponent!.basicSalary)}</strong></div><div className="payroll-detail-line"><span>Tunjangan tetap</span><strong>{rupiah(selectedRow.employee.salaryComponent!.fixedAllowance)}</strong></div></div>
                <div className="payroll-detail-section"><h3>Potongan</h3><div className="payroll-detail-line"><span>Potongan tetap</span><strong>− {rupiah(selectedRow.employee.salaryComponent!.deduction)}</strong></div><div className="payroll-detail-line"><span>Potongan alpa ({selectedRow.absenceDays} hari)</span><strong>− {rupiah(selectedRow.absenceDeduction)}</strong></div><div className="payroll-detail-line"><span>Potongan keterlambatan ({selectedRow.lateCount} kali)</span><strong>− {rupiah(selectedRow.latenessDeduction)}</strong></div></div>
                <div className={`payroll-net-total ${selectedRow.status === "negative" ? "payroll-net-negative" : ""}`}><span>Gaji bersih</span><strong>{rupiah(selectedRow.netSalary ?? 0)}</strong></div>
                {selectedRow.status === "negative" && <div className="inline-notice error-notice"><ShieldAlert size={18} /><span>Hasil negatif. Tandai untuk ditinjau; jangan membulatkan diam-diam.</span></div>}
              </>
            )}
            <p className="payroll-detail-footnote">Rincian ini memakai data contoh dan tarif potongan simulasi. Nilai final harus mengikuti aturan Keuangan dan respons API.</p>
            <button type="button" className="button-secondary payroll-close-detail" onClick={() => setSelectedEmployeeId(null)}>Tutup rincian</button>
          </section>
        </div>
      )}
      <footer className="page-footer"><span>M14 · Perhitungan gaji berdasarkan kehadiran</span><span>Capstone Project · Kelompok C5</span></footer>
    </>
  );
}
