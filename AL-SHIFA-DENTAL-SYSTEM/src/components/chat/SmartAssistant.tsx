import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Trash2, Loader2, ExternalLink, MessageSquare } from "lucide-react";
import { AgentAPI } from "@/lib/api"; 
import { useRouter } from "next/navigation"; 

// --- Types ---
interface BotButton {
  label: string;
  action: string;
  type: "navigate" | "chat";
}

interface BotResponse {
  text: string;
  buttons?: BotButton[];
}

interface Message {
  role: "assistant" | "user";
  content: string | BotResponse;
}

export default function SmartAssistant() {
  const router = useRouter();
  
  // --- State ---
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: "assistant", 
      content: { text: "Hello! I am your Clinical OS. I can manage Patients, Treatments, Inventory, and Finance. How can I help?" } 
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- Effects: History & Scroll ---
  
  // 1. Load History on Mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("agent_history");
      if (saved) {
        try {
          setMessages(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse chat history", e);
        }
      }
    }
  }, []);

  // 2. Save History & Scroll on Update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    if (messages.length > 1) {
        localStorage.setItem("agent_history", JSON.stringify(messages));
    }
  }, [messages]);

  // --- Handlers ---

  const handleSend = async (textOverride?: string) => {
    const textToSend = textOverride || input;
    if (!textToSend.trim()) return;

    // 1. Add User Message
    const userMsg: Message = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      // 2. API Call
      const res = await AgentAPI.chat(textToSend);
      const botData = res.data.response; 
      
      // 3. Normalize Response (Handle both string and object responses)
      const botContent: BotResponse = typeof botData === "string" 
        ? { text: botData, buttons: [] } 
        : botData;

      setMessages((prev) => [...prev, { role: "assistant", content: botContent }]);
    } catch (error) {
      console.error("Agent Error:", error);
      setMessages((prev) => [...prev, { 
        role: "assistant", 
        content: { text: "⚠️ System Error: Unable to reach the Agent brain." } 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleButtonClick = (btn: BotButton) => {
    if (btn.type === "navigate") {
      router.push(btn.action);
    } else {
      handleSend(btn.action);
    }
  };

  const clearHistory = () => {
    const resetMsg: Message = { 
      role: "assistant", 
      content: { text: "History cleared. Ready for new tasks." } 
    };
    setMessages([resetMsg]);
    localStorage.removeItem("agent_history");
  };

  // --- Render Helpers ---
  
  // Safely renders text with simple formatting (Bold)
  const renderText = (content: string | BotResponse) => {
    // FIX: Extract text string safely, handling both String and Object formats
    const text = typeof content === "string" ? content : (content?.text || "");
    
    if (!text) return null; 

    // Replace **bold** with <strong>bold</strong> and newlines with <br>
    const formatted = text
      .replace(/\n/g, "<br/>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      
    return <div dangerouslySetInnerHTML={{ __html: formatted }} />;
  };

  return (
    <Card className="flex flex-col h-[600px] w-full max-w-md mx-auto shadow-xl border-t-4 border-indigo-600">
      {/* Header */}
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
      
      {/* Chat Area */}
      <CardContent className="flex-1 p-0 overflow-hidden relative bg-slate-50/50">
        <ScrollArea className="h-full p-4 pr-5">
          <div className="flex flex-col gap-6 pb-4">
            {messages.map((msg, i) => {
              const isUser = msg.role === "user";
              
              // FIX: Robust content extraction
              let buttons: BotButton[] = [];
              if (!isUser && typeof msg.content !== "string") {
                 buttons = (msg.content as BotResponse).buttons || [];
              }

              return (
                <div key={i} className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-3 max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                    
                    {/* Avatar Icon */}
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? "bg-indigo-600 text-white" : "bg-white border border-gray-200 shadow-sm text-indigo-600"}`}>
                      {isUser ? <User size={16} /> : <Bot size={16} />}
                    </div>

                    {/* Content Bubble */}
                    <div className="flex flex-col gap-2 items-start max-w-full">
                        <div className={`p-3.5 px-5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                          isUser 
                            ? "bg-indigo-600 text-white rounded-tr-none" 
                            : "bg-white border border-gray-200 text-gray-800 rounded-tl-none"
                        }`}>
                          {renderText(msg.content)}
                        </div>

                        {/* Interactive Buttons (Bot Only) */}
                        {!isUser && buttons.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-1 pl-1">
                                {buttons.map((btn, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => handleButtonClick(btn)}
                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full transition-colors border border-indigo-200"
                                    >
                                        {btn.type === "navigate" ? <ExternalLink size={12} /> : <MessageSquare size={12} />}
                                        {btn.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                  </div>
                </div>
              );
            })}

            {/* Loading Spinner */}
            {isLoading && (
               <div className="flex w-full justify-start">
                  <div className="flex gap-3 max-w-[85%]">
                     <div className="h-8 w-8 rounded-full bg-white border border-gray-200 flex items-center justify-center">
                        <Bot size={16} className="text-gray-400"/>
                     </div>
                     <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-tl-none flex items-center gap-2 shadow-sm">
                        <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
                        <span className="text-xs text-gray-400 font-medium">Processing...</span>
                     </div>
                  </div>
               </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </CardContent>

      {/* Input Area */}
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
            placeholder="Ask me anything..."
            className="flex-1 focus-visible:ring-indigo-500 bg-gray-50 border-gray-200"
          />
          <Button type="submit" disabled={isLoading || !input.trim()} className="bg-indigo-600 hover:bg-indigo-700 shadow-md transition-all">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </Card>
  );
}