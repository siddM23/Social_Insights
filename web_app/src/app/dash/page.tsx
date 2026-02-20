"use client";

import React, { useState } from "react";
import { RefreshCcw, AlertCircle, Clock } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/AuthContext";
import { cn } from "@/utils";
import { DateFilter } from "@/components/ui/date-filter";
import { format } from "date-fns";
import { SocialMetricRow } from "@/features/dashboard/components/SocialMetricRow";
import { useDashboardMetrics } from "@/features/dashboard/hooks/useDashboardMetrics";
import { MetricItem, TimeRange } from "@/features/dashboard/types";
import { API_URL } from "@/services/api";

export default function DashPage() {
    const { token, user } = useAuth();
    const [timeRange, setTimeRange] = useState<TimeRange>('7d');
    const [customRange, setCustomRange] = useState<{ start: string; end: string } | null>(null);
    const [activeTab, setActiveTab] = useState("Instagram");
    const [isSyncing, setIsSyncing] = useState(false);

    const queryClient = useQueryClient();
    const platforms = ["Instagram", "Meta", "Youtube", "Pinterest"];

    // 1. Fetch Sync Status
    const { data: syncStatus = { sync_count: 0, sync_limit_stat: false, last_sync_time: null, max_limit: 3 } } = useQuery({
        queryKey: ["sync-status"],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/sync/status`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return null;
            return res.json();
        },
        enabled: !!token,
        refetchInterval: 1000 * 30,
    });

    // 2. Fetch Metrics (using our custom hook)
    const { data: metrics = [], isLoading: isMetricsLoading } = useDashboardMetrics(token, timeRange, customRange);

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            const res = await fetch(`${API_URL}/sync`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            if (res.ok) {
                queryClient.invalidateQueries({ queryKey: ["sync-status"] });
                setTimeout(() => {
                    queryClient.invalidateQueries({ queryKey: ["metrics"] });
                }, 2000);
            } else {
                alert(data.detail || "Failed to trigger sync.");
            }
        } catch (err) {
            console.error("Sync Error:", err);
            queryClient.invalidateQueries({ queryKey: ["metrics"] });
        } finally {
            setIsSyncing(false);
        }
    };

    const handleDateRangeChange = async (label: string, start?: Date, end?: Date) => {
        if (label === "Last 7 days") {
            setTimeRange('7d');
            setCustomRange(null);
        } else if (label === "Last 30 days") {
            setTimeRange('30d');
            setCustomRange(null);
        } else if (start && end) {
            setTimeRange('custom');
            setCustomRange({
                start: format(start, "yyyy-MM-dd"),
                end: format(end, "yyyy-MM-dd")
            });
        }
    };

    const getMetric = (m: any, field: string, isPrev = false) => {
        const raw = m.data;
        if (timeRange === 'custom') return (isPrev ? raw.previous_period : raw.custom_period)?.[field] || 0;
        const key = { '7d': isPrev ? 'period_7_14' : 'period_7d', '30d': isPrev ? 'period_30_60' : 'period_30d' }[timeRange as string] || '';
        return raw.raw_metrics?.[key]?.[field] || 0;
    };

    const mapToRowData = (m: any) => {
        const fields = ['followersNew', 'viewsOrganic', 'viewsAds', 'interactions', 'profileVisits', 'accountsReached', 'saves', 'audience'];
        const map = (p: boolean) => Object.fromEntries(fields.map(f => [f, parseInt(getMetric(m, f.replace(/[A-Z]/g, l => `_${l.toLowerCase()}`), p))]));
        return { accountName: m.accountName, platform: m.platform, followersTotal: parseInt(m.data.followers_total) || 0, ...map(false), prevData: { ...map(true), followersTotal: parseInt(getMetric(m, 'followers_total', true)) } };
    };

    const groupedMetrics = {
        instagram: metrics.filter((m: MetricItem) => m.platform === 'instagram').map(mapToRowData),
        meta: metrics.filter((m: MetricItem) => ['meta', 'facebook'].includes(m.platform)).map(mapToRowData),
        pinterest: metrics.filter((m: MetricItem) => m.platform === 'pinterest').map(mapToRowData),
        youtube: metrics.filter((m: MetricItem) => m.platform === 'youtube').map(mapToRowData)
    };

    const renderTable = (platform: string, data: any[]) => {
        if (data.length === 0) return null;
        const isPinterest = platform === 'pinterest';

        return (
            <div className="mb-10 last:mb-0">
                <div className="flex items-center gap-3 mb-6 px-2">
                    <div className={cn(
                        "w-1 h-6 rounded-full",
                        platform === 'instagram' ? "bg-pink-500" : platform === 'meta' ? "bg-blue-600" : "bg-red-600"
                    )} />
                    <h2 className="text-xl font-bold text-slate-900">
                        {platform === 'instagram' ? 'Instagram' : platform === 'meta' ? 'Meta' : 'Pinterest'}
                    </h2>
                    <span className="bg-slate-100 text-slate-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest">{data.length} Accounts</span>
                </div>

                <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[1000px]">
                        <thead className="sticky top-0 z-10 shadow-sm">
                            {isPinterest ? (
                                <tr className="bg-slate-50">
                                    <th className="py-6 px-6 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Account</th>
                                    <th className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Impressions</th>
                                    <th className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Engagement</th>
                                    <th className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Audience</th>
                                    <th className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Saves</th>
                                </tr>
                            ) : (
                                <>
                                    <tr className="bg-slate-50">
                                        <th rowSpan={2} className="py-6 px-6 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Account</th>
                                        <th colSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100 relative">
                                            Followers
                                        </th>
                                        <th colSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100 relative">
                                            Views
                                        </th>
                                        <th rowSpan={2} className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Interactions</th>
                                        <th rowSpan={2} className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100">Profile Visits</th>
                                        <th rowSpan={2} className="py-6 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Accounts Reached</th>
                                    </tr>
                                    <tr className="bg-slate-50 border-b border-slate-100/50">
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-400 bg-slate-50 border-r border-slate-100/50 uppercase tracking-widest">Total</th>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-400 bg-slate-50 border-r border-slate-100/50 uppercase tracking-widest">New</th>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-400 bg-slate-50 uppercase tracking-widest border-r border-slate-100/50">Organic</th>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-400 bg-slate-50 border-r border-slate-100/50 uppercase tracking-widest">Ads</th>
                                    </tr>
                                </>
                            )}
                        </thead>
                        <tbody>
                            {data.map((m, i) => (
                                <SocialMetricRow key={i} {...m} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    return (
        <div className="p-8">
            <div className="flex justify-center mb-10">
                <div className="bg-slate-200/50 p-1 rounded-2xl flex gap-1 overflow-x-auto no-scrollbar max-w-full">
                    {platforms.map(p => (
                        <button
                            key={p}
                            onClick={() => setActiveTab(p)}
                            className={cn(
                                "px-8 py-2.5 rounded-xl text-sm font-bold transition-all duration-300 whitespace-nowrap",
                                activeTab === p
                                    ? "bg-white text-slate-900 shadow-md transform scale-105"
                                    : "text-slate-500 hover:text-slate-700 hover:bg-white/50"
                            )}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mb-8 flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 mb-2">Social Media Reporting</h1>
                    <div className="flex items-center gap-4">
                        <p className="text-slate-500">Cross-platform performance analytics </p>
                        <div className="w-1 h-1 rounded-full bg-slate-200" />
                        <span className="text-xs font-semibold text-slate-400">{user}</span>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {syncStatus?.sync_limit_stat && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl text-sm">
                            <Clock size={16} className="text-amber-500" />
                            <span className="text-amber-700 font-medium whitespace-nowrap">
                                3hr Cooldown Active
                            </span>
                        </div>
                    )}
                    <div className="z-20 ml-2">
                        <DateFilter onRangeChange={handleDateRangeChange} />
                    </div>
                    <button
                        onClick={handleSync}
                        disabled={isSyncing || isMetricsLoading || syncStatus?.sync_limit_stat}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed h-10"
                    >
                        <RefreshCcw size={16} className={cn((isSyncing || isMetricsLoading) && "animate-spin")} />
                        {isSyncing ? "Syncing..." : `Sync Data (${syncStatus?.sync_count || 0}/${syncStatus?.max_limit || 3})`}
                    </button>
                </div>
            </div>

            <div className="space-y-6">
                {(isMetricsLoading && timeRange === 'custom') ? (
                    <div className="bg-white rounded-3xl border border-slate-200 p-12 flex flex-col items-center justify-center gap-4">
                        <RefreshCcw size={32} className="animate-spin text-indigo-500" />
                        <p className="font-bold text-slate-400">Fetching custom metrics...</p>
                    </div>
                ) : metrics.length > 0 ? (
                    <>
                        {activeTab === "Instagram" && renderTable('instagram', groupedMetrics.instagram)}
                        {activeTab === "Meta" && renderTable('meta', groupedMetrics.meta)}
                        {activeTab === "Youtube" && renderTable('youtube', groupedMetrics.youtube)}
                        {activeTab === "Pinterest" && renderTable('pinterest', groupedMetrics.pinterest)}
                    </>
                ) : (
                    <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 flex flex-col items-center justify-center h-[400px] text-slate-400 gap-4">
                        <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center">
                            <AlertCircle size={32} className="opacity-20" />
                        </div>
                        <div className="text-center">
                            <p className="font-bold text-slate-900">No cross-platform data found</p>
                            <p className="text-sm">Try syncing connected accounts or selecting a different date range.</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
