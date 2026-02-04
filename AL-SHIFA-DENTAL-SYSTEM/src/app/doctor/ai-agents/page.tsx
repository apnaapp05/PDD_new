import React from 'react';
import SmartAssistant from '@/components/chat/SmartAssistant';
import KnowledgeUpload from '@/components/chat/KnowledgeUpload';
import { Sparkles } from 'lucide-react';

export default function AgentsPage() {
  return (
    <div className="h-[calc(100vh-100px)] flex flex-col gap-4 max-w-7xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center gap-3 border-b pb-4">
        <div className="p-3 bg-teal-100 rounded-xl">
          <Sparkles className="w-6 h-6 text-teal-700" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Master Assistant</h1>
          <p className="text-slate-500">
            One bot to rule them all. Manage Schedule, Inventory, and Finance here.
          </p>
        </div>
      </div>

      <div className="flex gap-6 h-full overflow-hidden">
        {/* Chat Interface (Main) */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border overflow-hidden">
          <SmartAssistant />
        </div>

        {/* Sidebar for Controls */}
        <div className="w-80 flex flex-col gap-4">
          {/* Upload Component */}
          <KnowledgeUpload />

          {/* Future controls can go here */}
        </div>
      </div>
    </div>
  );
}