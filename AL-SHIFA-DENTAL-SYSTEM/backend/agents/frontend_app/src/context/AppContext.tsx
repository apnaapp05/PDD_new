import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AppContextType, Role, Appointment, InventoryItem, MedicalHistoryItem, Patient, Invoice } from '../types';
import { MOCK_HOSPITALS, MOCK_DOCTORS, MOCK_PATIENTS, MOCK_INVENTORY, MOCK_APPOINTMENTS, MOCK_INVOICES } from '../mockData';
// IMPORTS FOR INTEGRATION
import { api } from '../services/api';

const AppContext = createContext<AppContextType & { registerPatient: (patient: Patient) => void } | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AppContextType['user']>(null);
  const [appointments, setAppointments] = useState<Appointment[]>(MOCK_APPOINTMENTS);
  const [inventory, setInventory] = useState<InventoryItem[]>(MOCK_INVENTORY);
  const [patients, setPatients] = useState<Patient[]>(MOCK_PATIENTS);
  const [invoices, setInvoices] = useState<Invoice[]>(MOCK_INVOICES);

  // 1. Check Backend Connection on Load
  useEffect(() => {
    api.checkHealth().then(status => console.log("Backend Status:", status));
  }, []);

  const login = (role: Role, id: string) => {
    if (role === Role.DOCTOR) {
      const doc = MOCK_DOCTORS.find(d => d.id === id);
      if (doc) setUser({ role, id, name: doc.name, hospitalId: doc.hospitalId });
    } else {
      const pat = patients.find(p => p.id === id);
      if (pat) setUser({ role, id, name: pat.name });
    }
  };

  const registerPatient = (newPatient: Patient) => {
      setPatients([...patients, newPatient]);
      setUser({ role: Role.PATIENT, id: newPatient.id, name: newPatient.name });
  };

  const logout = () => setUser(null);

  // --- INTEGRATED FUNCTION: Book Appointment ---
  const bookAppointment = async (appt: Omit<Appointment, 'id' | 'status'>) => {
    try {
        // 1. Call the Appointment Agent
        const response = await api.bookAppointment("Current User", appt.patientId, `Book appointment on ${appt.date} at ${appt.timeSlot}`);
        console.log("Agent Response:", response);

        // 2. Update UI if successful
        if (response.status === 'SUCCESS' || response.status === 'PENDING_TOOL_CALL') {
            const newAppt: Appointment = {
                ...appt,
                id: Math.random().toString(36).substr(2, 9),
                status: 'Confirmed'
            };
            setAppointments([...appointments, newAppt]);
            alert("Appointment confirmed by Agent!");
        }
    } catch (error) {
        console.error("Booking failed:", error);
        alert("Failed to connect to Appointment Agent.");
    }
  };

  // --- INTEGRATED FUNCTION: Update Stock ---
  const updateStock = async (itemId: string, newStock: number) => {
    try {
        // 1. Call Inventory Agent
        await api.updateStock(itemId, newStock);
        
        // 2. Update UI
        setInventory(prev => prev.map(item => item.id === itemId ? { ...item, stock: newStock } : item));
    } catch (error) {
        alert("Failed to update stock in backend.");
    }
  };

  const addNoteToPatient = (patientId: string, note: MedicalHistoryItem) => {
      setPatients(prev => prev.map(p => {
          if (p.id === patientId) {
              return { ...p, history: [note, ...p.history] };
          }
          return p;
      }));
  };

  return (
    <AppContext.Provider value={{
      user,
      hospitals: MOCK_HOSPITALS,
      doctors: MOCK_DOCTORS,
      patients,
      appointments,
      inventory,
      invoices,
      login,
      logout,
      registerPatient,
      bookAppointment,
      updateStock,
      addNoteToPatient
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};