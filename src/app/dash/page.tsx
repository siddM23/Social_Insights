"use client";

import React, { useState, useEffect } from "react";
import { RefreshCcw, AlertCircle, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

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

            {/* Followers */}
            <td className="py-4 px-4 text-center">
                <div className="flex flex-col items-center justify-center gap-0.5">
                    <span className="font-bold text-slate-900 text-lg">{m.followersTotal.toLocaleString()}</span>
                    <span className="text-xs text-green-600 font-bold bg-green-50 px-2 py-0.5 rounded-full">+{m.followersNew.toLocaleString()}</span>
                </div>
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
    const [timeRange, setTimeRange] = useState<'7d' | '30d'>('30d');
    const [metrics, setMetrics] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const [isSyncing, setIsSyncing] = useState(false);
    const [syncStatus, setSyncStatus] = useState<{
        sync_count: number;
        sync_limit_stat: boolean;
        last_sync_time: string | null;
        max_limit: number;
    }>({
        sync_count: 0,
        sync_limit_stat: false,
        last_sync_time: null,
        max_limit: 3
    });

    const loadDashboardData = async () => {
        setIsLoading(true);
        let integrations: any[] = [];
        try {
            // 1. Fetch connected integrations (accounts)
            const integrationsRes = await fetch(`${API_URL}/integrations`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (integrationsRes.ok) {
                integrations = await integrationsRes.json();
            }

            // 2. Fetch sync status
            const statusRes = await fetch(`${API_URL}/sync/status`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                setSyncStatus(statusData);
            }

            // 3. Fetch metrics for each account
            if (Array.isArray(integrations) && integrations.length > 0) {
                const promises = integrations.map(async (acc: any) => {
                    const account_id = acc.account_id;
                    // Default / Fallback structure
                    let fullData = {
                        period_7d: {},
                        period_30d: {},
                        followers_total: 0
                    };

                    try {
                        const mRes = await fetch(`${API_URL}/metrics/${acc.platform}/${account_id}`, {
                            headers: { "Authorization": `Bearer ${token}` }
                        });
                        if (mRes.ok) {
                            const mData = await mRes.json();
                            if (Array.isArray(mData) && mData.length > 0) {
                                const latest = mData[0];
                                fullData = latest;
                            }
                        }
                    } catch (err) {
                        console.warn(`Failed fetching metrics for ${account_id}`, err);
                    }

                    return {
                        accountName: acc.account_name || acc.account_id,
                        platform: acc.platform,
                        data: fullData
                    };
                });

                const results = await Promise.all(promises);
                setMetrics(results);
            } else {
                setMetrics([]);
            }

        } catch (e) {
            console.error("Failed to fetch data", e);
            setMetrics([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            const res = await fetch(`${API_URL}/sync`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();

            if (res.ok) {
                console.log("Sync result:", data);

                // 2. Update sync status
                setSyncStatus(prev => ({
                    ...prev,
                    sync_count: data.sync_count,
                    sync_limit_stat: data.limit_reached,
                    last_sync_time: new Date().toISOString()
                }));

                // 3. Wait a moment and then reload data to catch the initial sync results
                setTimeout(() => {
                    loadDashboardData();
                }, 2000);
            } else {
                alert(data.detail || "Failed to trigger sync.");
            }
        } catch (err) {
            console.error("Sync Trigger Error:", err);
            alert("Unable to reach sync service. This might be a timeout or a temporary server issue. Refreshing data now anyway...");
            setTimeout(() => loadDashboardData(), 2000);
        } finally {
            setIsSyncing(false);
        }
    };

    useEffect(() => {
        loadDashboardData();
    }, []);

    // Helper to extract metric for the selected time range
    const getMetric = (m: any, field: string) => {
        // m is the item from results array: { accountName, platform, data: { ... } }
        const raw = m.data;
        const periodData = timeRange === '7d' ? raw.period_7d : raw.period_30d;

        // If new structure exists, use it
        if (periodData && typeof periodData === 'object') {
            return periodData[field] || 0;
        }

        // Fallback to root (legacy data), but strictly speaking legacy data was undefined period (usually 30d or mixed)
        // If we are asking for 7d and only legacy exists, it's inaccurate but better than 0?
        // Or we return 0. Let's return root if periodData is missing to be safe for now.
        return raw[field] || 0;
    };

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
        instagram: metrics.filter(m => m.platform === 'instagram').map(mapToRowData),
        meta: metrics.filter(m => ['meta', 'facebook'].includes(m.platform)).map(mapToRowData),
        pinterest: metrics.filter(m => m.platform === 'pinterest').map(mapToRowData)
    };

    const renderTable = (platform: string, data: any[]) => {
        if (data.length === 0) return null;

        const isPinterest = platform === 'pinterest';

        return (
            <div className="mb-10 last:mb-0">
                <div className="flex items-center gap-3 mb-4 px-2">
                    <div className={cn(
                        "w-1 h-6 rounded-full",
                        platform === 'instagram' ? "bg-pink-500" : platform === 'meta' ? "bg-blue-600" : "bg-red-600"
                    )} />
                    <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">
                        {platform === 'instagram' ? 'Instagram' : platform === 'meta' ? 'Meta' : 'Pinterest'}
                    </h2>
                    <span className="bg-slate-100 text-slate-500 text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-widest">{data.length} Accounts</span>
                </div>

                <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[1000px]">
                        <thead className="bg-slate-50">
                            {isPinterest ? (
                                <tr>
                                    <th className="py-4 px-6 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Account</th>
                                    <th className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Impressions</th>
                                    <th className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Engagement</th>
                                    <th className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Audience</th>
                                    <th className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Saves</th>
                                </tr>
                            ) : (
                                <>
                                    <tr>
                                        <th rowSpan={2} className="py-4 px-6 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-200/50">Account</th>
                                        <th colSpan={1} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-200/50">Followers</th>
                                        <th colSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-200/50">Views</th>
                                        <th rowSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-200/50">Interactions</th>
                                        <th rowSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400 border-r border-slate-200/50">Profile Visits</th>
                                        <th rowSpan={2} className="py-4 px-4 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Accounts Reached</th>
                                    </tr>
                                    <tr>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-500 bg-slate-100/30 border-r border-slate-200/50 border-t border-slate-200/50">Total / New</th>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-500 bg-slate-100/30 border-t border-slate-200/50">Organic</th>
                                        <th className="py-2 px-4 text-center text-[10px] font-bold text-slate-500 bg-slate-100/30 border-r border-slate-200/50 border-t border-slate-200/50">Ads</th>
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
        <div className="p-8 max-w-[1600px] mx-auto">
            <div className="mb-12 flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">Social Media Reporting</h1>
                    <div className="flex items-center gap-4">
                        <p className="text-slate-500 font-medium">Cross-platform performance analytics </p>
                        <div className="w-1 h-1 rounded-full bg-slate-300" />
                        <span className="text-xs font-bold text-slate-400">{user}</span>
                        <div className="w-1 h-1 rounded-full bg-slate-300" />

                        {/* 7D / 30D Switch */}
                        <div className="flex p-1 bg-slate-100 rounded-xl">
                            <button
                                onClick={() => setTimeRange('7d')}
                                className={cn(
                                    "px-3 py-1 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all",
                                    timeRange === '7d' ? "bg-white text-slate-900 shadow-sm" : "text-slate-400 hover:text-slate-600"
                                )}
                            >
                                7 Days
                            </button>
                            <button
                                onClick={() => setTimeRange('30d')}
                                className={cn(
                                    "px-3 py-1 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all",
                                    timeRange === '30d' ? "bg-white text-slate-900 shadow-sm" : "text-slate-400 hover:text-slate-600"
                                )}
                            >
                                30 Days
                            </button>
                        </div>

                        <button
                            onClick={logout}
                            className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-red-500 transition-colors bg-white px-3 py-1.5 rounded-xl border border-slate-100 shadow-sm"
                        >
                            <LogOut size={12} />
                            Log Out
                        </button>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex flex-col items-end gap-1">
                        <div className="flex items-center gap-2">
                            {/* Last Synced Display */}
                            {syncStatus.last_sync_time && (
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    Last Synced: {new Date(syncStatus.last_sync_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Sync Limit</span>
                            <div className="flex gap-1">
                                {[...Array(syncStatus.max_limit)].map((_, i) => (
                                    <div
                                        key={i}
                                        className={cn(
                                            "w-3 h-1.5 rounded-full transition-all duration-500",
                                            i < syncStatus.sync_count ? "bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" : "bg-slate-200"
                                        )}
                                    />
                                ))}
                            </div>
                        </div>
                        {syncStatus.sync_limit_stat && (
                            <span className="text-[10px] font-bold text-red-500 uppercase tracking-tight flex items-center gap-1">
                                <AlertCircle size={10} /> 3hr Cooldown Active
                            </span>
                        )}
                    </div>

                    <button
                        onClick={handleSync}
                        disabled={isSyncing || isLoading || syncStatus.sync_limit_stat}
                        className={cn(
                            "flex items-center gap-2.5 px-6 py-2.5 rounded-[14px] text-sm font-bold transition-all shadow-lg active:scale-95 group disabled:opacity-50 disabled:cursor-not-allowed",
                            syncStatus.sync_limit_stat
                                ? "bg-slate-100 text-slate-400 border border-slate-200 shadow-none"
                                : "bg-slate-900 border border-slate-900 text-white hover:bg-slate-800 shadow-slate-200"
                        )}
                    >
                        <RefreshCcw size={16} className={cn((isSyncing || isLoading) && "animate-spin")} />
                        {isSyncing ? "Syncing..." : `Sync Data (${syncStatus.sync_count}/${syncStatus.max_limit})`}
                    </button>
                </div>
            </div>

            <div className="space-y-6">
                {metrics.length > 0 ? (
                    <>
                        {renderTable('instagram', groupedMetrics.instagram)}
                        {renderTable('meta', groupedMetrics.meta)}
                        {renderTable('pinterest', groupedMetrics.pinterest)}
                    </>
                ) : (
                    <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 flex flex-col items-center justify-center h-[400px] text-slate-400 gap-4">
                        <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center">
                            <AlertCircle size={32} className="opacity-20" />
                        </div>
                        <div className="text-center">
                            <p className="font-bold text-slate-900">No cross-platform data synced</p>
                            <p className="text-sm"></p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
