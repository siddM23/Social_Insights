import React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPage() {
    return (
        <div className="max-w-4xl mx-auto p-8 md:p-12 bg-white min-h-screen">
            <Link href="/integrations" className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 mb-8 transition-colors">
                <ArrowLeft size={20} />
                <span>Back to Integrations</span>
            </Link>

            <h1 className="text-4xl font-bold text-slate-900 mb-8">Privacy Policy</h1>

            <div className="prose prose-slate max-w-none space-y-6 text-slate-600">
                <p className="text-sm italic">Last Updated: February 27, 2026</p>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">1. Introduction</h2>
                    <p>
                        Welcome to **Social Insights**. We value your privacy and are committed to protecting your personal data.
                        This privacy policy explains how we collect, use, and safeguard your information when you use our application
                        to manage and aggregate your social media metrics.
                    </p>
                </section>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">2. Data We Collect</h2>
                    <p>
                        Social Insights provides a centralized dashboard for your social media performance. To do this, we collect:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                        <li>**Authentication Data**: OAuth tokens (Access and Refresh tokens) provided by platforms like Google (YouTube), Meta (Instagram/Facebook), and Pinterest.</li>
                        <li>**Public Metrics**: Views, likes, comments, subscriber counts, and other performance data from your authorized social media accounts.</li>
                        <li>**Account Information**: Basic profile information (e.g., channel name, profile picture) to identify your accounts within our dashboard.</li>
                    </ul>
                </section>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">3. How We Use Data</h2>
                    <p>
                        We use the collected data exclusively to:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                        <li>Display aggregated performance reports and analytics to you.</li>
                        <li>Synchronize data in the background to keep your dashboard up to date.</li>
                        <li>Improve the functionality and user experience of our application.</li>
                    </ul>
                    <p className="font-medium text-slate-800">
                        We do not sell your data to third parties. We do not use your data for advertising purposes.
                    </p>
                </section>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">4. Data Retention and Security</h2>
                    <p>
                        Your metrics are cached in our secure database to provide historical reporting. We implement industry-standard
                        security measures to protect your tokens and data. You can disconnect any integration at any time from the
                        Integrations page, which will immediately stop data collection for that account.
                    </p>
                </section>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">5. Google API Services Usage</h2>
                    <p>
                        Social Insights' use and transfer to any other app of information received from Google APIs will adhere to
                        [Google API Service User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
                        including the Limited Use requirements.
                    </p>
                </section>

                <section>
                    <h2 className="text-2xl font-semibold text-slate-800 mb-4">6. Contact Us</h2>
                    <p>
                        If you have any questions about this Privacy Policy, please contact us at siddharth@cubehq.ai.
                    </p>
                </section>
            </div>
        </div>
    );
}
