import { useState, useMemo } from "react";
import type { AgentResponse } from "../types";
import "./DataExplorer.css";

interface Props {
    response: AgentResponse | null;
}

interface DataRow {
    [key: string]: string | number;
}

export function DataExplorer({ response }: Props) {
    const [searchTerm, setSearchTerm] = useState("");
    const [sortField, setSortField] = useState<string>("");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
    const [page, setPage] = useState(0);
    const pageSize = 15;

    // Extract tabular data from SQL result
    const { columns, rows } = useMemo(() => {
        if (!response?.sql_result) return { columns: [] as string[], rows: [] as DataRow[] };

        const result = response.sql_result as Record<string, unknown>;

        // SQL results come as { columns: [...], rows: [...], row_count: N }
        const sqlRows = result.rows as DataRow[] | undefined;
        const sqlColumns = result.columns as string[] | undefined;

        if (sqlRows && Array.isArray(sqlRows) && sqlRows.length > 0) {
            const cols = sqlColumns && Array.isArray(sqlColumns)
                ? sqlColumns
                : Object.keys(sqlRows[0]);
            return { columns: cols, rows: sqlRows };
        }

        // Try trend data (current_week / previous_week)
        const currentWeek = result.current_week as Record<string, unknown> | undefined;
        if (currentWeek?.rows && Array.isArray(currentWeek.rows) && (currentWeek.rows as DataRow[]).length > 0) {
            const cwRows = currentWeek.rows as DataRow[];
            const cols = (currentWeek.columns as string[]) || Object.keys(cwRows[0]);
            return { columns: cols, rows: cwRows };
        }

        return { columns: [] as string[], rows: [] as DataRow[] };
    }, [response]);

    // Filter
    const filtered = useMemo(() => {
        if (!searchTerm) return rows;
        const term = searchTerm.toLowerCase();
        return rows.filter((row) =>
            Object.values(row).some((v) => String(v).toLowerCase().includes(term))
        );
    }, [rows, searchTerm]);

    // Sort
    const sorted = useMemo(() => {
        if (!sortField) return filtered;
        return [...filtered].sort((a, b) => {
            const aVal = a[sortField] ?? "";
            const bVal = b[sortField] ?? "";
            const cmp = typeof aVal === "number" && typeof bVal === "number"
                ? aVal - bVal
                : String(aVal).localeCompare(String(bVal));
            return sortDir === "asc" ? cmp : -cmp;
        });
    }, [filtered, sortField, sortDir]);

    // Paginate
    const totalPages = Math.ceil(sorted.length / pageSize);
    const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

    const handleSort = (col: string) => {
        if (sortField === col) {
            setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        } else {
            setSortField(col);
            setSortDir("asc");
        }
    };

    if (!response) {
        return (
            <div className="data-explorer-card empty">
                <div className="card-header">
                    <span className="card-icon">—</span>
                    <span className="card-title">Veri Gezgini</span>
                </div>
                <div className="card-body">
                    <div className="empty-state">
                        <p>Sorgu çalıştırıldığında veriler burada tablo halinde görünecek</p>
                    </div>
                </div>
            </div>
        );
    }

    if (columns.length === 0) {
        return (
            <div className="data-explorer-card">
                <div className="card-header">
                    <span className="card-icon">—</span>
                    <span className="card-title">Veri Gezgini</span>
                </div>
                <div className="card-body">
                    <div className="empty-state">
                        <p>Bu sorgunun tablo verisi yok</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="data-explorer-card">
            <div className="card-header">
                <span className="card-icon">—</span>
                <span className="card-title">Veri Gezgini</span>
                <span className="data-count">{filtered.length} kayıt</span>
                <div className="search-box">
                    <input
                        type="text"
                        placeholder="Filtrele..."
                        value={searchTerm}
                        onChange={(e) => { setSearchTerm(e.target.value); setPage(0); }}
                    />
                </div>
            </div>
            <div className="card-body table-wrapper">
                <table className="data-table">
                    <thead>
                        <tr>
                            {columns.map((col) => (
                                <th key={col} onClick={() => handleSort(col)} className="sortable">
                                    {col}
                                    {sortField === col && (
                                        <span className="sort-arrow">{sortDir === "asc" ? " ▲" : " ▼"}</span>
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paged.map((row, i) => (
                            <tr key={i}>
                                {columns.map((col) => (
                                    <td key={col}>{String(row[col] ?? "")}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {totalPages > 1 && (
                <div className="pagination">
                    <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                        ‹ Önceki
                    </button>
                    <span className="page-info">
                        {page + 1} / {totalPages}
                    </span>
                    <button disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                        Sonraki ›
                    </button>
                </div>
            )}
        </div>
    );
}
