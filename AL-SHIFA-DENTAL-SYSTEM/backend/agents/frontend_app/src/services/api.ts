// src/services/api.ts
import { Appointment } from '../types';

const API_BASE_URL = 'http://localhost:8000'; // The URL of your Python Backend

export const api = {
  // 1. System Check
  checkHealth: async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/`);
      return await res.json();
    } catch (e) {
      console.error("Backend Offline", e);
      return { status: "Offline" };
    }
  },

  // 2. Appointment Agent (Book)
  bookAppointment: async (patientName: string, patientId: string, query: string) => {
    const res = await fetch(`${API_BASE_URL}/api/appointments/book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        user_query: query, 
        patient_id: patientId, 
        patient_name: patientName 
      }),
    });
    return res.json(); // Returns the Agent's structured response
  },

  // 3. Inventory Agent (Update Stock)
  updateStock: async (itemId: string, quantity: number) => {
    const res = await fetch(`${API_BASE_URL}/api/inventory/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: itemId, quantity }),
    });
    return res.json();
  },

  // 4. Case Tracking Agent (Trigger Procedure & Stock Deduction)
  logProcedure: async (patientId: string, procedure: string) => {
    const res = await fetch(`${API_BASE_URL}/api/cases/add-procedure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId, procedure: procedure }),
    });
    return res.json();
  },

  // 5. Revenue Agent (Generate Invoice)
  generateInvoice: async (patientId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/revenue/generate-invoice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId }),
    });
    return res.json();
  }
};