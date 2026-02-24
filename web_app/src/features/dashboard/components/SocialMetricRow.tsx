import React from "react";
import { cn } from "@/utils";
import { SocialMetricData, InstagramMetrics, MetaMetrics, PinterestMetrics } from "../types";

const DeltaIndicator = ({ current, previous }: { current: number, previous?: number }) => {
    if (previous === undefined || previous === 0) return null;
    const diff = current - previous;
    if (diff === 0) return null;
    const isPositive = diff > 0;

    return (
        <span className={cn(
            "text-[10px] ml-1.5 font-bold",
            isPositive ? "text-green-600" : "text-red-500"
        )}>
            {isPositive ? '+' : ''}{diff.toLocaleString()}
        </span>
    );
};

const Cell = ({ v, p, c = "" }: { v: number, p?: number, c?: string }) => (
    <td className={cn("py-4 px-4 text-center font-bold", c)}>
        {v.toLocaleString()}
        <DeltaIndicator current={v} previous={p} />
    </td>
);

export const SocialMetricRow: React.FC<SocialMetricData> = (props) => {
    const { platform, accountName, prevData } = props;
    const p = props as any, prev = prevData as any;

    if (platform === 'pinterest') return (
        <tr className="border-b border-slate-100 bg-white hover:bg-slate-50 transition-colors">
            <td className="py-4 px-6 font-semibold text-slate-900 min-w-[200px] text-xs uppercase tracking-wider flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-600"></span>{accountName}</td>
            <Cell v={p.viewsOrganic || 0} p={prev?.viewsOrganic} c="text-slate-900 text-lg font-black" />
            <Cell v={p.interactions || 0} p={prev?.interactions} c="text-slate-700" />
            <Cell v={p.outboundClicks ?? p.audience ?? 0} p={prev?.outboundClicks ?? prev?.audience} c="text-indigo-600" />
            <Cell v={p.saves || 0} p={prev?.saves} c="text-red-500" />
        </tr>
    );

    return (
        <tr className="border-b border-slate-100 bg-white hover:bg-slate-50 transition-colors">
            <td className="py-4 px-6 font-semibold text-slate-900 min-w-[200px] text-xs uppercase tracking-wider flex items-center gap-2">
                <span className={cn("w-2 h-2 rounded-full", platform === 'instagram' ? "bg-pink-500" : "bg-blue-600")}></span>{accountName}
            </td>
            <Cell v={p.followersTotal} p={prev?.followersTotal} c="text-slate-900 text-lg border-r border-slate-100" />
            <td className="py-4 px-4 text-center">
                <div className="flex items-center justify-center">
                    <span className="text-xs text-green-600 font-bold bg-green-50 px-2 py-0.5 rounded-full">+{p.followersNew.toLocaleString()}</span>
                    <DeltaIndicator current={p.followersNew} previous={prev?.followersNew} />
                </div>
            </td>
            <td className="py-4 px-4 text-center bg-slate-50/30">
                <div className="flex flex-col items-center">
                    <div className="flex items-center"><span className="font-bold text-slate-700">{p.viewsOrganic.toLocaleString()}</span><DeltaIndicator current={p.viewsOrganic} previous={prev?.viewsOrganic} /></div>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Organic</span>
                </div>
            </td>
            <td className="py-4 px-4 text-center border-r border-slate-100/50 bg-slate-50/30">
                <div className="flex flex-col items-center">
                    <div className="flex items-center"><span className="font-bold text-slate-700">{p.viewsAds.toLocaleString()}</span><DeltaIndicator current={p.viewsAds} previous={prev?.viewsAds} /></div>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Ads</span>
                </div>
            </td>
            <Cell v={p.interactions} p={prev?.interactions} c="text-slate-700" />
            {platform !== 'youtube' && (
                <Cell v={p.profileVisits} p={prev?.profileVisits} c="text-slate-700" />
            )}
            <Cell v={p.accountsReached} p={prev?.accountsReached} c="text-slate-900 text-lg" />
        </tr>
    );
};
