"use client";
import { useEffect, useState, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar } from "@/components/ui/avatar";
import { 
  Building2, User, Bot, Calendar, Sparkles, Send, ArrowLeft, 
  MessageSquare, Trash2, Clock, ChevronRight, Stethoscope, RefreshCcw
} from "lucide-react";
import { useRouter } from "next/navigation";
import { PatientAPI, AuthAPI, api } from "@/lib/api";

function ManualBooking({ onBack }: { onBack: () => void }) {
    return <div className="p-10 text-center"><h2 className="text-xl font-bold">Manual Booking</h2><Button onClick={onBack} className="mt-4">Back</Button></div>;
}

function AIBooking({ onBack }: { onBack: () => void }) {
  const [messages, setMessages] = useState<{role: string, text: string, time: string}[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentState, setCurrentState] = useState("INIT");
  
  // DATA STORES
  const [hospitals, setHospitals] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [treatments, setTreatments] = useState<any[]>([]); // NEW: Store treatments
  
  const [selectedHospitalId, setSelectedHospitalId] = useState<number | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null); // NEW: Track selected doc
  const [customDate, setCustomDate] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    AuthAPI.getVerifiedHospitals().then(res => setHospitals(res.data));
    PatientAPI.getDoctors().then(res => setDoctors(res.data));
    addBotMessage("Hello! Let s book your appointment. Which hospital?", "SELECT_HOSPITAL");
  }, []);

  // NEW: Fetch treatments when doctor is selected
  useEffect(() => {
      if (selectedDocId) {
          PatientAPI.getDoctorTreatments(selectedDocId)
            .then(res => setTreatments(res.data))
            .catch(err => console.error("Failed to load treatments", err));
      }
  }, [selectedDocId]);

  const addBotMessage = (text: string, state: string) => {
      const cleanText = text.replace(/\[STATE:.*?\]/g, "");
      setMessages(prev => [...prev, { role: "bot", text: cleanText, time: new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) }]);
      setCurrentState(state);
  };

  const handleSend = async (textOverride?: string) => {
    const text = textOverride || input;
    if (!text.trim()) return;

    const newHistory = [...messages, { role: "user", text: text, time: new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) }];
    setMessages(newHistory);
    setInput("");
    setLoading(true);
    setCurrentState("PROCESSING");

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/agent/router", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ user_query: text, role: "patient_booking", history: newHistory.map(m => ({ role: m.role, text: m.text })) })
      });
      const data = await res.json();
      let nextState = "CHAT";
      const match = data.response.match(/\[STATE:\s*(\w+)\]/);
      if (match) nextState = match[1];
      addBotMessage(data.response, nextState);
    } catch { addBotMessage("System Error.", "ERROR"); } 
    finally { setLoading(false); }
  };

  const renderChips = () => {
      if (loading) return null;

      switch (currentState) {
          case "SELECT_HOSPITAL":
              return (
                  <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in slide-in-from-bottom-2">
                      {hospitals.map(h => (
                          <button key={h.id} onClick={() => { setSelectedHospitalId(h.id); handleSend(h.name); }} 
                                  className="flex items-center gap-2 bg-white text-slate-700 px-4 py-2 rounded-xl text-sm font-bold border border-slate-200 hover:border-blue-500 hover:bg-blue-50 transition-all shadow-sm">
                              <Building2 className="h-4 w-4"/> {h.name}
                          </button>
                      ))}
                  </div>
              );

          case "SELECT_DOCTOR":
              const relevantDocs = selectedHospitalId ? doctors.filter(d => d.hospital_id === selectedHospitalId) : doctors;
              if (relevantDocs.length === 0) return <p className="text-xs text-red-500 mt-2">No doctors found here. Type "Change Hospital" to go back.</p>;
              return (
                  <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in slide-in-from-bottom-2">
                      {relevantDocs.map(d => (
                          <button key={d.id} onClick={() => { setSelectedDocId(d.id); handleSend(`Dr. ${d.full_name}`); }} 
                                  className="flex items-center gap-2 bg-white text-slate-700 px-4 py-2 rounded-xl text-sm font-bold border border-slate-200 hover:border-purple-500 hover:bg-purple-50 transition-all shadow-sm">
                              <User className="h-4 w-4"/> Dr. {d.full_name} ({d.specialization})
                          </button>
                      ))}
                      <button onClick={() => handleSend("Change Hospital")} className="px-3 py-2 text-xs text-slate-400 hover:text-slate-600 underline">Change Hospital</button>
                  </div>
              );

          case "SELECT_DATE":
              const today = new Date().toISOString().split('T')[0];
              const tmrw = new Date(Date.now() + 86400000).toISOString().split('T')[0];
              return (
                  <div className="mt-3 animate-in fade-in slide-in-from-bottom-2 space-y-3">
                      <div className="flex gap-2">
                        <button onClick={() => handleSend(today)} className="bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg text-sm font-bold border border-emerald-200 hover:bg-emerald-100">Today</button>
                        <button onClick={() => handleSend(tmrw)} className="bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg text-sm font-bold border border-emerald-200 hover:bg-emerald-100">Tomorrow</button>
                      </div>
                      <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-500">Pick date:</span>
                          <input type="date" className="border text-sm p-1 rounded" onChange={(e) => setCustomDate(e.target.value)} />
                          <Button size="sm" variant="outline" onClick={() => customDate && handleSend(customDate)} disabled={!customDate}>Set</Button>
                      </div>
                  </div>
              );

          case "SELECT_TIME":
              const times = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM", "03:00 PM", "04:00 PM"];
              return (
                  <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in slide-in-from-bottom-2">
                      {times.map(t => (
                          <button key={t} onClick={() => handleSend(t)} className="flex items-center gap-2 bg-orange-50 text-orange-700 px-3 py-1.5 rounded-lg text-sm font-bold border border-orange-200 hover:bg-orange-100 transition-all">
                              <Clock className="h-3 w-3"/> {t}
                          </button>
                      ))}
                  </div>
              );

          case "SELECT_REASON":
              // DYNAMIC REASONS FROM DB
              if (treatments.length === 0) {
                  // Fallback if no treatments found in DB
                  return <div className="flex flex-wrap gap-2 mt-3">{["Checkup", "Pain", "Cleaning"].map(r => <button key={r} onClick={() => handleSend(r)} className="bg-pink-50 text-pink-700 px-4 py-2 rounded-xl text-sm font-bold border border-pink-200">{r}</button>)}</div>;
              }
              return (
                  <div className="flex flex-wrap gap-2 mt-3 animate-in fade-in slide-in-from-bottom-2">
                      {treatments.map((t: any) => (
                          <button key={t.id} onClick={() => handleSend(t.name)} className="bg-pink-50 text-pink-700 px-4 py-2 rounded-xl text-sm font-bold border border-pink-200 hover:bg-pink-100 hover:shadow-md transition-all">
                              <Stethoscope className="inline h-3 w-3 mr-1"/> {t.name} (Rs. {t.cost})
                          </button>
                      ))}
                  </div>
              );
              
          case "DONE":
             return <Button onClick={onBack} className="mt-4 w-full bg-green-600 hover:bg-green-700 text-lg shadow-lg shadow-green-200">Return to Dashboard</Button>;

          default: return null;
      }
  };

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, currentState]);

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col max-w-4xl mx-auto w-full p-4">
      <Button variant="ghost" onClick={onBack} className="w-fit mb-2 text-slate-500"><ArrowLeft className="h-4 w-4 mr-2"/> Exit Chat</Button>
      <Card className="flex-1 flex flex-col overflow-hidden shadow-2xl border-slate-200 rounded-2xl bg-white">
        <div className="p-4 border-b bg-slate-50 flex items-center justify-between"><div className="flex items-center gap-3"><Bot className="h-6 w-6 text-indigo-600"/><div><h3 className="font-bold text-slate-800">Booking Assistant</h3><p className="text-xs text-green-600 font-bold">● Online</p></div></div><Button variant="ghost" size="sm" onClick={() => { setMessages([]); setCurrentState("INIT"); addBotMessage("Resetting... Which hospital?", "SELECT_HOSPITAL"); }}><RefreshCcw className="h-4 w-4"/></Button></div>
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/30">
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <Avatar className="h-8 w-8 mt-1 border border-slate-100 bg-white">{m.role === 'user' ? <User className="h-4 w-4 text-slate-700 m-auto"/> : <Bot className="h-4 w-4 text-indigo-600 m-auto"/>}</Avatar>
              <div className={`flex flex-col max-w-[85%] ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-5 py-3.5 rounded-2xl text-sm shadow-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white border text-slate-700 rounded-tl-none'}`}>{m.text}</div>
                {i === messages.length - 1 && m.role === 'bot' && renderChips()}
              </div>
            </div>
          ))}
          {loading && <div className="text-xs text-slate-400 ml-12 animate-pulse">Thinking...</div>}<div ref={scrollRef}/>
        </div>
        <div className="p-4 bg-white border-t flex gap-2"><Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSend()} placeholder="Type or select an option..." disabled={loading} /><Button onClick={() => handleSend()} disabled={loading} className="bg-indigo-600"><Send className="h-4 w-4"/></Button></div>
      </Card>
    </div>
  );
}

