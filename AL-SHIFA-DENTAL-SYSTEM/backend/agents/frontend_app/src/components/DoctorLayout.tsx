import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { LayoutDashboard, Calendar, Users, Package, DollarSign, LogOut, Menu, X } from 'lucide-react';
import { DoctorDashboard } from './DoctorDashboard';
import { Schedule } from './Schedule';
import { Patients } from './Patients';
import { Inventory } from './Inventory';
import { Finance } from './Finance';

export const DoctorLayout: React.FC = () => {
  const { user, logout } = useApp();
  const [activePage, setActivePage] = useState<'dashboard' | 'schedule' | 'patients' | 'inventory' | 'finance'>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'schedule', label: 'Schedule', icon: Calendar },
    { id: 'patients', label: 'Patients', icon: Users },
    { id: 'inventory', label: 'Inventory', icon: Package },
    { id: 'finance', label: 'Finance', icon: DollarSign },
  ];

  const NavContent = () => (
    <>
        <div className="p-6 border-b border-gray-700">
            <h1 className="text-xl font-bold text-white">DentalIntell</h1>
            <p className="text-xs text-medical-200 mt-1">Dr. {user?.name.split(' ')[1]}</p>
        </div>
        <nav className="flex-1 p-4 space-y-2">
            {navItems.map(item => (
                <button
                    key={item.id}
                    onClick={() => { setActivePage(item.id as any); setMobileMenuOpen(false); }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activePage === item.id ? 'bg-medical-600 text-white shadow-lg' : 'text-medical-100 hover:bg-medical-800 hover:text-white'}`}
                >
                    <item.icon size={20} />
                    <span className="font-medium">{item.label}</span>
                </button>
            ))}
        </nav>
        <div className="p-4 border-t border-gray-700">
            <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-3 text-red-300 hover:bg-medical-800 hover:text-red-200 rounded-lg transition-all">
                <LogOut size={20} />
                <span>Logout</span>
            </button>
        </div>
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar Desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-medical-900 h-screen sticky top-0">
        <NavContent />
      </aside>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 w-full bg-medical-900 text-white z-20 flex justify-between items-center p-4 shadow-md">
          <h1 className="font-bold">DentalIntell</h1>
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <X /> : <Menu />}
          </button>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
          <div className="fixed inset-0 bg-medical-900 z-10 pt-16 md:hidden flex flex-col">
              <NavContent />
          </div>
      )}

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-8 mt-16 md:mt-0 overflow-y-auto h-screen">
        {activePage === 'dashboard' && <DoctorDashboard />}
        {activePage === 'schedule' && <Schedule />}
        {activePage === 'patients' && <Patients />}
        {activePage === 'inventory' && <Inventory />}
        {activePage === 'finance' && <Finance />}
      </main>
    </div>
  );
};
