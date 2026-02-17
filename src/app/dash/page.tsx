"use client";

import React, { useState, useEffect } from "react";
import { RefreshCcw, AlertCircle, LogOut, Clock } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { DateFilter } from "@/components/ui/date-filter";
import { format } from "date-fns";

interface InstagramMetrics {
    platform: 'instagram';
    followersTotal: number;
    followersNew: number;
    viewsOrganic: number;
    viewsAds: number;
    interactions: number;
    profileVisits: number;
    accountsReached: number;
}

interface MetaMetrics {
    platform: 'meta' | 'facebook';
    followersTotal: number;
    followersNew: number;
    viewsOrganic: number; // For Meta these might be impressions
    viewsAds: number;
    interactions: number;
    profileVisits: number;
    accountsReached: number;
}

interface PinterestMetrics {
    platform: 'pinterest';
    viewsOrganic: number; // Impressions
    interactions: number; // Engagement
    followersTotal: number; // Audience
    saves: number;
}

type SocialMetricData = (InstagramMetrics | MetaMetrics | PinterestMetrics) & { accountName: string };

interface MetricItem {
    accountName: string;
    platform: string;
    data: any;
}

const SocialMetricRow: React.FC<SocialMetricData> = (props) => {
    const { platform, accountName } = props;

    if (platform === 'pinterest') {
        const p = props as PinterestMetrics;
        return (
            <tr className="border-b border-slate-100 bg-white hover:bg-slate-50 transition-colors">
                <td className="py-4 px-6 font-semibold text-slate-900 min-w-[200px] text-xs uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-600"></span>
                    {accountName}
                </td>
                <td className="py-4 px-4 text-center font-black text-slate-900 text-lg">{(p.viewsOrganic || 0).toLocaleString()}</td>
                <td className="py-4 px-4 text-center font-bold text-slate-700">{(p.interactions || 0).toLocaleString()}</td>
                <td className="py-4 px-4 text-center font-bold text-indigo-600">{(p.followersTotal || 0).toLocaleString()}</td>
                <td className="py-4 px-4 text-center font-bold text-red-500">{(p.saves || 0).toLocaleString()}</td>
            </tr>
        );
    }

    const m = props as InstagramMetrics | MetaMetrics;
    return (
        <tr className="border-b border-slate-100 bg-white hover:bg-slate-50 transition-colors">
            <td className="py-4 px-6 font-semibold text-slate-900 min-w-[200px] text-xs uppercase tracking-wider flex items-center gap-2">
                <span className={cn(
                    "w-2 h-2 rounded-full",
                    platform === 'instagram' ? "bg-pink-500" : "bg-blue-600"
                )}></span>
                {accountName}
            </td>

            {/* Followers Total */}
            <td className="py-4 px-4 text-center font-bold text-slate-900 text-lg border-r border-slate-100">
                {m.followersTotal.toLocaleString()}
            </td>

            {/* Followers New */}
            <td className="py-4 px-4 text-center">
                <span className="text-xs text-green-600 font-bold bg-green-50 px-2 py-0.5 rounded-full">+{m.followersNew.toLocaleString()}</span>
            </td>

            {/* Views */}
            <td className="py-4 px-4 text-center bg-slate-50/30">
                <div className="flex flex-col items-center">
                    <span className="font-bold text-slate-700">{m.viewsOrganic.toLocaleString()}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Organic</span>
                </div>
            </td>
            <td className="py-4 px-4 text-center border-r border-slate-100/50 bg-slate-50/30">
                <div className="flex flex-col items-center">
                    <span className="font-bold text-slate-700">{m.viewsAds.toLocaleString()}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Ads</span>
                </div>
            </td>

            {/* Interactions */}
            <td className="py-4 px-4 text-center font-bold text-slate-700">{m.interactions.toLocaleString()}</td>

            {/* Profile Visits */}
            <td className="py-4 px-4 text-center font-bold text-slate-700">{m.profileVisits.toLocaleString()}</td>

            {/* Accounts Reached */}
            <td className="py-4 px-4 text-center font-bold text-slate-900 text-lg">{m.accountsReached.toLocaleString()}</td>
        </tr>
    );
};

