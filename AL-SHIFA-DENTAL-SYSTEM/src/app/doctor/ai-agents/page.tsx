"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Bot, 
  Calendar, 
  DollarSign, 
  Package, 
  Activity, 
  Send, 
  Sparkles, 
  Trash2, 
  User, 
  ChevronRight 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Avatar } from "@/components/ui/avatar";

// --- AGENT CONFIGURATION & PERSONAS ---
const AGENTS = [
  { 
    id: "appointment", 
    name: "Appointment Agent", 
    icon: Calendar, 
    color: "bg-blue-100 text-blue-600", 
    border: "border-blue-200",
    welcome: "Hello, Doctor. I can view your schedule, book new patients, or manage cancellations. What do you need?",
    suggestions: ["Show today's schedule", "Find slots for tomorrow", "Book a new appointment", "Cancel an appointment"]
  },
  { 
    id: "revenue", 
    name: "Revenue Agent", 
    icon: DollarSign, 
    color: "bg-green-100 text-green-600", 
    border: "border-green-200",
    welcome: "Financial systems online. I can analyze revenue, track unpaid invoices, and summarize earnings for you.",
    suggestions: ["Show total revenue", "List pending invoices", "Show recent payments", "Mark an invoice as Paid"]
  },
  { 
    id: "inventory", 
    name: "Inventory Agent", 
    icon: Package, 
    color: "bg-orange-100 text-orange-600", 
    border: "border-orange-200",
    welcome: "Inventory loaded. I am tracking stock levels. I can alert you on low stock or update item quantities.",
    suggestions: ["Check stock levels", "List low stock items", "Update item quantity", "Check details for a specific item"]
  },
  { 
    id: "casetracking", 
    name: "Case Tracking", 
    icon: Activity, 
    color: "bg-purple-100 text-purple-600", 
    border: "border-purple-200",
    welcome: "Clinical records active. Provide a patient name to review their history, or add a new diagnosis/prescription.",
    suggestions: ["Find patient history", "Add a medical record", "Show recent diagnoses", "Check last visit details"]
  },
];

type Message = {
  role: "user" | "bot";
  text: string;
  time: string;
};

export default function AgentsPage() {
  const [activeAgent, setActiveAgent] = useState(AGENTS[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 1. Load History
  useEffect(() => {
    const saved = localStorage.getItem(`chat_history_${activeAgent.id}`);
    if (saved) {
      setMessages(JSON.parse(saved));
    } else {
      setMessages([{
        role: "bot",
        text: activeAgent.welcome,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  }, [activeAgent]);

  // 2. Save History
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`chat_history_${activeAgent.id}`, JSON.stringify(messages));
    }
  }, [messages, activeAgent]);

  // 3. Scroll
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const clearHistory = () => {
    if(confirm("Clear this conversation history?")) {
        localStorage.removeItem(`chat_history_${activeAgent.id}`);
        setMessages([{
            role: "bot",
            text: activeAgent.welcome,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
    }
  };

  const handleSend = async (textOverride?: string) => {
    const textToSend = textOverride || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { 
      role: "user", 
      text: textToSend, 
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    };
    
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/agent/router", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          user_query: textToSend,
          role: activeAgent.id,
          history: newHistory.map(m => ({ role: m.role, text: m.text })) 
        })
      });
      
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: "bot", 
        text: data.response || "No response from local AI.", 
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
      }]);

    } catch (error) {
      setMessages(prev => [...prev, { 
        role: "bot", 
        text: "Error: AI Service Offline.", 
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-120px)] gap-6 p-4 max-w-7xl mx-auto">
      
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
                  {activeAgent.id === agent.id ? "Active" : "Switch"}
                </p>
              </div>
              {activeAgent.id === agent.id && <div className="absolute right-0 top-0 bottom-0 w-1 bg-indigo-600" />}
            </button>
          ))}
        </div>
      </div>

      {/* CHAT AREA */}
      <Card className="flex-1 flex flex-col overflow-hidden bg-white shadow-xl border-slate-200 rounded-2xl">
        <div className="p-4 border-b bg-slate-50/80 backdrop-blur-md flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className={`h-11 w-11 rounded-full flex items-center justify-center ${activeAgent.color} shadow-sm`}>
              <activeAgent.icon className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg leading-tight">{activeAgent.name}</h3>
              <p className="text-xs text-slate-500 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                Phi-3 Memory Active
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={clearHistory} className="text-slate-400 hover:text-red-500 hover:bg-red-50">
            <Trash2 className="h-4 w-4 mr-2" /> Clear History
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <Avatar className="h-8 w-8 mt-1 border border-slate-100 shadow-sm">
                {msg.role === 'bot' ? (
                  <div className={`h-full w-full flex items-center justify-center ${activeAgent.color}`}>
                    <activeAgent.icon className="h-4 w-4" />
                  </div>
                ) : (
                  <div className="h-full w-full bg-indigo-600 flex items-center justify-center text-white">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </Avatar>
              <div className={`flex flex-col max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm whitespace-pre-wrap
                    ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-700 rounded-tl-none'}`}>
                  {msg.text}
                </div>
                <span className="text-[10px] text-slate-400 mt-1 px-1">{msg.time}</span>
              </div>
            </div>
          ))}

          {/* SUGGESTIONS LOOP (GENERIC) */}
          {messages.length > 0 && messages[messages.length - 1].role === 'bot' && !loading && (
            <div className="ml-11 grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg animate-in fade-in slide-in-from-bottom-2 duration-500 mb-2">
              {activeAgent.suggestions.map((s, i) => (
                <button key={i} onClick={() => handleSend(s)} className="text-left text-xs px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors shadow-sm flex items-center justify-between group">
                  {s} <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          )}

          {loading && (
             <div className="flex gap-3 ml-1">
               <div className={`h-8 w-8 rounded-full flex items-center justify-center ${activeAgent.color} opacity-50`}>
                 <activeAgent.icon className="h-4 w-4" />
               </div>
               <div className="bg-white border border-slate-200 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1">
                 <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                 <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                 <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
               </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        <div className="p-4 bg-white border-t border-slate-100 relative flex items-center gap-2">
           <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} placeholder={`Ask ${activeAgent.name}...`} className="pl-4 pr-12 py-6 rounded-xl border-slate-200 focus-visible:ring-indigo-600 shadow-sm text-base" disabled={loading} />
           <Button onClick={() => handleSend()} disabled={loading || !input.trim()} className="absolute right-6 h-10 w-10 p-0 rounded-lg bg-indigo-600 hover:bg-indigo-700 transition-all shadow-md">
             {loading ? <Sparkles className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
           </Button>
        </div>
      </Card>
    </div>
  );
}
