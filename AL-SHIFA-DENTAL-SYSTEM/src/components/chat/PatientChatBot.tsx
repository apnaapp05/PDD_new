"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Bot, Clock, X, Sparkles, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
  data?: any; // For slots, doctor info, etc.
}

export default function PatientChatBot({ onCancel }: { onCancel: () => void }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "bot",
      content: "Hello! I am the Al-Shifa AI Assistant. \n\nI can help you:\n• Check doctor availability\n• Book appointments\n• Cancel existing bookings\n\nHow can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const sendMessage = async (text: string = input) => {
    if (!text.trim()) return;

    // 1. Add User Message
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      // 2. Call the Brain
      const res = await api.post("/patient/agent/chat", { message: text });
      
      // 3. Add Bot Response
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "bot",
        content: res.data.text,
        data: res.data.data
      };
      
      setMessages((prev) => [...prev, botMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "bot", content: "I'm having trouble reaching the scheduling server. Please try again or use Manual Booking." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  // Helper to click a suggested slot
  const handleSlotClick = (slot: string, doctor: string, date: string) => {
      // We send a message that the Brain will recognize as a confirmation
      const cmd = `Book ${slot} with ${doctor} on ${date}`;
      sendMessage(cmd);
  };

  return (
    <div className="flex flex-col h-[600px] w-full bg-white rounded-3xl shadow-2xl overflow-hidden border border-slate-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-4 flex justify-between items-center text-white shadow-md z-10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 backdrop-blur-sm rounded-full shadow-inner border border-white/10">
            <Bot size={24} className="text-white" />
          </div>
          <div>
            <h3 className="font-bold text-md flex items-center gap-2">
              Al-Shifa Assistant <Sparkles size={12} className="text-yellow-300 animate-pulse"/>
            </h3>
            <p className="text-xs text-purple-100 opacity-90">Powered by SpaCy & RapidFuzz</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onCancel} className="hover:bg-white/20 text-white rounded-full">
          <X size={20} />
        </Button>
      </div>

      {/* Chat Area */}
      <ScrollArea className="flex-1 p-4 bg-slate-50/50">
        <div className="space-y-6">
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.3 }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {/* Message Bubble */}
              <div className={`flex gap-3 max-w-[85%] ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.role === "user" ? "bg-slate-200 text-slate-600" : "bg-purple-100 text-purple-600"}`}>
                    {m.role === "user" ? <User size={14}/> : <Bot size={14}/>}
                </div>

                <div
                  className={`p-4 rounded-2xl text-sm shadow-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === "user"
                      ? "bg-purple-600 text-white rounded-tr-none"
                      : "bg-white text-slate-700 border border-slate-200 rounded-tl-none"
                  }`}
                >
                  {m.content}
                  
                  {/* Interactive Slots (Data Science Magic) */}
                  {m.data && m.data.slots && (
                      <div className="mt-4 pt-3 border-t border-slate-100">
                          <p className="text-xs font-bold text-slate-400 mb-2 uppercase tracking-wider">Available Slots</p>
                          <div className="grid grid-cols-2 gap-2">
                              {m.data.slots.map((slot: string) => (
                                  <button 
                                      key={slot}
                                      onClick={() => handleSlotClick(slot, m.data.doctor, m.data.date)}
                                      className="bg-purple-50 hover:bg-purple-600 hover:text-white text-purple-700 border border-purple-200 rounded-lg py-2 px-3 text-xs transition-all flex items-center justify-center gap-1.5 font-medium"
                                  >
                                      <Clock size={12}/> {slot}
                                  </button>
                              ))}
                          </div>
                      </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start pl-12">
              <div className="bg-white border border-slate-200 py-3 px-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-1.5 w-16">
                <motion.span animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0 }} className="w-1.5 h-1.5 bg-purple-400 rounded-full"/>
                <motion.span animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.2 }} className="w-1.5 h-1.5 bg-purple-400 rounded-full"/>
                <motion.span animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.6, delay: 0.4 }} className="w-1.5 h-1.5 bg-purple-400 rounded-full"/>
              </div>
            </motion.div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-100">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
          className="flex gap-3 items-center"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your request (e.g., 'Book with Dr. Sarah tomorrow')..."
            className="flex-1 bg-slate-50 border-slate-200 focus-visible:ring-purple-500 rounded-full px-4 h-12"
          />
          <Button type="submit" size="icon" disabled={!input.trim() || isTyping} className="bg-purple-600 hover:bg-purple-700 transition-colors h-12 w-12 rounded-full shadow-lg shadow-purple-200 disabled:opacity-50">
            <Send size={20} />
          </Button>
        </form>
      </div>
    </div>
  );
}