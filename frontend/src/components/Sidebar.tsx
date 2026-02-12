"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Settings, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const Sidebar = () => {
    const pathname = usePathname();

    const navItems = [
        { name: "Dashboard", icon: LayoutDashboard, href: "/dash" },
    ];

    const bottomItems = [
        { name: "Integrations", icon: Settings, href: "/integrations" },
    ];

    return (
        <div className="flex flex-col h-screen w-16 md:w-20 bg-white border-r border-slate-200">
            <div className="flex items-center justify-center h-20 border-b border-slate-100 mb-2">
                <Link href="/" className="transition-transform duration-300 hover:scale-110 active:scale-95">
                    <img
                        src="/cube_logo.png"
                        alt="CUBE"
                        className="w-12 h-12 object-contain"
                    />
                </Link>
            </div>

            <nav className="flex-1 px-2 py-4 space-y-2 flex flex-col items-center">
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "p-3 rounded-xl transition-all duration-200 group flex justify-center items-center w-full",
                            pathname === item.href
                                ? "bg-indigo-50 text-indigo-600 shadow-sm"
                                : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                        )}
                        title={item.name}
                    >
                        <item.icon size={24} />
                    </Link>
                ))}
            </nav>

            <div className="px-2 py-6 border-t border-slate-100 flex flex-col items-center">
                {bottomItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "p-3 rounded-xl transition-all duration-200 group flex justify-center items-center w-full",
                            pathname === item.href
                                ? "bg-indigo-50 text-indigo-600 shadow-sm"
                                : "text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                        )}
                        title={item.name}
                    >
                        <item.icon size={24} />
                    </Link>
                ))}
            </div>
        </div>
    );
};

export default Sidebar;
