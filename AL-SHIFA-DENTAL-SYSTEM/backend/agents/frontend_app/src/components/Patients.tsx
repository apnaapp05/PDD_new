import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from './Button';
import { Search, User, FileText, Plus, Sparkles, Activity, DollarSign, X } from 'lucide-react';
import { Patient } from '../types';
import { generateClinicalSummary } from '../services/geminiService';

export const Patients: React.FC = () => {
  const { patients, addNoteToPatient } = useApp();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [newNote, setNewNote] = useState('');
  const [aiSummary, setAiSummary] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);

  const filteredPatients = patients.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    p.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddNote = (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedPatient || !newNote) return;
      
      addNoteToPatient(selectedPatient.id, {
          id: Date.now().toString(),
          date: new Date().toISOString().split('T')[0],
          procedure: 'Doctor Note',
          doctorName: 'Me',
          notes: newNote,
          status: 'Completed'
      });
      setNewNote('');
  };

  const handleGenerateSummary = async () => {
      if (!selectedPatient) return;
      setIsGenerating(true);
      const historyText = selectedPatient.history.map(h => `${h.date}: ${h.procedure} - ${h.notes}`).join('\n');
      const summary = await generateClinicalSummary(historyText);
      setAiSummary(summary);
      setIsGenerating(false);
  };

  // --- AGENT TRIGGERS (New Functionality) ---
  
  const handleAddProcedure = (patientId: string) => {
      // In a real app, this calls the Inventory Agent API
      console.log(`[Agent Trigger] Case Tracking -> Inventory Agent: Stock deducted for procedure on patient ${patientId}`);
      alert("Procedure logged. Stock deduction trigger sent to Inventory Agent.");
  };

  const handleGenerateInvoice = (patientId: string) => {
      // In a real app, this calls the Revenue Agent API
      console.log(`[Agent Trigger] Case Tracking -> Revenue Agent: Generating invoice for patient ${patientId}`);
      alert("Invoice generation request sent to Revenue Agent.");
  };

  return (
    <div className="space-y-6 h-[calc(100vh-100px)] flex flex-col">
      <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-slate-800">Patient Records</h2>
          <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20}/>
              <input 
                type="text" 
                placeholder="Search patients..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none w-64"
              />
          </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden">
          {/* Patient List */}
          <div className="lg:col-span-1 bg-white rounded-xl shadow-sm overflow-hidden flex flex-col border border-gray-200">
              <div className="p-4 bg-slate-50 border-b border-gray-200 font-semibold text-slate-700">
                  All Patients ({filteredPatients.length})
              </div>
              <div className="overflow-y-auto flex-1">
                  {filteredPatients.map(p => (
                      <div 
                        key={p.id} 
                        onClick={() => { setSelectedPatient(p); setAiSummary(''); }}
                        className={`p-4 border-b border-gray-100 cursor-pointer transition-colors hover:bg-slate-50 ${selectedPatient?.id === p.id ? 'bg-medical-50 border-l-4 border-l-medical-600' : ''}`}
                      >
                          <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500">
                                  <User size={20}/>
                              </div>
                              <div>
                                  <p className="font-bold text-slate-800">{p.name}</p>
                                  <p className="text-xs text-slate-500">{p.age} yrs, {p.gender}</p>
                              </div>
                          </div>
                      </div>
                  ))}
              </div>
          </div>

          {/* Patient Detail View */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden">
              {selectedPatient ? (
                  <div className="flex flex-col h-full">
                      {/* Header */}
                      <div className="p-6 border-b border-gray-200 flex justify-between items-start bg-slate-50">
                          <div>
                              <h2 className="text-2xl font-bold text-slate-800">{selectedPatient.name}</h2>
                              <div className="flex gap-4 mt-2 text-sm text-slate-600">
                                  <span>ID: <span className="font-mono">{selectedPatient.id}</span></span>
                                  <span>•</span>
                                  <span>{selectedPatient.email}</span>
                              </div>
                          </div>
                          <div className="flex gap-2">
                              <Button variant="secondary" onClick={() => setSelectedPatient(null)}>
                                <X size={20} />
                              </Button>
                          </div>
                      </div>

                      {/* Agent Actions Toolbar */}
                      <div className="p-4 border-b border-gray-200 bg-white flex flex-wrap gap-3">
                          <Button 
                            variant="outline" 
                            onClick={() => handleAddProcedure(selectedPatient.id)}
                            className="text-xs"
                          >
                            <Activity size={16} /> Add Procedure & Deduct Stock
                          </Button>
                          <Button 
                            variant="outline" 
                            onClick={() => handleGenerateInvoice(selectedPatient.id)}
                            className="text-xs"
                          >
                            <DollarSign size={16} /> Generate Invoice
                          </Button>
                      </div>

                      <div className="flex-1 overflow-y-auto p-6 space-y-6">
                          {/* AI Summary Section */}
                          <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                              <div className="flex justify-between items-center mb-3">
                                  <h3 className="font-bold text-indigo-900 flex items-center gap-2">
                                      <Sparkles size={18} className="text-indigo-600"/> Clinical Summary (AI)
                                  </h3>
                                  <Button 
                                    variant="secondary" 
                                    onClick={handleGenerateSummary} 
                                    disabled={isGenerating}
                                    className="text-xs h-8"
                                  >
                                      {isGenerating ? 'Generating...' : 'Generate Summary'}
                                  </Button>
                              </div>
                              {aiSummary ? (
                                  <p className="text-sm text-indigo-800 leading-relaxed">{aiSummary}</p>
                              ) : (
                                  <p className="text-xs text-indigo-400 italic">Click generate to analyze patient history...</p>
                              )}
                          </div>

                          {/* History Timeline */}
                          <div>
                              <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                                  <FileText size={20} /> Medical History
                              </h3>
                              <div className="space-y-4 relative before:absolute before:left-2 before:top-2 before:h-full before:w-0.5 before:bg-slate-200 pl-6">
                                  {selectedPatient.history.map(item => (
                                      <div key={item.id} className="relative">
                                          <div className="absolute -left-[29px] top-1 w-3 h-3 rounded-full bg-medical-500 border-2 border-white ring-1 ring-slate-200"></div>
                                          <div className="bg-white border border-gray-200 p-4 rounded-lg hover:shadow-md transition-shadow">
                                              <div className="flex justify-between mb-1">
                                                  <span className="font-bold text-slate-800">{item.procedure}</span>
                                                  <span className="text-xs text-slate-500 font-mono">{item.date}</span>
                                              </div>
                                              <p className="text-sm text-slate-600 mb-2">{item.notes}</p>
                                              <div className="text-xs text-slate-400 flex gap-2">
                                                  <span>Dr. {item.doctorName}</span>
                                                  <span>•</span>
                                                  <span className="text-green-600 font-medium">{item.status}</span>
                                              </div>
                                          </div>
                                      </div>
                                  ))}
                              </div>
                          </div>
                      </div>

                      {/* Add Note Footer */}
                      <div className="p-4 border-t border-gray-200 bg-gray-50">
                          <form onSubmit={handleAddNote} className="flex gap-2">
                              <input 
                                type="text" 
                                value={newNote}
                                onChange={(e) => setNewNote(e.target.value)}
                                placeholder="Add a clinical note..."
                                className="flex-1 p-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-medical-400 outline-none"
                              />
                              <Button type="submit">
                                  <Plus size={20} />
                              </Button>
                          </form>
                      </div>
                  </div>
              ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400">
                      <User size={48} className="mb-4 opacity-50" />
                      <p>Select a patient to view records</p>
                  </div>
              )}
          </div>
      </div>
    </div>
  );
};