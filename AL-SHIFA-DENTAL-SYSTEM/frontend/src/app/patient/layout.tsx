import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import PatientAssistantFAB from "@/components/chat/PatientAssistantFAB";

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar role="patient" />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Pass role purely for context, Header handles the rest */}
        <Header role="patient" /> 
        <main className="flex-1 overflow-auto p-6 relative">
          {children}
        </main>
      </div>
      {/* The Toggle Button Component */}
      <PatientAssistantFAB />
    </div>
  );
}