"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Loader2, ShieldCheck, Mail, Lock, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

const API_URL = (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? "http://127.0.0.1:8000"
    : "/api";

export default function AuthPage() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        const endpoint = isLogin ? "/login" : "/register";

        try {
            const res = await fetch(`${API_URL}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: email, password }),
            });

            const data = await res.json();

            if (res.ok) {
                if (isLogin) {
                    login(data.access_token, email);
                } else {
                    alert("Account created! Please login.");
                    setIsLogin(true);
                }
            } else {
                setError(data.detail || "Authentication failed");
            }
        } catch (err) {
            setError("Could not connect to authentication service");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-100 via-slate-50 to-slate-50">
            <div className="w-full max-w-md">
                <div className="bg-white rounded-[2.5rem] shadow-2xl shadow-indigo-100 border border-slate-200 overflow-hidden">
                    <div className="p-10 pt-12">
                        {/* Header */}
                        <div className="flex flex-col items-center text-center mb-10">
                            <div className="w-16 h-16 bg-slate-900 rounded-3xl flex items-center justify-center mb-6 shadow-xl shadow-slate-200 rotate-3">
                                <ShieldCheck className="text-white" size={32} />
                            </div>
                            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
                                {isLogin ? "Welcome Back" : "Create Account"}
                            </h1>
                            <p className="text-slate-500 font-medium px-4">
                                {isLogin
                                    ? "Access your unified social media reporting dashboard"
                                    : "Join Social Insights to track all your KPIs in one place"}
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-5">Email Address</label>
                                <div className="relative group">
                                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-300 group-focus-within:text-indigo-500 transition-colors">
                                        <Mail size={18} />
                                    </div>
                                    <input
                                        type="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-12 pr-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500/30 transition-all font-medium text-slate-900 placeholder:text-slate-300"
                                        placeholder="you@cubehq.ai"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-5">Password</label>
                                <div className="relative group">
                                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-300 group-focus-within:text-indigo-500 transition-colors">
                                        <Lock size={18} />
                                    </div>
                                    <input
                                        type="password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full pl-12 pr-6 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500/30 transition-all font-medium text-slate-900 placeholder:text-slate-300"
                                        placeholder="••••••••"
                                    />
                                </div>
                            </div>

                            {error && (
                                <div className="bg-red-50 border border-red-100 text-red-600 px-5 py-3 rounded-2xl text-xs font-bold flex items-center gap-3 animate-shake">
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse"></div>
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full bg-slate-900 text-white py-4 px-6 rounded-2xl font-black text-sm flex items-center justify-center gap-3 hover:bg-slate-800 transition-all duration-300 shadow-xl shadow-slate-200 active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed group mt-6"
                            >
                                {isLoading ? (
                                    <Loader2 className="animate-spin" size={18} />
                                ) : (
                                    <>
                                        {isLogin ? "Sign In" : "Start Tracking"}
                                        <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </button>
                        </form>

                        {/* Toggle */}
                        <div className="mt-10 text-center">
                            <button
                                onClick={() => setIsLogin(!isLogin)}
                                className="text-xs font-bold text-slate-400 hover:text-indigo-600 transition-colors"
                            >
                                {isLogin ? (
                                    <>Create an Account<span className="text-slate-900 underline underline-offset-4 decoration-indigo-500/30">Sign Up</span></>
                                ) : (
                                    <>Already have an account? <span className="text-slate-900 underline underline-offset-4 decoration-indigo-500/30">Sign In</span></>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                <p className="text-center mt-10 text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">
                    Unified Social Insights • Secure v1.0
                </p>
            </div>
        </div>
    );
}
