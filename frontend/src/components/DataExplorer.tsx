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

    // Extract tabular data from ES result
    const { columns, rows } = useMemo(() => {
        if (!response?.es_result) return { columns: [] as string[], rows: [] as DataRow[] };

        const result = response.es_result as Record<string, unknown>;

        // Try aggregations first
        const aggs = result.aggregations || result.aggs;
        if (aggs && typeof aggs === "object") {
            const aggData = aggs as Record<string, unknown>;
            const aggRows: DataRow[] = [];

            for (const [aggName, aggValue] of Object.entries(aggData)) {
                const agg = aggValue as Record<string, unknown>;
                if (agg?.buckets && Array.isArray(agg.buckets)) {
                    for (const bucket of agg.buckets) {
                        const row: DataRow = {
                            [aggName]: bucket.key as string,
                            count: bucket.doc_count as number,
                        };
                        // Check for nested aggregations
                        for (const [subKey, subVal] of Object.entries(bucket)) {
                            const sub = subVal as Record<string, unknown>;
                            if (sub?.buckets && Array.isArray(sub.buckets)) {
                                row[subKey] = (sub.buckets as Array<{ key: string }>).map((b) => b.key).join(", ");
                            }
                        }
                        aggRows.push(row);
                    }
                }
            }
            if (aggRows.length > 0) {
                return { columns: Object.keys(aggRows[0]), rows: aggRows };
            }
        }

        // Fall back to hits
        const hits = result.hits as Record<string, unknown> | undefined;
        const hitsList = (hits?.hits as Array<Record<string, unknown>>) || [];
        if (hitsList.length > 0) {
            const hitsRows: DataRow[] = hitsList.map((h) => {
                const src = (h._source || {}) as Record<string, string | number>;
                return { ...src };
            });
            const cols = Object.keys(hitsRows[0] || {});
            return { columns: cols, rows: hitsRows };
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
                    <span className="card-icon">📊</span>
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
                    <span className="card-icon">📊</span>
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
                <span className="card-icon">📊</span>
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
