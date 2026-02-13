"use client";

import React from "react";
import Sidebar from "@/components/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth();
    const pathname = usePathname();
    const isAuthPage = pathname.startsWith("/auth");

    if (isLoading) {
        return (
            <div className="flex h-screen w-screen items-center justify-center bg-slate-50">
                <Loader2 className="animate-spin text-slate-300" size={48} />
            </div>
        );
    }

    if (isAuthPage) {
        return <>{children}</>;
    }

    return (
        <div className="flex h-screen overflow-hidden bg-slate-50 w-full">
            <Sidebar />
            <main className="flex-1 overflow-y-auto w-full">
                {children}
            </main>
        </div>
    );
}