export default function NewBookingPage() {
  const [mode, setMode] = useState<"select" | "manual" | "ai">("select");
  if (mode === "manual") return <ManualBooking onBack={() => setMode("select")} />;
  if (mode === "ai") return <AIBooking onBack={() => setMode("select")} />;
  return (
    <div className="max-w-5xl mx-auto pt-12 p-6 animate-in fade-in duration-700">
      <h1 className="text-4xl font-extrabold text-center mb-12">New Appointment</h1>
      <div className="grid md:grid-cols-2 gap-8">
        <div className="border rounded-3xl p-8 hover:shadow-2xl cursor-pointer transition-all bg-white group" onClick={() => setMode("manual")}> 
            <Calendar className="h-16 w-16 text-blue-600 mb-6 group-hover:scale-110 transition-transform"/> <h2 className="text-2xl font-bold">Manual Booking</h2><p className="text-slate-500">Select slots from calendar.</p>
        </div>
        <div className="border border-indigo-100 bg-indigo-50/50 rounded-3xl p-8 hover:shadow-2xl cursor-pointer transition-all group" onClick={() => setMode("ai")}>
            <Sparkles className="h-16 w-16 text-indigo-600 mb-6 group-hover:scale-110 transition-transform"/><h2 className="text-2xl font-bold text-indigo-900">Book with AI</h2><p className="text-slate-600">Step-by-step guided booking.</p>
        </div>
      </div>
    </div>
  );
}
