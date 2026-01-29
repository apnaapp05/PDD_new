// src/components/chat/SmartAssistant.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  // NEW: Dynamic Options support
  options?: string[]; 
}

interface SmartAssistantProps {
  agentType: string;
  placeholder?: string;
  onClose?: () => void;
}

export default function SmartAssistant({ agentType, placeholder, onClose }: SmartAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello! I am your ${agentType.replace('_', ' ')} assistant. How can I help you today?`,
      timestamp: new Date(),
      options: ['Show Schedule', 'Find Slots', 'Book Appointment'] // Default start options
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    // Add User Message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Send History + Query
      const history = messages.map(m => ({ role: m.role, text: m.content }));
      
      const res = await api.post('/agent/router', {
        user_query: text,
        role: agentType,
        history: history.slice(-5) // Keep context light
      });

      // Add AI Response with Dynamic Options
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: res.data.response,
        timestamp: new Date(),
        options: res.data.options || [] // Catch backend options
      };
      setMessages(prev => [...prev, aiMsg]);

    } catch (error) {
      console.error('Agent Error:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: "Sorry, I encountered a connection error. Please try again.",
        timestamp: new Date(),
        options: ['Retry', 'Main Menu']
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-md bg-white rounded-xl shadow-2xl border border-indigo-100 overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-indigo-600 flex justify-between items-center text-white">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5" />
          <span className="font-semibold capitalize">{agentType.replace('_', ' ')} Agent</span>
        </div>
        {onClose && <Button variant="ghost" size="sm" onClick={onClose} className="text-white hover:bg-indigo-700">✕</Button>}
      </div>

      {/* Chat Area */}
      <ScrollArea className="flex-1 p-4 bg-slate-50" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
              <div className={cn("flex flex-col max-w-[85%] gap-2", msg.role === 'user' ? "items-end" : "items-start")}>
                
                {/* Message Bubble */}
                <div className={cn(
                  "p-3 rounded-2xl text-sm shadow-sm",
                  msg.role === 'user' 
                    ? "bg-indigo-600 text-white rounded-br-none" 
                    : "bg-white text-slate-800 border border-indigo-50 rounded-bl-none"
                )}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {/* DYNAMIC OPTIONS CHIPS (Only for Assistant) */}
                {msg.role === 'assistant' && msg.options && msg.options.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1">
                    {msg.options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(opt)}
                        className="px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full border border-indigo-200 hover:bg-indigo-100 transition-colors"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                <span className="text-[10px] text-slate-400 px-1">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white p-3 rounded-2xl rounded-bl-none border border-indigo-50 shadow-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                <span className="text-xs text-slate-500">Thinking...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-100">
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSend(input); }}
          className="flex gap-2"
        >
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder || "Type a message..."}
            className="flex-1 focus-visible:ring-indigo-500"
          />
          <Button type="submit" size="icon" className="bg-indigo-600 hover:bg-indigo-700">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
