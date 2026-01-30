"use client";

import React, { useState } from "react";
import { 
  Bot, 
  Calendar, 
  DollarSign, 
  Package, 
  Activity
} from "lucide-react";
import SmartAssistant from "@/components/chat/SmartAssistant";

const AGENTS = [
  { 
    id: "appointment", 
    name: "Appointment Agent", 
    icon: Calendar, 
    color: "bg-blue-100 text-blue-600", 
    description: "Manage schedule, book, and cancel."
  },
  { 
    id: "revenue", 
    name: "Revenue Agent", 
    icon: DollarSign, 
    color: "bg-green-100 text-green-600", 
    description: "Track earnings and invoices."
  },
  { 
    id: "inventory", 
    name: "Inventory Agent", 
    icon: Package, 
    color: "bg-orange-100 text-orange-600", 
    description: "Monitor stock and supplies."
  },
  { 
    id: "casetracking", 
    name: "Case Tracking", 
    icon: Activity, 
    color: "bg-purple-100 text-purple-600", 
    description: "Patient history and records."
  },
];

export default function AgentsPage() {
  const [activeAgent, setActiveAgent] = useState(AGENTS[0]);

  return (
    <div className="flex h-[calc(100vh-120px)] gap-6 p-4 max-w-7xl mx-auto font-sans">
      
      {/* SIDEBAR */}
      <div className="w-1/4 min-w-[260px] flex flex-col gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Bot className="h-7 w-7 text-indigo-600" /> AI Agents
          </h2>
          <p className="text-slate-500 text-sm">Select a specialized assistant</p>
        </div>
        
        <div className="space-y-3 overflow-y-auto pr-2">
          {AGENTS.map((agent) => (
            <button
              key={agent.id}
              onClick={() => setActiveAgent(agent)}
              className={`w-full text-left p-3 rounded-xl transition-all border flex items-center gap-3 group relative overflow-hidden
                ${activeAgent.id === agent.id 
                  ? "bg-white border-indigo-600 shadow-md ring-1 ring-indigo-600" 
                  : "bg-white/60 border-slate-200 hover:bg-white hover:shadow-sm"
                }`}
            >
              <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${agent.color}`}>
                <agent.icon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <p className="font-bold text-sm text-slate-800 group-hover:text-indigo-700 transition-colors">
                  {agent.name}
                </p>
                <p className="text-[11px] text-slate-500 line-clamp-1">
                  {agent.description}
                </p>
              </div>
              {activeAgent.id === agent.id && (
                <div className="absolute right-0 top-0 bottom-0 w-1 bg-indigo-600" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* MAIN CHAT AREA */}
      <div className="flex-1 flex flex-col h-full">
        <SmartAssistant 
          key={activeAgent.id} 
          agentType={activeAgent.id} 
          placeholder={`Ask ${activeAgent.name}...`}
        />
      </div>
    </div>
  );
}
