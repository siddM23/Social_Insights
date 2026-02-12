"use client";

import React, { useState, useEffect } from "react";
import { Plus, X, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronRight, Instagram, Facebook, LayoutGrid, Chrome } from "lucide-react";
import { cn } from "@/lib/utils";

interface PlatformCardProps {
    id: string;
    title: string;
    description?: string;
    icon: React.ReactNode;
    accounts: { email: string; status: "Active" | "Inactive"; account_id: string; account_name: string }[];
    accentColor: string;
    onConnect: () => void;
    onRemove: (accountId: string) => void;
    isActive?: boolean;
}

const PlatformCard: React.FC<PlatformCardProps> = ({
    id,
    title,
    description,
    icon,
    accounts,
    accentColor,
    onConnect,
    onRemove,
    isActive = true
}) => {
    const [isExpanded, setIsExpanded] = useState(id === "instagram");

    return (
        <div className={cn(
            "group bg-white rounded-[2rem] border border-slate-200 shadow-xl shadow-slate-200/40 overflow-hidden transition-all duration-500 mb-6",
            !isActive && "opacity-60 grayscale-[0.5] bg-slate-50/50"
        )}>
            {/* Header / Trigger */}
            <div
                onClick={() => isActive && setIsExpanded(!isExpanded)}
                className={cn(
                    "p-6 flex items-center justify-between cursor-pointer select-none transition-colors",
                    isExpanded ? "bg-slate-50/50" : "hover:bg-slate-50/30"
                )}
            >
                <div className="flex items-center gap-5">
                    <div className={cn(
                        "w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm transition-transform duration-500 group-hover:scale-110",
                        accentColor
                    )}>
                        {icon}
                    </div>
                    <div>
                        <div className="flex items-center gap-3">
                            <h3 className="text-xl font-black text-slate-900 tracking-tight">{title}</h3>
                            <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full uppercase tracking-widest">
                                {accounts.length} {accounts.length === 1 ? 'Account' : 'Accounts'}
                            </span>
                        </div>
                        <p className="text-sm text-slate-500 font-medium">{description}</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {isActive ? (
                        <div className={cn(
                            "w-10 h-10 rounded-full flex items-center justify-center bg-slate-100 text-slate-400 border border-slate-200 transition-all duration-300",
                            isExpanded ? "rotate-180 bg-slate-900 text-white border-slate-900 shadow-md" : "group-hover:bg-slate-200"
                        )}>
                            <ChevronDown size={18} strokeWidth={3} />
                        </div>
                    ) : (
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">Coming Soon</span>
                    )}
                </div>
            </div>

            {/* Collapsible Content */}
            <div className={cn(
                "grid transition-all duration-500 ease-in-out overflow-hidden",
                isExpanded ? "grid-rows-[1fr] opacity-100 border-t border-slate-100" : "grid-rows-[0fr] opacity-0"
            )}>
                <div className="min-h-0">
                    <div className="p-8 space-y-6">
                        {/* Connected Accounts List */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {accounts.length > 0 ? (
                                accounts.map((acc, i) => (
                                    <div key={acc.account_id || i} className="group/item relative flex items-center justify-between p-5 bg-white border border-slate-100 rounded-3xl hover:border-indigo-200 transition-all shadow-sm hover:shadow-indigo-100/50 hover:-translate-y-1">
                                        <div className="flex flex-col gap-1">
                                            <span className="text-[15px] font-black text-slate-900">{acc.account_name}</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                                                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{acc.account_id}</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onRemove(acc.account_id); }}
                                            className="opacity-0 group-item-hover:opacity-100 text-slate-300 hover:text-red-500 hover:bg-red-50 p-2.5 rounded-2xl transition-all"
                                        >
                                            <X size={18} />
                                        </button>
                                    </div>
                                ))
                            ) : (
                                <div className="col-span-full py-12 flex flex-col items-center justify-center border-2 border-dashed border-slate-100 rounded-[2rem] bg-slate-50/30">
                                    <div className="w-16 h-16 rounded-3xl bg-white border border-slate-100 flex items-center justify-center shadow-sm mb-4">
                                        <AlertCircle size={28} className="text-slate-200" />
                                    </div>
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">No accounts connected yet</p>
                                </div>
                            )}
                        </div>

                        {/* Action Bar */}
                        <div className="pt-4 border-t border-slate-100 flex justify-end">
                            <button
                                onClick={(e) => { e.stopPropagation(); onConnect(); }}
                                className="px-6 py-3.5 bg-slate-900 text-white rounded-2xl text-sm font-black hover:bg-slate-800 transition-all duration-300 flex items-center gap-3 shadow-xl shadow-slate-200 group/btn active:scale-95"
                            >
                                <Plus size={18} strokeWidth={3} className="text-white/60 group-btn-hover:text-white transition-colors" />
                                Add {title} Profile
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function IntegrationsPage() {
    const [connectedAccounts, setConnectedAccounts] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetchIntegrations();

        // Handle OAuth callback status from URL
        const urlParams = new URLSearchParams(window.location.search);
        const status = urlParams.get('status');
        const platform = urlParams.get('platform');
        const count = urlParams.get('count');
        const message = urlParams.get('message');

        if (status === 'success') {
            fetchIntegrations();
            alert(`Successfully connected ${count || 1} ${platform} account(s)!`);
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (status === 'error') {
            alert(`Failed to connect: ${message || "Unknown error"}`);
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, []);

    const handleCompleteSocialAuth = async (token: string, platform: string) => {
        // This function is no longer needed as the backend auto-saves
        console.log("Social auth completed on backend for", platform);
    };

    const fetchIntegrations = async () => {
        try {
            const res = await fetch(`${API_URL}/integrations`);
            const data = await res.json();
            setConnectedAccounts(data);
        } catch (err) {
            console.error("Failed to fetch integrations", err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRemoveAccount = async (platform: string, accountId: string) => {
        if (!confirm(`Are you sure you want to remove this ${platform} account?`)) return;

        try {
            const res = await fetch(`${API_URL}/integrations/${platform}/${accountId}`, {
                method: "DELETE"
            });

            if (res.ok) {
                fetchIntegrations();
            } else {
                alert("Failed to remove account.");
            }
        } catch (err) {
            console.error(err);
            alert("Error removing account.");
        }
    };

    const handleConnectInstagram = () => {
        window.location.href = `${API_URL}/auth/instagram/login`;
    };

    const handleConnectMeta = () => {
        window.location.href = `${API_URL}/auth/meta/login`;
    };

    const handleConnectPinterest = () => {
        window.location.href = `${API_URL}/auth/pinterest/login`;
    };

    const handleConnectYoutube = () => {
        window.location.href = `${API_URL}/auth/youtube/login`;
    };

    const filterAccounts = (platform: string) => {
        return connectedAccounts
            .filter(a => a.platform.toLowerCase() === platform.toLowerCase())
            .map(a => ({
                email: a.email || "N/A",
                status: (a.additional_info?.status || "Active") as "Active" | "Inactive",
                account_id: a.account_id,
                account_name: a.account_name || a.account_id
            }));
    };

    const platforms = [
        {
            id: "instagram",
            title: "Instagram",
            icon: <img src="/instagram1.png" alt="Instagram" className="w-8 h-8 object-contain" />,
            accentColor: "bg-white border border-slate-100",
            onConnect: handleConnectInstagram,
            isActive: true
        },
        {
            id: "facebook",
            title: "Meta",
            icon: <img src="/facebook1.png" alt="Meta" className="w-8 h-8 object-contain" />,
            accentColor: "bg-white border border-slate-100",
            onConnect: handleConnectMeta,
            isActive: true
        },
        {
            id: "pinterest",
            title: "Pinterest",
            icon: <img src="/pinterest1.png" alt="Pinterest" className="w-8 h-8 object-contain" />,
            accentColor: "bg-white border border-slate-100",
            onConnect: handleConnectPinterest,
            isActive: true
        },
        {
            id: "youtube",
            title: "YouTube",
            icon: <img src="/youtube.png" alt="YouTube" className="w-8 h-8 object-contain" />,
            accentColor: "bg-white border border-slate-100",
            onConnect: handleConnectYoutube,
            isActive: true
        }
    ];

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="mb-12 flex items-center justify-between">
                <div>
                    <h1 className="text-4xl font-black text-slate-900 mb-3 tracking-tight">Accounts</h1>
                    <p className="text-slate-500 font-medium">Connect and manage your social platform integrations</p>
                </div>
                <div className="flex items-center gap-3">
                    {isLoading && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-full">
                            <Loader2 className="animate-spin text-slate-500" size={16} />
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Syncing</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="space-y-4">
                {platforms.map((platform) => (
                    <PlatformCard
                        key={platform.id}
                        {...platform}
                        accounts={filterAccounts(platform.id)}
                        onRemove={(accountId) => handleRemoveAccount(platform.id, accountId)}
                    />
                ))}
            </div>
        </div>
    );
}
