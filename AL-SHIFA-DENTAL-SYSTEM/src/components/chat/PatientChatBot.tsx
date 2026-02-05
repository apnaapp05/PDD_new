'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgentAPI } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { getChatStorageKey } from '@/lib/chatStorage';

interface Message {
  role: 'user' | 'bot';
  content: string;
  actions?: string[];
  redirect?: string;
}

export default function PatientChatBot({ isFullPage = false }: { isFullPage?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: 'Salam! I am your Al-Shifa Assistant. How can I help you today?' }
  ]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load history from localStorage on mount (user-specific)
  useEffect(() => {
    const chatKey = getChatStorageKey('chat_history_patient');
    const saved = localStorage.getItem(chatKey);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) { console.error("Failed to load chat history"); }
    }
  }, []);

  // Save to localStorage whenever messages change (user-specific)
  // Auto-scroll to the bottom when messages change
  useEffect(() => {
    if (messages.length > 1) { // Don't save if only initial message
      const chatKey = getChatStorageKey('chat_history_patient');
      localStorage.setItem(chatKey, JSON.stringify(messages));
    }
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!query.trim()) return;
    const userMsg = query;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setQuery('');
    setLoading(true);

    try {
      const res = await AgentAPI.patientChat(userMsg);
      const botRes = res.data;

      setMessages(prev => [...prev, {
        role: 'bot',
        content: botRes.response || botRes.text,
        actions: botRes.actions,
        redirect: botRes.redirect
      }]);

      if (botRes.redirect) {
        setTimeout(() => router.push(botRes.redirect), 2500);
      }

    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', content: '⚠️ Connection error. Please ensure the backend is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  const containerClasses = isFullPage ? "flex flex-col h-full w-full" : "flex flex-col h-[500px] w-full";

  return (
    <div className={containerClasses}>
      {/* Messages Window */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>

              {/* Avatar Icon */}
              <div className={`h-9 w-9 rounded-full flex items-center justify-center shrink-0 shadow-sm ${m.role === 'user' ? 'bg-blue-600' : 'bg-teal-600'
                }`}>
                {m.role === 'user' ? <User className="h-5 w-5 text-white" /> : <Bot className="h-5 w-5 text-white" />}
              </div>

              {/* Chat Bubble */}
              <div className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${m.role === 'user'
                ? 'bg-blue-600 text-white rounded-tr-none'
                : 'bg-white border border-slate-200 text-slate-700 rounded-tl-none'
                }`}>
                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* AI Action Chips */}
                {m.actions && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {m.actions.map(a => (
                      <button
                        key={a}
                        onClick={() => { setQuery(a); }}
                        className="text-[11px] font-bold bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full border border-blue-100 hover:bg-blue-100 transition-colors"
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                )}

                {/* Redirecting Indicator */}
                {m.redirect && (
                  <div className="mt-3 text-[10px] font-medium text-blue-100 flex items-center gap-1.5 animate-pulse">
                    <Sparkles className="h-3 w-3" /> Taking you there...
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 px-4 py-2 rounded-full shadow-sm">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce"></span>
                <span className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
              </div>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Section */}
      <div className="p-4 bg-white border-t border-slate-200 flex flex-col gap-2">
        <div className="flex gap-3 items-center">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask me to book, cancel or analyze..."
            className="flex-1 border border-slate-200 rounded-2xl px-5 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 bg-slate-50 transition-all"
          />
          <Button
            onClick={handleSend}
            disabled={!query.trim() || loading}
            className="h-12 w-12 rounded-2xl bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all active:scale-95"
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex justify-center">
          <button
            onClick={() => {
              const chatKey = getChatStorageKey('chat_history_patient');
              localStorage.removeItem(chatKey);
              setMessages([{ role: 'bot', content: 'Salam! I am your Al-Shifa Assistant. How can I help you today?' }]);
            }}
            className="text-[10px] text-slate-400 hover:text-red-500 transition-colors"
          >
            Clear Conversation History
          </button>
        </div>
      </div>
    </div>
  );
}