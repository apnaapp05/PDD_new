// src/components/chat/SmartAssistant.tsx
import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, Loader2, Bot, User, X, Zap } from "lucide-react";
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
      content: "Hello! I am your AI Assistant. I am ready.",
      timestamp: new Date()
    }
  ]);

  // NUCLEAR FIX: Start with EMPTY options. Do not use hardcoded defaults.
  const [currentOptions, setCurrentOptions] = useState<string[]>([]);
  
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initial greeting options (Only once)
  useEffect(() => {
    if (agentType === "appointment") {
      setCurrentOptions(["Show Today's Schedule", "Cancel Appointment", "Book Appointment"]);
    } else {
      setCurrentOptions(["Main Menu"]);
    }
  }, [agentType]);

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
    
    // CRITICAL: Clear options immediately so you dont click old ones
    setCurrentOptions([]); 

    try {
      // 2. Call Backend
      const history = messages.map(m => ({ role: m.role, text: m.content }));
      
      const res = await api.post("/agent/router", {
        user_query: text,
        role: agentType,
        history: history.slice(-5) 
      });

      // 3. Add AI Response
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.data.response || "Done.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMsg]);
      
      // 4. FORCE UPDATE OPTIONS
      // If backend sends options, use them. If not, show Main Menu.
      if (res.data.options && Array.isArray(res.data.options) && res.data.options.length > 0) {
        console.log("Setting Options:", res.data.options);
        setCurrentOptions(res.data.options);
      } else {
        setCurrentOptions(["Main Menu", "Show Schedule"]);
      }

    } catch (error) {
      console.error("Agent Error:", error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: "Server Error. Is the backend running?",
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
      <div className="p-4 bg-indigo-600 flex justify-between items-center text-white shadow-md z-10">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-white" />
          <div>
            <h3 className="font-bold text-sm capitalize">{agentType} Agent</h3>
            <div className="flex items-center gap-1">
               <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
               <p className="text-[10px] text-indigo-100">Live Connection</p>
            </div>
          </div>
        </div>
        {onClose && <button onClick={onClose}><X className="w-5 h-5" /></button>}
      </div>

      {/* CHAT AREA */}
      <ScrollArea className="flex-1 p-4 bg-slate-50" ref={scrollRef}>
        <div className="space-y-4 pb-2">
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full", msg.role === "user" ? "justify-end" : "justify-start")}>
              {msg.role === "assistant" && <Bot className="w-6 h-6 text-indigo-600 mr-2 mt-1" />}
              <div className={cn("p-3 rounded-2xl text-sm shadow-sm max-w-[80%]", msg.role === "user" ? "bg-indigo-600 text-white rounded-br-none" : "bg-white text-slate-800 rounded-bl-none")}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-slate-400 text-xs ml-8">
              <Loader2 className="w-3 h-3 animate-spin" /> Thinking...
            </div>
          )}
        </div>
      </ScrollArea>

      {/* DYNAMIC ACTION BAR (THE FIX) */}
      <div className="bg-white border-t border-slate-100 p-3">
        {currentOptions.length > 0 ? (
          <div className="flex flex-wrap gap-2 mb-3">
            {currentOptions.map((opt, idx) => (
               <button
                key={idx}
                onClick={() => handleSend(opt)}
                className="px-3 py-2 text-xs font-bold bg-indigo-50 text-indigo-700 rounded-lg border border-indigo-200 hover:bg-indigo-600 hover:text-white transition-all shadow-sm"
              >
                {opt}
              </button>
            ))}
          </div>
        ) : (
           /* Visual placeholder if no options exist */
           <div className="h-8 mb-2 flex items-center justify-center text-xs text-slate-300 italic">
             Waiting for response...
           </div>
        )}

        {/* INPUT */}
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
