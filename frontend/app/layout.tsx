import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/sidebar";
import { StatusPanel } from "@/components/status-panel";
import { TopHeader } from "@/components/top-header";
import { WorkflowContextPanel } from "@/components/workflow-context-panel";
import { getStatusOrFallback } from "@/lib/api";

import "./globals.css";

export const metadata: Metadata = {
  title: "AutoMap",
  description: "AutoMap: County GIS Request Engine",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const status = await getStatusOrFallback();

  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <Sidebar />
          <div className="main-shell">
            <TopHeader status={status} />
            <div className="content-grid">
              <main className="content-main">{children}</main>
              <div className="right-rail">
                <StatusPanel status={status} />
                <WorkflowContextPanel />
              </div>
            </div>
            <footer className="footer">AutoMap v{status.version || "2.0.0"} - local draft workflow only.</footer>
          </div>
        </div>
      </body>
    </html>
  );
}
