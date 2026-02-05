"use client";

import PatientChatBot from "@/components/chat/PatientChatBot";
import { Button } from "@/components/ui/button";
import { X, Bot, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";

export default function AIChatPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] w-full max-w-5xl mx-auto">

      {/* Header Bar */}
      <div className="flex justify-between items-center bg-white p-5 rounded-t-3xl shadow-sm border-x border-t border-slate-100">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center shadow-lg shadow-teal-100">
            <Bot className="h-7 w-7 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-black text-slate-800 tracking-tight">Al-Shifa Smart Assistant</h1>
            <div className="flex items-center gap-1.5">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Live Analysis Active</p>
            </div>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={() => router.back()}
          className="rounded-xl border-red-100 text-red-600 hover:bg-red-50 hover:border-red-200 font-bold transition-all px-6"
        >
          <X className="mr-2 h-4 w-4" /> Exit
        </Button>
      </div>


      {/* Chat Component Container */}
      <div className="flex-1 bg-white border-x border-b border-slate-100 rounded-b-3xl shadow-2xl shadow-slate-200/50 overflow-hidden">
        <PatientChatBot isFullPage={true} />
      </div>

      {/* Footer Disclaimer */}
      <p className="text-center text-[10px] text-slate-400 mt-4 flex items-center justify-center gap-1.5">
        <ShieldCheck className="h-3 w-3" /> Secure AI Session. Your medical data is protected.
      </p>
    </div >
  );
}