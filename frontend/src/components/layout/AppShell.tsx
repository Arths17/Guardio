"use client";

import { useEffect, useState } from "react";
import { connectWebSocket, disconnectWebSocket } from "@/lib/websocket";
import Sidebar, { type ViewId } from "./Sidebar";
import TopBar from "./TopBar";
import dynamic from "next/dynamic";

const ThreatMap = dynamic(() => import("@/components/map/ThreatMap"), { ssr: false });
const InfraGraph = dynamic(() => import("@/components/graph/InfraGraph"), { ssr: false });
const IncidentTimeline = dynamic(() => import("@/components/timeline/IncidentTimeline"), { ssr: false });
const ThreatIntelPanel = dynamic(() => import("@/components/intelligence/ThreatIntelPanel"), { ssr: false });
const AICopilot = dynamic(() => import("@/components/ai/AICopilot"), { ssr: false });

export default function AppShell() {
  const [view, setView] = useState<ViewId>("map");

  useEffect(() => {
    connectWebSocket();
    return () => disconnectWebSocket();
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-bg-base">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={view} onChange={setView} />
        <main className="flex-1 overflow-hidden relative">
          {view === "map" && <ThreatMap />}
          {view === "graph" && <InfraGraph />}
          {view === "timeline" && <IncidentTimeline />}
          {view === "intel" && <ThreatIntelPanel />}
          {view === "ai" && <AICopilot />}
        </main>
      </div>
    </div>
  );
}
