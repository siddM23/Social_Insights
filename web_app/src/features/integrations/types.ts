import { ReactNode } from "react";

export interface Account {
    email?: string;
    status: string;
    account_id: string;
    account_name: string;
    platform?: string;
    additional_info?: {
        status?: string;
    };
    last_error?: string;
}

export interface PlatformCardProps {
    title: string;
    description: string;
    icon: ReactNode;
    accounts: Account[];
    accentColor: string;
    onConnect: () => void;
    onDelete: (accountId: string) => void;
}
