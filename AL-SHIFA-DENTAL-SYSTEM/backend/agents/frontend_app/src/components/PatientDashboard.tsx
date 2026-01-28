import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/Button';
import { Calendar, Clock, MapPin, Activity, FileText, Bell, User, MessageSquare, ChevronDown, LogOut, Settings, Send, X } from 'lucide-react';
import { Hospital, Doctor } from '../types';
import { chatWithReceptionist } from '../services/geminiService';

export const PatientDashboard: React.FC = () => {
  const { user, appointments, hospitals, doctors, bookAppointment, patients, logout } = useApp();
  const [activeTab, setActiveTab] = useState<'home' | 'book' | 'history'>('home');
  
  // Profile Dropdown
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Booking State
  const [bookingMode, setBookingMode] = useState<'select' | 'manual' | 'chat'>('select');
  const [bookingStep, setBookingStep] = useState(1);
  const [selectedHospital, setSelectedHospital] = useState<Hospital | null>(null);
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');

  // Chat State
  const [chatHistory, setChatHistory] = useState<{role: string, text: string}[]>([
      { role: 'model', text: 'Hello! I am the clinic virtual assistant. How can I help you book an appointment today?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Current Patient Info
  const patientProfile = patients.find(p => p.id === user?.id);
  const myAppointments = appointments.filter(a => a.patientId === user?.id);

  useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
          if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
              setShowProfileMenu(false);
          }
      };
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleBook = () => {
    if(selectedHospital && selectedDoctor && selectedDate && selectedTime && user) {
        bookAppointment({
            patientId: user.id,
            hospitalId: selectedHospital.id,
            doctorId: selectedDoctor.id,
            date: selectedDate,
            timeSlot: selectedTime,
            type: 'General Checkup'
        });
        setActiveTab('home');
        setBookingStep(1);
        setBookingMode('select');
        // Reset
        setSelectedHospital(null);
        setSelectedDoctor(null);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!chatInput.trim()) return;

      const newHistory = [...chatHistory, { role: 'user', text: chatInput }];
      setChatHistory(newHistory);
      setChatInput('');
      setIsChatLoading(true);

      // Format for Gemini API
      const apiHistory = newHistory.map(h => ({
          role: h.role,
          parts: [{ text: h.text }]
      }));

      const response = await chatWithReceptionist(chatInput, apiHistory);
      
      setChatHistory([...newHistory, { role: 'model', text: response }]);
      setIsChatLoading(false);
  };

  const renderBookingFlow = () => {
      if (bookingMode === 'select') {
          return (
            <div className="max-w-3xl mx-auto">
                <h2 className="text-2xl font-bold text-slate-800 mb-6 text-center">How would you like to book?</h2>
                <div className="grid md:grid-cols-2 gap-6">
                    <div 
                        onClick={() => setBookingMode('manual')}
                        className="bg-white p-8 rounded-2xl shadow-sm border-2 border-transparent hover:border-medical-500 cursor-pointer transition-all group text-center"
                    >
                        <div className="w-16 h-16 bg-medical-50 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-medical-600 transition-colors">
                            <Calendar className="text-medical-600 group-hover:text-white w-8 h-8" />
                        </div>
                        <h3 className="text-xl font-bold text-slate-800 mb-2">Manual Booking</h3>
                        <p className="text-slate-500">Select your preferred clinic, doctor, and time slot step-by-step.</p>
                    </div>

                    <div 
                        onClick={() => setBookingMode('chat')}
                        className="bg-white p-8 rounded-2xl shadow-sm border-2 border-transparent hover:border-purple-500 cursor-pointer transition-all group text-center"
                    >
                        <div className="w-16 h-16 bg-purple-50 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-purple-600 transition-colors">
                            <MessageSquare className="text-purple-600 group-hover:text-white w-8 h-8" />
                        </div>
                        <h3 className="text-xl font-bold text-slate-800 mb-2">Chat Assistant</h3>
                        <p className="text-slate-500">Talk to our AI receptionist to find the perfect time for you.</p>
                    </div>
                </div>
            </div>
          );
      }

      if (bookingMode === 'chat') {
          return (
              <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-[600px]">
                  <div className="p-4 bg-purple-600 text-white flex justify-between items-center">
                      <div className="flex items-center gap-2">
                          <MessageSquare size={20} />
                          <h3 className="font-bold">AI Assistant</h3>
                      </div>
                      <button onClick={() => setBookingMode('select')} className="text-white/80 hover:text-white">
                          <X size={20} />
                      </button>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                      {chatHistory.map((msg, idx) => (
                          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                              <div className={`max-w-[80%] p-3 rounded-lg ${msg.role === 'user' ? 'bg-purple-600 text-white rounded-br-none' : 'bg-white text-slate-800 shadow-sm rounded-bl-none border border-gray-100'}`}>
                                  {msg.text}
                              </div>
                          </div>
                      ))}
                      {isChatLoading && (
                          <div className="flex justify-start">
                              <div className="bg-white text-slate-500 p-3 rounded-lg rounded-bl-none shadow-sm text-sm italic">
                                  Typing...
                              </div>
                          </div>
                      )}
                  </div>

                  <form onSubmit={handleSendMessage} className="p-4 bg-white border-t border-gray-100 flex gap-2">
                      <input 
                        type="text" 
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="I need a dentist next Tuesday..."
                        className="flex-1 p-3 border rounded-lg outline-none focus:border-purple-500"
                      />
                      <Button type="submit" disabled={!chatInput.trim() || isChatLoading} className="!bg-purple-600 hover:!bg-purple-700">
                          <Send size={18} />
                      </Button>
                  </form>
              </div>
          );
      }

      // Manual Booking Flow
      return (
          <div className="max-w-3xl mx-auto">
             <button onClick={() => { setBookingMode('select'); setBookingStep(1); }} className="text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"><ChevronDown size={16} className="rotate-90"/> Back to Options</button>
             
             {/* Progress Bar */}
             <div className="flex justify-between mb-8 relative">
                 <div className="absolute top-1/2 left-0 w-full h-1 bg-gray-200 -z-10"></div>
                 {[1, 2, 3].map(step => (
                     <div key={step} className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${bookingStep >= step ? 'bg-medical-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
                         {step}
                     </div>
                 ))}
             </div>

             {bookingStep === 1 && (
                 <div>
                     <h2 className="text-xl font-bold text-slate-800 mb-4">Select a Clinic</h2>
                     <div className="grid md:grid-cols-2 gap-4">
                         {hospitals.map(h => (
                             <div key={h.id} onClick={() => { setSelectedHospital(h); setBookingStep(2); }} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:border-medical-400 cursor-pointer transition-all flex gap-4">
                                 <img src={h.image} className="w-20 h-20 rounded-lg object-cover" alt={h.name} />
                                 <div>
                                     <h3 className="font-bold text-slate-800">{h.name}</h3>
                                     <p className="text-sm text-slate-500 flex items-center gap-1 mt-1"><MapPin size={14}/> {h.address}</p>
                                 </div>
                             </div>
                         ))}
                     </div>
                 </div>
             )}

             {bookingStep === 2 && (
                 <div>
                     <button onClick={() => setBookingStep(1)} className="text-sm text-slate-500 mb-4 hover:underline">Back to Clinics</button>
                     <h2 className="text-xl font-bold text-slate-800 mb-4">Select a Doctor at {selectedHospital?.name}</h2>
                     <div className="grid md:grid-cols-2 gap-4">
                         {doctors.filter(d => d.hospitalId === selectedHospital?.id).map(d => (
                             <div key={d.id} onClick={() => { setSelectedDoctor(d); setBookingStep(3); }} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 hover:border-medical-400 cursor-pointer transition-all flex gap-4 items-center">
                                 <img src={d.image} className="w-16 h-16 rounded-full object-cover" alt={d.name} />
                                 <div>
                                     <h3 className="font-bold text-slate-800">{d.name}</h3>
                                     <p className="text-sm text-medical-600 font-medium">{d.specialization}</p>
                                     <p className="text-xs text-yellow-500 mt-1">★ {d.rating}</p>
                                 </div>
                             </div>
                         ))}
                     </div>
                 </div>
             )}

             {bookingStep === 3 && (
                 <div className="bg-white p-6 rounded-xl shadow-sm">
                     <button onClick={() => setBookingStep(2)} className="text-sm text-slate-500 mb-4 hover:underline">Back to Doctors</button>
                     <h2 className="text-xl font-bold text-slate-800 mb-6">Schedule Appointment</h2>
                     
                     <div className="mb-6">
                         <label className="block text-sm font-medium text-slate-700 mb-2">Select Date</label>
                         <input type="date" onChange={(e) => setSelectedDate(e.target.value)} className="w-full p-3 border rounded-lg outline-none focus:border-medical-500" />
                     </div>

                     <div className="mb-8">
                        <label className="block text-sm font-medium text-slate-700 mb-2">Available Slots</label>
                        <div className="grid grid-cols-3 gap-2">
                            {['09:00 AM', '10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM'].map(time => (
                                <button 
                                    key={time} 
                                    onClick={() => setSelectedTime(time)}
                                    className={`p-2 rounded-lg text-sm border ${selectedTime === time ? 'bg-medical-600 text-white border-medical-600' : 'bg-white text-slate-600 border-gray-200 hover:bg-gray-50'}`}
                                >
                                    {time}
                                </button>
                            ))}
                        </div>
                     </div>

                     <Button fullWidth onClick={handleBook} disabled={!selectedDate || !selectedTime}>
                         Confirm Booking
                     </Button>
                 </div>
             )}
          </div>
      )
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20 md:pb-0">
      {/* Header */}
      <header className="bg-white shadow-sm p-4 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold text-medical-600">MyHealth</h1>
          
          {/* Profile Menu */}
          <div className="relative" ref={profileRef}>
            <button 
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="flex items-center gap-3 hover:bg-gray-50 p-2 rounded-lg transition-colors"
            >
                <div className="text-right hidden md:block">
                    <p className="font-semibold text-sm text-slate-800">{user?.name}</p>
                    <p className="text-xs text-slate-500">ID: {user?.id}</p>
                </div>
                <div className="w-10 h-10 bg-medical-100 rounded-full flex items-center justify-center text-medical-700 font-bold border-2 border-white shadow-sm">
                    {user?.name.charAt(0)}
                </div>
                <ChevronDown size={16} className="text-slate-400" />
            </button>

            {/* Dropdown */}
            {showProfileMenu && (
                <div className="absolute right-0 top-full mt-2 w-72 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden animate-fade-in">
                    <div className="p-6 bg-medical-50 border-b border-gray-100">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-xl font-bold text-medical-600 shadow-sm">
                                {user?.name.charAt(0)}
                            </div>
                            <div>
                                <h3 className="font-bold text-slate-800">{user?.name}</h3>
                                <p className="text-xs text-slate-500">@{user?.id}</p>
                            </div>
                        </div>
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-slate-500">Email</span>
                                <span className="font-medium text-slate-700">{patientProfile?.email}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500">Age/Sex</span>
                                <span className="font-medium text-slate-700">{patientProfile?.age} / {patientProfile?.gender}</span>
                            </div>
                        </div>
                    </div>
                    <div className="p-2">
                        <button className="w-full flex items-center gap-3 p-3 hover:bg-slate-50 rounded-lg text-slate-600 text-sm font-medium">
                            <Settings size={16} /> Account Settings
                        </button>
                        <button 
                            onClick={() => logout()}
                            className="w-full flex items-center gap-3 p-3 hover:bg-red-50 rounded-lg text-red-600 text-sm font-medium"
                        >
                            <LogOut size={16} /> Logout
                        </button>
                    </div>
                </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-4">
        {activeTab === 'home' && (
            <div className="space-y-6">
                {/* Welcome & Stats */}
                <div className="bg-gradient-to-r from-medical-600 to-medical-800 rounded-2xl p-6 text-white shadow-lg">
                    <h2 className="text-2xl font-bold mb-2">Welcome back, {user?.name.split(' ')[0]}</h2>
                    <p className="opacity-90">Your dental health score is looking great!</p>
                </div>

                {/* Reminders */}
                {myAppointments.length > 0 && (
                    <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-yellow-400 flex items-start gap-3">
                        <Bell className="text-yellow-500 flex-shrink-0" />
                        <div>
                            <h3 className="font-bold text-slate-800">Upcoming Appointment</h3>
                            <p className="text-sm text-slate-600">
                                {myAppointments[myAppointments.length - 1].date} at {myAppointments[myAppointments.length - 1].timeSlot} with Dr. {doctors.find(d => d.id === myAppointments[myAppointments.length - 1].doctorId)?.name}
                            </p>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                    <div onClick={() => setActiveTab('book')} className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col items-center justify-center gap-3 text-center h-40">
                        <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-medical-600">
                            <Calendar size={24}/>
                        </div>
                        <span className="font-semibold text-slate-700">Book Visit</span>
                    </div>
                    <div onClick={() => setActiveTab('history')} className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col items-center justify-center gap-3 text-center h-40">
                        <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center text-purple-600">
                            <Activity size={24}/>
                        </div>
                        <span className="font-semibold text-slate-700">My History</span>
                    </div>
                </div>
            </div>
        )}

        {activeTab === 'book' && renderBookingFlow()}

        {activeTab === 'history' && (
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-100">
                    <h2 className="text-lg font-bold text-slate-800">Treatment History</h2>
                </div>
                <div className="divide-y divide-gray-100">
                    {patientProfile?.history.map(item => (
                        <div key={item.id} className="p-4 hover:bg-gray-50">
                            <div className="flex justify-between items-start mb-1">
                                <h3 className="font-semibold text-slate-800">{item.procedure}</h3>
                                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">{item.status}</span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-slate-500 mb-2">
                                <span className="flex items-center gap-1"><Calendar size={14}/> {item.date}</span>
                                <span className="flex items-center gap-1"><User size={14}/> {item.doctorName}</span>
                            </div>
                            <p className="text-sm text-slate-600 bg-gray-50 p-2 rounded border border-gray-100">
                                <FileText size={12} className="inline mr-1"/> {item.notes}
                            </p>
                        </div>
                    ))}
                    {(!patientProfile?.history || patientProfile.history.length === 0) && (
                        <div className="p-8 text-center text-slate-400 text-sm">No history found.</div>
                    )}
                </div>
            </div>
        )}
      </main>
      
      {/* Mobile Nav */}
      <div className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-200 md:hidden flex justify-around p-3 text-xs font-medium text-slate-500 z-10">
        <button onClick={() => setActiveTab('home')} className={`flex flex-col items-center gap-1 ${activeTab === 'home' ? 'text-medical-600' : ''}`}>
            <Calendar size={20}/> Home
        </button>
        <button onClick={() => setActiveTab('book')} className={`flex flex-col items-center gap-1 ${activeTab === 'book' ? 'text-medical-600' : ''}`}>
            <Clock size={20}/> Book
        </button>
        <button onClick={() => setActiveTab('history')} className={`flex flex-col items-center gap-1 ${activeTab === 'history' ? 'text-medical-600' : ''}`}>
            <Activity size={20}/> History
        </button>
      </div>
    </div>
  );
};