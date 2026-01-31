import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function SmartAssistant() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I am your Dental AI Agent. Ask me about Revenue, Inventory, or Schedules.',
      timestamp: new Date()
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

  // --- ACTION HANDLER ---
  const performAction = (action: string | null, intent: string | null) => {
    if (!action && !intent) return;

    console.log("Agent Action:", action, "Intent:", intent);

    // 1. Handle Navigation/Redirects from Backend
    if (action && action.startsWith('redirect:')) {
      const page = action.split(':')[1];
      if (page === 'appointment_new') router.push('/doctor/schedule'); // Redirect to schedule
      if (page === 'patient_new') router.push('/doctor/patients');
    }

    // 2. Handle Modals (Simulated via Redirects for now)
    if (action && action.startsWith('opening_modal:')) {
      const modalType = action.split(':')[1];
      if (modalType === 'inventory_add') router.push('/doctor/inventory');
      if (modalType === 'schedule_block') router.push('/doctor/schedule');
      // Fixed the syntax error below:
      alert(`Agent requested to open '${modalType}' modal. Navigating to page instead.`);
    }

    // 3. Handle Direct Intents (Legacy support)
    if (intent === 'NAV_DASHBOARD') router.push('/doctor/dashboard');
    if (intent === 'NAV_SETTINGS' || intent === 'NAV_PROFILE') router.push('/doctor/profile');
    if (intent === 'NAV_LOGOUT') {
        localStorage.removeItem('token');
        router.push('/auth/doctor/login');
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content }),
      });

      const data = await res.json();

      const botMsg: Message = { 
        id: (Date.now() + 1).toString(), 
        role: 'assistant', 
        content: data.response || "I didn't understand that.", 
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, botMsg]);

      // EXECUTE ACTION
      performAction(data.action, data.intent);

    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { 
        id: Date.now().toString(), 
        role: 'assistant', 
        content: "Sorry, I lost connection to the server.", 
        timestamp: new Date() 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-full w-full border-none shadow-none bg-white">
      <div className="p-4 border-b flex justify-between items-center bg-teal-50">
        <div className="flex items-center gap-2">
          <div className="bg-teal-100 p-2 rounded-full">
             <Bot className="w-5 h-5 text-teal-700" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-800">Dental Assistant</h3>
            <p className="text-xs text-teal-600 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Online
            </p>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-teal-700" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] rounded-2xl p-3 text-sm ${
                  msg.role === 'user'
                    ? 'bg-teal-600 text-white rounded-tr-none'
                    : 'bg-gray-100 text-gray-800 rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2">
               <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-teal-700" />
               </div>
               <div className="bg-gray-100 rounded-2xl p-3 rounded-tl-none flex items-center gap-1">
                 <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
               </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your request..."
            className="flex-1 focus-visible:ring-teal-500"
          />
          <Button 
            type="submit" 
            size="icon"
            disabled={isLoading || !input.trim()}
            className="bg-teal-600 hover:bg-teal-700 text-white transition-all duration-200"
          >
            {isLoading ? <Sparkles className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </form>
      </div>
    </Card>
  );
}