// Use environment variable for API URL or default to localhost
const API_URL = (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? "http://127.0.0.1:8000"
    : "/api";

export default function DashPage() {
    const { token, logout, user } = useAuth();
    const [timeRange, setTimeRange] = useState<'7d' | '30d' | 'custom'>('7d');
    const [customRange, setCustomRange] = useState<{ start: string; end: string } | null>(null);
    const [activeTab, setActiveTab] = useState("Instagram");
    const [isSyncing, setIsSyncing] = useState(false);

    const queryClient = useQueryClient();
    const platforms = ["Instagram", "Meta", "Youtube", "Pinterest"];

    // 1. Fetch Sync Status
    const { data: syncStatus = { sync_count: 0, sync_limit_stat: false, last_sync_time: null, max_limit: 3 }, refetch: refetchSyncStatus } = useQuery({
        queryKey: ["sync-status"],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/sync/status`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return null;
            return res.json();
        },
        enabled: !!token,
        refetchInterval: 1000 * 30, // 30 seconds
    });

    // 2. Fetch Metrics (Base or Custom)
    const { data: metrics = [], isLoading: isMetricsLoading } = useQuery({
        queryKey: ["metrics", timeRange, customRange],
        queryFn: async () => {
            if (timeRange === 'custom' && customRange) {
                const res = await fetch(`${API_URL}/metrics/custom_range`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        start_date: customRange.start,
                        end_date: customRange.end
                    })
                });
                if (!res.ok) throw new Error("Failed to fetch custom metrics");
                return res.json();
            }

            // Standard fetching (integrations + then metrics for each)
            const integrationsRes = await fetch(`${API_URL}/integrations`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!integrationsRes.ok) return [];
            const integrations = await integrationsRes.json();

            const promises = integrations.map(async (acc: any) => {
                const account_id = acc.account_id;
                let fullData = { period_7d: {}, period_30d: {}, followers_total: 0 };
                try {
                    const mRes = await fetch(`${API_URL}/metrics/${acc.platform}/${account_id}`, {
                        headers: { "Authorization": `Bearer ${token}` }
                    });
                    if (mRes.ok) {
                        const mData = await mRes.json();
                        if (Array.isArray(mData) && mData.length > 0) fullData = mData[0];
                    }
                } catch (err) { console.warn(`Failed for ${account_id}`, err); }

                return {
                    accountName: acc.account_name || acc.account_id,
                    platform: acc.platform,
                    data: fullData
                };
            });

            return Promise.all(promises);
        },
        enabled: !!token,
        staleTime: 1000 * 60 * 5, // 5 minutes
    });

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

    // Helper to extract metric for the selected time range
    const getMetric = (m: any, field: string) => {
        // m is the item from results array: { accountName, platform, data: { ... } }
        const raw = m.data;

        if (timeRange === 'custom') {
            // Check custom_period object
            const custom = raw.custom_period;
            if (custom && typeof custom === 'object') {
                return custom[field] || 0;
            }
            return 0;
        }

        const periodData = timeRange === '7d' ? raw.period_7d : raw.period_30d;

        // If new structure exists, use it
        if (periodData && typeof periodData === 'object') {
            return periodData[field] || 0;
        }

        // Fallback to root (legacy data)
        return raw[field] || 0;
    };

    // Which dataset to use?
    const activeMetrics = metrics;

    const mapToRowData = (m: any) => ({
        accountName: m.accountName,
        platform: m.platform,
        followersTotal: parseInt(m.data.followers_total) || 0, // Total is always at root
        followersNew: parseInt(getMetric(m, 'followers_new')),
        viewsOrganic: parseInt(getMetric(m, 'views_organic')),
        viewsAds: parseInt(getMetric(m, 'views_ads')),
        interactions: parseInt(getMetric(m, 'interactions')),
        profileVisits: parseInt(getMetric(m, 'profile_visits')),
        accountsReached: parseInt(getMetric(m, 'accounts_reached')),
        saves: parseInt(getMetric(m, 'saves'))
    });

    const groupedMetrics = {
        instagram: activeMetrics.filter((m: MetricItem) => m.platform === 'instagram').map(mapToRowData),
        meta: activeMetrics.filter((m: MetricItem) => ['meta', 'facebook'].includes(m.platform)).map(mapToRowData),
        pinterest: activeMetrics.filter((m: MetricItem) => m.platform === 'pinterest').map(mapToRowData),
        youtube: activeMetrics.filter((m: MetricItem) => m.platform === 'youtube').map(mapToRowData)
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
                                            <span className="relative z-10">Followers</span>
                                            <div className="absolute inset-x-4 bottom-2 h-[1px] bg-slate-200/50"></div>
                                        </th>
                                        <th colSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-100 relative">
                                            <span className="relative z-10">Views</span>
                                            <div className="absolute inset-x-4 bottom-2 h-[1px] bg-slate-200/50"></div>
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
            {/* Platform Selector Tabs */}
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
                    {syncStatus.sync_limit_stat && (
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
                        disabled={isSyncing || isMetricsLoading || syncStatus.sync_limit_stat}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed h-10"
                    >
                        <RefreshCcw size={16} className={cn((isSyncing || isMetricsLoading) && "animate-spin")} />
                        {isSyncing ? "Syncing..." : `Sync Data (${syncStatus.sync_count}/${syncStatus.max_limit})`}
                    </button>

                </div>
            </div>

            <div className="space-y-6">
                {(isMetricsLoading && timeRange === 'custom') ? (
                    <div className="bg-white rounded-3xl border border-slate-200 p-12 flex flex-col items-center justify-center gap-4">
                        <RefreshCcw size={32} className="animate-spin text-indigo-500" />
                        <p className="font-bold text-slate-400">Fetching custom metrics...</p>
                    </div>
                ) : activeMetrics.length > 0 ? (
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
