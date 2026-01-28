import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Role } from '../types';
import { Button } from '../components/Button';
import { User, Stethoscope, Building2, ArrowRight, ChevronLeft, KeyRound } from 'lucide-react';

export const Auth: React.FC = () => {
  // @ts-ignore - registerPatient is added in Context update
  const { login, registerPatient, hospitals } = useApp();
  const [view, setView] = useState<'selection' | 'login' | 'signup' | 'forgot'>('selection');
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [doctorStep, setDoctorStep] = useState(1); // 1: Creds, 2: Hospital Selection
  
  // Form States
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [patientId, setPatientId] = useState('');
  const [name, setName] = useState('');

  const handleRoleSelect = (role: Role) => {
    setSelectedRole(role);
    setView('login');
    setEmail('');
    setPassword('');
    setPatientId('');
    setName('');
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedRole === Role.DOCTOR) {
        login(Role.DOCTOR, 'd1');
    } else {
        // For demo, if p1 exists try that, else try the patientId entered if mocking
        login(Role.PATIENT, 'p1'); 
    }
  };

  const handleSignup = (e: React.FormEvent) => {
      e.preventDefault();
      if (selectedRole === Role.PATIENT) {
          registerPatient({
              id: patientId || `p-${Date.now()}`,
              name: name || 'New Patient',
              age: 30, // Default
              gender: 'Other', // Default
              email: email,
              history: []
          });
      }
  };

  // Role Selection Screen
  if (view === 'selection') {
    return (
      <div className="min-h-screen bg-medical-50 flex flex-col items-center justify-center p-4">
        <div className="mb-8 text-center animate-fade-in-down">
            <div className="bg-white p-4 rounded-full inline-block shadow-lg mb-4">
                <div className="text-medical-600">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.28 3.6-1.28 5.1-.53M2 13.47c1.5-.75 3.6-.75 5.1.53M9 19c3 1.49 3 4.51 3 4.51s0-3.02 3-4.51M12 4V2m-8 7v14a2 2 0 0 0 2-2V9h12v12a2 2 0 0 0 2 2v-2m-7-9 2 2 2-2"/></svg>
                </div>
            </div>
          <h1 className="text-3xl font-bold text-slate-800">DentalIntell</h1>
          <p className="text-slate-500 mt-2">Advanced Clinic Intelligence System</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl w-full">
          {/* Doctor Card */}
          <div 
            onClick={() => handleRoleSelect(Role.DOCTOR)}
            className="bg-white p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all cursor-pointer border-2 border-transparent hover:border-medical-400 group"
          >
            <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mb-6 group-hover:bg-medical-600 transition-colors">
              <Stethoscope className="w-8 h-8 text-medical-600 group-hover:text-white" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">I am a Doctor</h2>
            <p className="text-slate-500">Manage appointments, patients, and clinic inventory efficiently.</p>
          </div>

          {/* Patient Card */}
          <div 
             onClick={() => handleRoleSelect(Role.PATIENT)}
             className="bg-white p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all cursor-pointer border-2 border-transparent hover:border-green-400 group"
          >
             <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mb-6 group-hover:bg-green-600 transition-colors">
              <User className="w-8 h-8 text-green-600 group-hover:text-white" />
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">I am a Patient</h2>
            <p className="text-slate-500">Book appointments, view history, and track your dental health.</p>
          </div>
        </div>
      </div>
    );
  }

  // Forgot Password Screen
  if (view === 'forgot') {
      return (
        <div className="min-h-screen bg-medical-50 flex items-center justify-center p-4">
            <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full">
                <button onClick={() => setView('login')} className="text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"><ChevronLeft size={16}/> Back to Login</button>
                <div className="flex flex-col items-center mb-6">
                    <div className="w-12 h-12 bg-yellow-50 rounded-full flex items-center justify-center text-yellow-600 mb-3">
                        <KeyRound size={24}/>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-800">Forgot Password?</h2>
                    <p className="text-slate-500 text-center text-sm mt-2">Enter your email address and we'll send you a link to reset your password.</p>
                </div>

                <form onSubmit={(e) => { e.preventDefault(); alert('Reset link sent!'); setView('login'); }} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
                        <input type="email" required className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none" placeholder="name@example.com" />
                    </div>
                    <Button type="submit" fullWidth>Send Reset Link</Button>
                </form>
            </div>
        </div>
      )
  }

  // Doctor Signup Step 2: Select Hospital
  if (view === 'signup' && selectedRole === Role.DOCTOR && doctorStep === 2) {
      return (
        <div className="min-h-screen bg-medical-50 flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full">
          <button onClick={() => setDoctorStep(1)} className="text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"><ChevronLeft size={16}/> Back</button>
          <h2 className="text-2xl font-bold text-slate-800 mb-6">Select Your Clinic</h2>
          
          <div className="space-y-4 mb-6 max-h-64 overflow-y-auto">
              {hospitals.map(h => (
                  <div key={h.id} onClick={() => login(Role.DOCTOR, 'd1')} className="p-3 border rounded-lg hover:bg-medical-50 cursor-pointer flex items-center gap-3 transition-colors">
                      <img src={h.image} alt={h.name} className="w-10 h-10 rounded-full object-cover" />
                      <div>
                          <p className="font-semibold text-slate-800">{h.name}</p>
                          <p className="text-xs text-slate-500">{h.address}</p>
                      </div>
                  </div>
              ))}
          </div>

          <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-gray-200"></div>
            <span className="flex-shrink-0 mx-4 text-gray-400 text-sm">OR</span>
            <div className="flex-grow border-t border-gray-200"></div>
          </div>

          <Button variant="outline" fullWidth className="mt-4">
             <Building2 size={18} /> Register New Clinic
          </Button>
        </div>
      </div>
      )
  }

  // Generic Login/Signup Form
  return (
    <div className="min-h-screen bg-medical-50 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full">
        <button onClick={() => setView('selection')} className="text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"><ChevronLeft size={16}/> Change Role</button>
        
        <h2 className="text-2xl font-bold text-slate-800 mb-2">
            {view === 'login' ? 'Welcome Back' : 'Create Account'}
        </h2>
        <p className="text-slate-500 mb-6">
            {selectedRole === Role.DOCTOR ? 'Access your clinic dashboard' : 'Manage your dental health'}
        </p>

        <form onSubmit={(e) => {
            if (view === 'signup' && selectedRole === Role.DOCTOR) {
                e.preventDefault();
                setDoctorStep(2);
            } else if (view === 'signup' && selectedRole === Role.PATIENT) {
                handleSignup(e);
            } else {
                handleLogin(e);
            }
        }} className="space-y-4">
          
          {view === 'signup' && selectedRole === Role.PATIENT && (
              <>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                    <input type="text" value={name} onChange={e => setName(e.target.value)} required className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none" placeholder="John Doe" />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Create Patient ID (Username)</label>
                    <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)} required className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none" placeholder="john_doe123" />
                </div>
              </>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none" placeholder="name@example.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-medical-400 outline-none" placeholder="••••••••" />
          </div>
          
          {view === 'login' && (
              <div className="flex justify-end">
                  <button type="button" onClick={() => setView('forgot')} className="text-sm text-medical-600 hover:underline">Forgot Password?</button>
              </div>
          )}

          <Button type="submit" fullWidth className="mt-6">
            {view === 'login' ? 'Sign In' : 'Continue'} <ArrowRight size={18} />
          </Button>
        </form>

        <div className="mt-6 text-center">
            <p className="text-sm text-slate-600">
                {view === 'login' ? "Don't have an account? " : "Already have an account? "}
                <button onClick={() => setView(view === 'login' ? 'signup' : 'login')} className="text-medical-600 font-semibold hover:underline">
                    {view === 'login' ? 'Sign Up' : 'Login'}
                </button>
            </p>
        </div>
      </div>
    </div>
  );
};