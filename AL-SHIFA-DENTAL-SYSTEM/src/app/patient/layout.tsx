import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import PatientAssistantFAB from "@/components/chat/PatientAssistantFAB";

export default function PatientLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* 1. Sidebar remains fixed on the left */}
      <Sidebar role="patient" />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 2. Header remains fixed at the top */}
        <Header role="patient" />

        {/* 3. Main Content Area - This is where children (Dashboard, Booking, etc.) appear */}
        <main className="flex-1 overflow-auto p-6 relative">
          {children}
        </main>
      </div>

      {/* 4. THE FLOATING BRAIN - Outside the main flow so it doesn't push content */}
      <PatientAssistantFAB />
    </div>
  );
}