"use client";

import React from 'react';
import Image from 'next/image';
import { LoginForm } from '@/features/auth/components/LoginForm';

export default function LoginPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
            <div className="w-full max-w-md">
                {/* Logo / Brand */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-24 h-24 mb-2">
                        <Image src="/cube_logo.png" alt="Cube Logo" width={96} height={96} className="object-contain" />
                    </div>
                    <h1 className="text-3xl font-bold text-slate-900">Social Insights</h1>
                    <p className="text-slate-500 mt-2">Unified Performance Dashboard</p>
                </div>

                {/* Form Card */}
                <LoginForm />
            </div>
        </div>
    );
}
