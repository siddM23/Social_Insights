import { useQuery } from "@tanstack/react-query";
import { API_URL } from "@/services/api";
import { TimeRange } from "../types";

export const useDashboardMetrics = (token: string | null, timeRange: TimeRange, customRange: { start: string; end: string } | null) => {
    return useQuery({
        queryKey: ["metrics", timeRange, customRange],
        queryFn: async () => {
            if (!token) return [];

            if (timeRange === 'custom' && customRange) {
                const res = await fetch(`${API_URL}/metrics/custom_range`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        start_date: customRange.start,
                        end_date: customRange.end
                    })
                });
                if (!res.ok) throw new Error("Failed to fetch custom metrics");
                return res.json();
            }

            const integrationsRes = await fetch(`${API_URL}/integrations`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!integrationsRes.ok) return [];
            const integrations = await integrationsRes.json();

            const promises = integrations.map(async (acc: any) => {
                const account_id = acc.account_id;
                let fullData = { period_7d: {}, period_30d: {}, followers_total: 0 };
                try {
                    const mRes = await fetch(`${API_URL}/metrics/${acc.platform}/${account_id}`, {
                        headers: { "Authorization": `Bearer ${token}` }
                    });
                    if (mRes.ok) {
                        const mData = await mRes.json();
                        if (Array.isArray(mData) && mData.length > 0) fullData = mData[0];
                    }
                } catch (err) { console.warn(`Failed for ${account_id}`, err); }

                return {
                    accountName: acc.account_name || acc.account_id,
                    platform: acc.platform,
                    data: fullData
                };
            });

            return Promise.all(promises);
        },
        enabled: !!token,
        staleTime: 1000 * 60 * 5,
    });
};
