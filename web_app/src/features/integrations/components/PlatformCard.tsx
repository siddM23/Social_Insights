import React from "react";
import { X, CheckCircle2, AlertCircle, Plus } from "lucide-react";
import { cn } from "@/utils";
import { PlatformCardProps } from "../types";

export const PlatformCard: React.FC<PlatformCardProps> = ({
    title,
    description,
    icon,
    accounts,
    accentColor,
    onConnect,
    onDelete
}) => {
    return (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden flex flex-col min-h-[450px] transition-all duration-300 hover:shadow-indigo-100/50 hover:-translate-y-1">
            <div className="p-8 border-b border-slate-100 flex items-start gap-5">
                <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg", accentColor)}>
                    {icon}
                </div>
                <div>
                    <h3 className="text-xl font-bold text-slate-900 mb-1">{title}</h3>
                    <p className="text-sm text-slate-500 leading-relaxed font-medium">{description}</p>
                </div>
            </div>

            <div className="p-8 flex-1 bg-slate-50/10">
                <div className="flex items-center justify-between mb-6">
                    <h4 className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">Connected Accounts</h4>
                    <span className="text-[10px] font-bold bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full uppercase tracking-wider">{accounts.length} Total</span>
                </div>
                <div className="space-y-4 max-h-[200px] overflow-y-auto pr-2 no-scrollbar">
                    {accounts.length > 0 ? (
                        accounts.map((acc, i) => (
                            <div key={acc.account_id || i} className="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-2xl hover:border-slate-300 transition-all shadow-sm shadow-slate-100 hover:shadow-md">
                                <div className="flex flex-col gap-0.5">
                                    <span className="text-[14px] font-bold text-slate-900">{acc.account_name}</span>
                                    {acc.email && <span className="text-[11px] text-slate-500 font-medium">{acc.email}</span>}
                                    <div className="flex items-center gap-1.5 px-2 py-0.5 w-fit rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-bold uppercase tracking-wider mt-1">
                                        <CheckCircle2 size={10} />
                                        {acc.status || "Active"}
                                    </div>
                                </div>
                                <button
                                    onClick={() => onDelete(acc.account_id)}
                                    className="text-slate-300 hover:text-red-500 hover:bg-red-50 p-2 rounded-xl transition-all"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        ))
                    ) : (
                        <div className="border-2 border-dashed border-slate-100 rounded-3xl h-40 flex flex-col items-center justify-center text-slate-300 gap-3 bg-slate-50/30">
                            <AlertCircle size={32} className="opacity-20" />
                            <span className="text-xs font-bold uppercase tracking-widest opacity-60">No accounts connected</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="p-8 pt-0">
                <button
                    onClick={onConnect}
                    className="w-full py-4 bg-slate-900 text-white rounded-2xl text-sm font-bold hover:bg-slate-800 transition-all duration-300 flex items-center justify-center gap-3 shadow-lg shadow-slate-200 group active:scale-[0.98]"
                >
                    <Plus size={20} className="text-white/70 group-hover:text-white transition-colors" />
                    Connect {title.split(' ')[0]} Account
                </button>
            </div>
        </div>
    );
};
