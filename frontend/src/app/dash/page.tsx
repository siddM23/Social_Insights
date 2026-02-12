"use client";

import React, { useState, useEffect } from "react";
import { RefreshCcw, AlertCircle } from "lucide-react";
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
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function DashPage() {
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
            const integrationsRes = await fetch(`${API_URL}/integrations`);
            if (integrationsRes.ok) {
                integrations = await integrationsRes.json();
            }

            // 2. Fetch sync status
            const statusRes = await fetch(`${API_URL}/sync/status`);
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                setSyncStatus(statusData);
            }

            // 3. Fetch metrics for each account
            if (Array.isArray(integrations) && integrations.length > 0) {
                const promises = integrations.map(async (acc: any) => {
                    const account_id = acc.account_id;
                    let m = {
                        accountName: acc.account_name || acc.account_id,
                        followersTotal: 0,
                        followersNew: 0,
                        viewsOrganic: 0,
                        viewsAds: 0,
                        interactions: 0,
                        profileVisits: 0,
                        accountsReached: 0,
                        saves: 0,
                        platform: acc.platform
                    };

                    try {
                        const mRes = await fetch(`${API_URL}/metrics/${acc.platform}/${account_id}`);
                        if (mRes.ok) {
                            const mData = await mRes.json();
                            if (Array.isArray(mData) && mData.length > 0) {
                                const latest = mData[0];
                                m = {
                                    accountName: acc.account_name || acc.account_id,
                                    followersTotal: parseInt(latest.followers_total) || 0,
                                    followersNew: parseInt(latest.followers_new) || 0,
                                    viewsOrganic: parseInt(latest.views_organic) || 0,
                                    viewsAds: parseInt(latest.views_ads) || 0,
                                    interactions: parseInt(latest.interactions) || 0,
                                    profileVisits: parseInt(latest.profile_visits) || 0,
                                    accountsReached: parseInt(latest.accounts_reached) || 0,
                                    saves: parseInt(latest.saves) || 0,
                                    platform: acc.platform
                                };
                            }
                        }
                    } catch (err) {
                        console.warn(`Failed fetching metrics for ${account_id}`, err);
                    }
                    return m;
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
            const res = await fetch(`${API_URL}/sync`, { method: "POST" });
            const data = await res.json();

            if (res.ok) {
                console.log("Sync result:", data);

                // 1. Update sync status (limit/count)
                setSyncStatus(prev => ({
                    ...prev,
                    sync_count: data.sync_count,
                    sync_limit_stat: data.limit_reached,
                    last_sync_time: new Date().toISOString()
                }));

                // 2. Map live metrics from response directly to UI
                if (data.metrics && Array.isArray(data.metrics)) {
                    const mappedMetrics = data.metrics.map((m: any) => ({
                        accountName: m.account_name || m.account_id,
                        followersTotal: parseInt(m.followers_total) || 0,
                        followersNew: parseInt(m.followers_new) || 0,
                        viewsOrganic: parseInt(m.views_organic) || 0,
                        viewsAds: parseInt(m.views_ads) || 0,
                        interactions: parseInt(m.interactions) || 0,
                        profileVisits: parseInt(m.profile_visits) || 0,
                        accountsReached: parseInt(m.accounts_reached) || 0,
                        saves: parseInt(m.saves) || 0,
                        platform: m.platform || 'instagram'
                    }));
                    setMetrics(mappedMetrics);
                }
            } else {
                alert(data.detail || "Failed to trigger sync.");
            }
        } catch (err) {
            console.error("Error during sync:", err);
            alert("Error connecting to sync service.");
        } finally {
            setIsSyncing(false);
        }
    };

    useEffect(() => {
        loadDashboardData();
    }, []);

    const groupedMetrics = {
        instagram: metrics.filter(m => m.platform === 'instagram'),
        meta: metrics.filter(m => m.platform === 'meta' || m.platform === 'facebook'),
        pinterest: metrics.filter(m => m.platform === 'pinterest')
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
                    <p className="text-slate-500 font-medium">Cross-platform performance analytics </p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex flex-col items-end gap-1">
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
