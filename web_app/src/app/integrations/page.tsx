"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import Image from "next/image";
import { useAuth } from "@/features/auth/AuthContext";
import { PlatformCard } from "@/features/integrations/components/PlatformCard";
import { useIntegrations } from "@/features/integrations/hooks/useIntegrations";
import { Account } from "@/features/integrations/types";

export default function IntegrationsPage() {
    const { token } = useAuth();
    const { data: connectedAccounts = [], isLoading, deleteIntegration, getConnectUrl } = useIntegrations(token);

    const handleConnect = async (platform: string) => {
        try {
            const url = await getConnectUrl(platform);
            if (url) {
                window.location.href = url;
            }
        } catch (err: any) {
            console.error(`OAuth Error (${platform}):`, err);
            alert(`Failed to start ${platform} OAuth flow: ${err.message || 'Network error'}`);
        }
    };

    const handleDelete = async (platform: string, accountId: string) => {
        if (!confirm("Are you sure you want to disconnect this account?")) return;
        try {
            await deleteIntegration({ platform, accountId });
        } catch (err) {
            console.error(err);
            alert("Error deleting integration");
        }
    };

    const filterAccounts = (platform: string): Account[] => {
        return connectedAccounts
            .filter((a: any) => {
                const p = a?.platform?.toLowerCase();
                if (platform === 'meta') return p === 'meta' || p === 'facebook';
                return p === platform.toLowerCase();
            })
            .map((a: any) => ({
                email: a.email,
                status: a.status || a.additional_info?.status || "Active",
                account_id: a.account_id,
                account_name: a.account_name || a.account_id,
                last_error: a.last_error
            }));
    };

    const platforms = [
        {
            id: "instagram",
            title: "Instagram",
            description: "Connect your Instagram Business accounts",
            icon: <Image src="/instagram1.jpeg" alt="Instagram" width={32} height={32} className="object-contain" />,
            accentColor: "bg-white",
            onConnect: () => handleConnect("instagram")
        },
        {
            id: "meta",
            title: "Meta (Facebook)",
            description: "Connect your Facebook Pages",
            icon: <Image src="/facebook.png" alt="Meta" width={32} height={32} className="object-contain" />,
            accentColor: "bg-white",
            onConnect: () => handleConnect("meta")
        },
        {
            id: "youtube",
            title: "YouTube",
            description: "Connect your YouTube Channels",
            icon: <Image src="/youtube.png" alt="YouTube" width={32} height={32} className="object-contain" />,
            accentColor: "bg-white",
            onConnect: () => handleConnect("youtube")
        },
        {
            id: "pinterest",
            title: "Pinterest",
            description: "Connect your Pinterest accounts",
            icon: <Image src="/pinterest.png" alt="Pinterest" width={32} height={32} className="object-contain" />,
            accentColor: "bg-white",
            onConnect: () => handleConnect("pinterest")
        }
    ];

    return (
        <div className="p-8">
            <div className="mb-12 flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 mb-2">Integrations</h1>
                    <div className="flex items-center gap-4">
                        <p className="text-slate-500">Manage your connected social platforms</p>
                        {isLoading && (
                            <>
                                <div className="w-1 h-1 rounded-full bg-slate-200" />
                                <Loader2 className="animate-spin text-slate-400" size={16} />
                            </>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {platforms.map((platform) => (
                    <PlatformCard
                        key={platform.id}
                        {...platform}
                        accounts={filterAccounts(platform.id)}
                        onDelete={(accountId) => handleDelete(platform.id === 'meta' ? 'facebook' : platform.id, accountId)}
                    />
                ))}
            </div>
        </div>
    );
}
