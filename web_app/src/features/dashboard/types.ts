export interface InstagramMetrics {
    platform: 'instagram';
    followersTotal: number;
    followersNew: number;
    viewsOrganic: number;
    viewsAds: number;
    interactions: number;
    profileVisits: number;
    accountsReached: number;
}

export interface MetaMetrics {
    platform: 'meta' | 'facebook';
    followersTotal: number;
    followersNew: number;
    viewsOrganic: number;
    viewsAds: number;
    interactions: number;
    profileVisits: number;
    accountsReached: number;
}

export interface PinterestMetrics {
    platform: 'pinterest';
    viewsOrganic: number;
    interactions: number;
    followersTotal: number;
    saves: number;
}

export interface YoutubeMetrics {
    platform: 'youtube';
    followersTotal: number;
    followersNew: number;
    viewsOrganic: number;
    viewsAds: number;
    interactions: number;
    accountsReached: number;
}

export type SocialMetricData = (InstagramMetrics | MetaMetrics | PinterestMetrics | YoutubeMetrics) & {
    accountName: string,
    prevData?: Partial<InstagramMetrics | MetaMetrics | PinterestMetrics | YoutubeMetrics>
};

export interface MetricItem {
    accountName: string;
    platform: string;
    data: any;
}

export type TimeRange = '7d' | '30d' | 'custom';
