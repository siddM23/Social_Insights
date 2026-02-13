"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
    token: string | null;
    user: string | null;
    login: (token: string, user: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [user, setUser] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        const storedToken = localStorage.getItem("auth_token");
        const storedUser = localStorage.getItem("auth_user");
        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(storedUser);
        }
        setIsLoading(false);
    }, []);

    useEffect(() => {
        if (!isLoading) {
            const publicRoutes = ["/auth/login", "/auth/register"];
            if (!token && !publicRoutes.includes(pathname)) {
                router.push("/auth/login");
            }
        }
    }, [token, isLoading, pathname, router]);

    const login = (newToken: string, newUser: string) => {
        localStorage.setItem("auth_token", newToken);
        localStorage.setItem("auth_user", newUser);
        setToken(newToken);
        setUser(newUser);
        router.push("/dash");
    };

    const logout = () => {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        setToken(null);
        setUser(null);
        router.push("/auth/login");
    };

    return (
        <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
