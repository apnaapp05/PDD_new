import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, Loader2, Bot, User, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface SmartAssistantProps {
  agentType: string;
  placeholder?: string;
  onClose?: () => void;
}

export default function SmartAssistant({ agentType, placeholder, onClose }: SmartAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: `Hello! I am your ${agentType} Agent (Version 3.0).`,
      timestamp: new Date()
    }
  ]);

  // STRICT: ONLY 2 OPTIONS INITIALLY.
  // The old "Find slots for tomorrow" is GONE.
  const [currentOptions, setCurrentOptions] = useState<string[]>(
    agentType === "appointment" 
      ? ["Show Today's Schedule", "Cancel Appointment"] 
      : ["Main Menu"]
  );
  
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    // 1. Add User Message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    setCurrentOptions([]); // CLEAR OPTIONS WHILE LOADING

    try {
      // 2. Call Backend
      const res = await api.post("/agent/router", {
        user_query: text,
        role: agentType,
        history: [] 
      });

      // 3. Add Response
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.data.response,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMsg]);
      
      // 4. SET OPTIONS FROM BACKEND
      if (res.data.options && res.data.options.length > 0) {
        setCurrentOptions(res.data.options);
      } else {
        setCurrentOptions(["Main Menu"]);
      }

    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: "Error: Backend unreachable.",
        timestamp: new Date()
      }]);
      setCurrentOptions(["Retry"]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-md bg-white rounded-xl shadow-2xl border border-indigo-100 overflow-hidden font-sans">
      {/* HEADER */}
      <div className="p-4 bg-slate-900 flex justify-between items-center text-white shadow-md">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-green-400" />
          <div>
            <h3 className="font-bold text-sm capitalize">{agentType} Agent</h3>
            <span className="text-[10px] text-green-400 font-bold bg-green-900/50 px-2 py-0.5 rounded-full border border-green-700">VERSION 3.0</span>
          </div>
        </div>
        {onClose && <button onClick={onClose}><X className="w-5 h-5" /></button>}
      </div>

      {/* CHAT AREA */}
      <ScrollArea className="flex-1 p-4 bg-slate-50" ref={scrollRef}>
        <div className="space-y-4 pb-2">
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full", msg.role === "user" ? "justify-end" : "justify-start")}>
              <div className={cn("p-3.5 rounded-xl text-sm max-w-[85%] shadow-sm leading-relaxed", msg.role === "user" ? "bg-indigo-600 text-white rounded-br-none" : "bg-white border border-slate-200 text-slate-800 rounded-bl-none")}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isLoading && <div className="text-xs text-slate-400 ml-2 animate-pulse">Processing...</div>}
        </div>
      </ScrollArea>

      {/* ACTION BAR */}
      <div className="bg-white border-t border-slate-200 p-3">
        {currentOptions.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {currentOptions.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(opt)}
                className="px-3 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg hover:bg-indigo-600 hover:text-white transition-colors"
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); handleSend(input); }} className="flex gap-2">
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type command..."
            className="flex-1 bg-slate-50"
          />
          <Button type="submit" size="icon" className="bg-indigo-600"><Send className="w-4 h-4" /></Button>
        </form>
      </div>
    </div>
  );
}