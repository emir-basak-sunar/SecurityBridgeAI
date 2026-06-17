import { useState, useEffect } from "react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area,
    Legend,
} from "recharts";
import "./Dashboard.css";

interface ChartItem {
    name: string;
    value: number;
}

interface TimelineItem {
    date: string;
    count: number;
}

interface DashboardData {
    total_events: number;
    by_action: ChartItem[];
    by_system: ChartItem[];
    by_listener: ChartItem[];
    timeline: TimelineItem[];
}

const PIE_COLORS = [
    "#2563eb", "#0891b2", "#059669", "#7c3aed", "#d97706",
    "#dc2626", "#0d9488", "#4f46e5", "#c026d3", "#ea580c",
    "#16a34a", "#9333ea", "#0284c7", "#b91c1c", "#ca8a04",
];

export function Dashboard() {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchDashboard();
    }, []);

    const fetchDashboard = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch("http://localhost:8000/api/dashboard");
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            const json = await res.json();
            setData(json);
        } catch (err) {
            setError(`Dashboard verisi yüklenemedi: ${err}`);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="dashboard">
                <div className="dashboard-loading">
                    <div className="spinner" />
                    <span>Dashboard verisi yükleniyor...</span>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="dashboard">
                <div className="dashboard-error">{error || "Veri bulunamadı"}</div>
            </div>
        );
    }

    const topActions = data.by_action.slice(0, 8);
    const shortTimeline = data.timeline.map((t) => ({
        ...t,
        date: t.date.slice(5), // MM-DD
    }));

    return (
        <div className="dashboard">
            {/* KPI Cards */}
            <div className="kpi-row">
                <div className="kpi-card">
                    <div className="kpi-value">{data.total_events.toLocaleString()}</div>
                    <div className="kpi-label">Toplam Olay</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-value">{data.by_action.length}</div>
                    <div className="kpi-label">Aksiyon Tipi</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-value">{data.by_system.length}</div>
                    <div className="kpi-label">Sistem Sayısı</div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-value">{data.by_listener.length}</div>
                    <div className="kpi-label">Listener Sayısı</div>
                </div>
            </div>

            {/* Row 1: Timeline */}
            {shortTimeline.length > 0 && (
                <div className="chart-card full-width">
                    <div className="chart-header">
                        <h3 className="chart-title">Günlük Olay Trendi (Son 30 Gün)</h3>
                        <button className="refresh-btn" onClick={fetchDashboard} title="Yenile">↻</button>
                    </div>
                    <div className="chart-body" style={{ height: 220 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={shortTimeline}>
                                <defs>
                                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <Tooltip
                                    contentStyle={{
                                        background: "#fff", border: "1px solid #e2e8f0",
                                        borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                                    }}
                                />
                                <Area
                                    type="monotone" dataKey="count" name="Olay Sayısı"
                                    stroke="#2563eb" strokeWidth={2}
                                    fill="url(#areaGrad)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* Row 2: Action bar + Action pie */}
            <div className="chart-row">
                <div className="chart-card">
                    <div className="chart-header">
                        <h3 className="chart-title">Olaylar — Aksiyon Tipine Göre</h3>
                    </div>
                    <div className="chart-body" style={{ height: 280 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={topActions} layout="vertical" margin={{ left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis type="number" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <YAxis
                                    dataKey="name" type="category" width={180}
                                    tick={{ fontSize: 11, fill: "#475569" }}
                                    tickFormatter={(v: string) => v.length > 28 ? v.slice(0, 28) + "…" : v}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: "#fff", border: "1px solid #e2e8f0",
                                        borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                                    }}
                                />
                                <Bar dataKey="value" name="Olay Sayısı" radius={[0, 4, 4, 0]}>
                                    {topActions.map((_entry, index) => (
                                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="chart-card">
                    <div className="chart-header">
                        <h3 className="chart-title">Aksiyon Dağılımı</h3>
                    </div>
                    <div className="chart-body" style={{ height: 280 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={topActions} dataKey="value" nameKey="name"
                                    cx="50%" cy="50%" outerRadius={90} innerRadius={45}
                                    paddingAngle={2} strokeWidth={0}
                                    label={((props: { name?: string; percent?: number }) => {
                                        const n = props.name ?? "";
                                        const p = props.percent ?? 0;
                                        return `${n.slice(0, 15)}${n.length > 15 ? "…" : ""} ${(p * 100).toFixed(0)}%`;
                                    }) as unknown as boolean}
                                >
                                    {topActions.map((_entry, index) => (
                                        <Cell key={`pie-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        background: "#fff", border: "1px solid #e2e8f0",
                                        borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Row 3: System bar + Listener bar */}
            <div className="chart-row">
                <div className="chart-card">
                    <div className="chart-header">
                        <h3 className="chart-title">Sistemlere Göre Dağılım</h3>
                    </div>
                    <div className="chart-body" style={{ height: 260 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.by_system.slice(0, 10)}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <Tooltip
                                    contentStyle={{
                                        background: "#fff", border: "1px solid #e2e8f0",
                                        borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                                    }}
                                />
                                <Legend wrapperStyle={{ fontSize: 12 }} />
                                <Bar dataKey="value" name="Olay Sayısı" fill="#0891b2" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="chart-card">
                    <div className="chart-header">
                        <h3 className="chart-title">Listener Dağılımı</h3>
                    </div>
                    <div className="chart-body" style={{ height: 260 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.by_listener.slice(0, 8)}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} />
                                <Tooltip
                                    contentStyle={{
                                        background: "#fff", border: "1px solid #e2e8f0",
                                        borderRadius: 8, fontSize: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                                    }}
                                />
                                <Legend wrapperStyle={{ fontSize: 12 }} />
                                <Bar dataKey="value" name="Olay Sayısı" fill="#7c3aed" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
