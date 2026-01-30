import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, Loader2, Bot, User, X, Calendar as CalendarIcon, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  options?: string[];
}

interface SmartAssistantProps {
  agentType: string;
  placeholder?: string;
  onClose?: () => void;
}

// DEFINING UNIQUE MENUS FOR EACH AGENT
const AGENT_MENUS: Record<string, string[]> = {
  appointment: [
    "Show Today's Schedule", 
    "Book Appointment", 
    "Reschedule Appointment", 
    "Cancel Appointment"
  ],
  revenue: [
    "Create New Invoice", 
    "Show Unpaid Bills", 
    "Daily Report", 
    "Weekly Report"
  ],
  inventory: [
    "Check Low Stock", 
    "Add New Item", 
    "Usage Report"
  ],
  casetracking: [
    "Search Patient Record", 
    "Add Clinical Note", 
    "View Prescriptions"
  ]
};

export default function SmartAssistant({ agentType, placeholder, onClose }: SmartAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollEndRef = useRef<HTMLDivElement>(null);

  // 1. INITIALIZE WITH CORRECT MENU
  useEffect(() => {
    const saved = localStorage.getItem(`chat_history_${agentType}`);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        initChat();
      }
    } else {
      initChat();
    }
  }, [agentType]);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`chat_history_${agentType}`, JSON.stringify(messages));
    }
  }, [messages, agentType]);

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const initChat = () => {
    // Select the correct menu based on agentType (fallback to Appointment if unknown)
    const startOptions = AGENT_MENUS[agentType] || AGENT_MENUS["appointment"];
    
    setMessages([{
      id: "1",
      role: "assistant",
      content: `Hello! I am your ${agentType.replace("_", " ")} Assistant.`,
      timestamp: new Date().toISOString(),
      options: startOptions
    }]);
  };

  const clearHistory = () => {
    localStorage.removeItem(`chat_history_${agentType}`);
    initChat();
  };

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text.startsWith("CALENDAR_DATE:") ? `Selected Date: ${text.split(":")[1].split("|")[0]}` : text,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await api.post("/agent/router", {
        user_query: text,
        role: agentType,
        history: []
      });

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.data.response,
        timestamp: new Date().toISOString(),
        options: res.data.options || []
      };
      setMessages(prev => [...prev, aiMsg]);

    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: "Error communicating with agent.",
        timestamp: new Date().toISOString(),
        options: ["Main Menu"]
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const isCalendarOption = (opt: string) => opt.startsWith("__UI_CALENDAR__");

  return (
    <div className="flex flex-col h-[600px] w-full max-w-md bg-white rounded-xl shadow-2xl border border-indigo-100 overflow-hidden font-sans">
      <div className="p-4 bg-indigo-600 flex justify-between items-center text-white shadow-md z-10">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-white" />
          <span className="font-bold text-sm capitalize">{agentType.replace("_", " ")} Agent</span>
        </div>
        <div className="flex gap-2">
            <button onClick={clearHistory} className="p-1 hover:bg-white/20 rounded-full transition-colors" title="Clear History">
                <Trash2 className="w-4 h-4" />
            </button>
            {onClose && <button onClick={onClose}><X className="w-5 h-5" /></button>}
        </div>
      </div>

      <ScrollArea className="flex-1 p-4 bg-slate-50/50">
        <div className="space-y-6 pb-2">
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full animate-in fade-in slide-in-from-bottom-2 duration-300", msg.role === "user" ? "justify-end" : "justify-start")}>
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center mr-2 border border-indigo-200 shrink-0"><Bot className="w-4 h-4 text-indigo-600" /></div>
              )}
              <div className={cn("flex flex-col max-w-[90%] gap-2", msg.role === "user" ? "items-end" : "items-start")}>
                <div className={cn("p-3.5 rounded-2xl text-sm shadow-sm leading-relaxed", msg.role === "user" ? "bg-indigo-600 text-white rounded-br-none" : "bg-white text-slate-700 border border-slate-100 rounded-bl-none")}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
                {msg.role === "assistant" && msg.options && msg.options.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1">
                    {msg.options.map((opt, idx) => {
                      if (isCalendarOption(opt)) {
                        const context = opt.split("|")[1];
                        return (
                          <div key={idx} className="w-full bg-white p-3 rounded-xl border border-indigo-100 shadow-sm">
                            <div className="flex items-center gap-2 mb-2 text-indigo-700 text-xs font-bold"><CalendarIcon className="w-4 h-4" /> Select Date</div>
                            <input 
                              type="date" 
                              className="w-full p-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                              min={new Date().toISOString().split("T")[0]}
                              onChange={(e) => { if(e.target.value) handleSend(`CALENDAR_DATE: ${e.target.value} | ${context}`); }}
                            />
                          </div>
                        );
                      }
                      return (
                        <button key={idx} onClick={() => handleSend(opt)} className="px-3 py-2 text-xs font-semibold bg-white text-indigo-700 rounded-lg border border-indigo-200 hover:bg-indigo-600 hover:text-white transition-all shadow-sm active:scale-95 text-left">
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                )}
                <span className="text-[10px] text-slate-400 px-1">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            </div>
          ))}
          {isLoading && <div className="flex justify-start items-center gap-2 pl-10"><Loader2 className="w-4 h-4 animate-spin text-indigo-600" /><span className="text-xs text-slate-500">Processing...</span></div>}
          <div ref={scrollEndRef} />
        </div>
      </ScrollArea>

      <div className="p-4 bg-white border-t border-slate-100">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(input); }} className="flex gap-2">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder={placeholder || "Type here..."} className="flex-1 bg-slate-50 border-slate-200 focus-visible:ring-indigo-500 rounded-xl" disabled={isLoading} />
          <Button type="submit" size="icon" className="rounded-xl bg-indigo-600 hover:bg-indigo-700" disabled={!input.trim() || isLoading}><Send className="w-4 h-4" /></Button>
        </form>
      </div>
    </div>
  );
}
