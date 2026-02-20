import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/services/api";
import { Account } from "../types";

export const useIntegrations = (token: string | null) => {
    const queryClient = useQueryClient();

    const fetchIntegrations = async (): Promise<Account[]> => {
        const res = await fetch(`${API_URL}/integrations`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to fetch integrations");
        return res.json();
    };

    const query = useQuery({
        queryKey: ["integrations"],
        queryFn: fetchIntegrations,
        enabled: !!token,
    });

    const deleteMutation = useMutation({
        mutationFn: async ({ platform, accountId }: { platform: string, accountId: string }) => {
            const res = await fetch(`${API_URL}/integrations/${platform}/${accountId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to delete integration");
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["integrations"] });
        }
    });

    const getConnectUrl = async (platform: string) => {
        const res = await fetch(`${API_URL}/auth/${platform}/login`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to get connect URL");
        const data = await res.json();
        return data.url;
    };

    return {
        ...query,
        deleteIntegration: deleteMutation.mutateAsync,
        getConnectUrl,
    };
};
