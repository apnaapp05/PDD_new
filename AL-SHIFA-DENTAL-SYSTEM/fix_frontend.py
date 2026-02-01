import os

file_path = "src/components/chat/SmartAssistant.tsx"

code = r'''
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface Message {
  role: "assistant" | "user";
  content: string;
}

export default function SmartAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I am your Clinical OS. I can manage Patients, Treatments, Inventory, and Finance. How can I help?" }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem("agent_history");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse chat history");
      }
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    if (messages.length > 1) {
        localStorage.setItem("agent_history", JSON.stringify(messages));
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await api.post("/agent/chat", { message: userMsg.content });
      const botMsg: Message = { 
        role: "assistant", 
        content: res.data.response || "I processed that request." 
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error("Agent Error:", error);
      setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ System Error: Unable to reach the Agent brain." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearHistory = () => {
    setMessages([{ role: "assistant", content: "History cleared. Ready for new tasks." }]);
    localStorage.removeItem("agent_history");
  };

  return (
    <Card className="flex flex-col h-[600px] w-full max-w-md mx-auto shadow-xl border-t-4 border-indigo-600">
      <CardHeader className="bg-gray-50 border-b flex flex-row items-center justify-between py-3">
        <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-100 rounded-full">
                <Bot className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
                <CardTitle className="text-lg">Dental Agent</CardTitle>
                <p className="text-xs text-green-600 font-medium flex items-center gap-1">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    Online & Ready
                </p>
            </div>
        </div>
        <Button variant="ghost" size="icon" onClick={clearHistory} title="Clear History">
            <Trash2 className="h-4 w-4 text-gray-400 hover:text-red-500" />
        </Button>
      </CardHeader>
      
      <CardContent className="flex-1 p-0 overflow-hidden relative">
        <ScrollArea className="h-full p-4 pr-5">
          <div className="flex flex-col gap-4 pb-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={lex w-full }
              >
                <div
                  className={lex gap-3 max-w-[85%] }
                >
                  <div
                    className={h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 }
                  >
                    {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  <div
                    className={p-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap shadow-sm }
                  >
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
               <div className="flex w-full justify-start">
                  <div className="flex gap-3 max-w-[85%]">
                     <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                        <Bot size={16} className="text-gray-700"/>
                     </div>
                     <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-tl-none flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                        <span className="text-xs text-gray-500">Thinking...</span>
                     </div>
                  </div>
               </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </CardContent>

      <div className="p-4 bg-white border-t">
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
            placeholder="Type a command (e.g., 'Block 3pm', 'Update Price')..."
            className="flex-1 focus-visible:ring-indigo-500"
          />
          <Button type="submit" disabled={isLoading || !input.trim()} className="bg-indigo-600 hover:bg-indigo-700">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </Card>
  );
}
'''

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code.strip())

print(f"✅ Successfully wrote clean content to {file_path}")
