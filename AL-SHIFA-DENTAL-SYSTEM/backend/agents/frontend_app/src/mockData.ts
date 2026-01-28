import { Hospital, Doctor, Patient, InventoryItem, Appointment, Invoice } from './types';

export const MOCK_HOSPITALS: Hospital[] = [
  { id: 'h1', name: 'City Dental Clinic', address: '123 Main St, Downtown', image: 'https://picsum.photos/100/100?random=1' },
  { id: 'h2', name: 'Bright Smiles Center', address: '456 Oak Ave, Westside', image: 'https://picsum.photos/100/100?random=2' },
  { id: 'h3', name: 'Elite Orthodontics', address: '789 Pine Ln, Uptown', image: 'https://picsum.photos/100/100?random=3' },
];

export const MOCK_DOCTORS: Doctor[] = [
  { id: 'd1', name: 'Dr. Sarah Smith', specialization: 'Orthodontist', hospitalId: 'h1', image: 'https://picsum.photos/200/200?random=4', rating: 4.8 },
  { id: 'd2', name: 'Dr. John Doe', specialization: 'General Dentist', hospitalId: 'h1', image: 'https://picsum.photos/200/200?random=5', rating: 4.5 },
  { id: 'd3', name: 'Dr. Emily White', specialization: 'Oral Surgeon', hospitalId: 'h2', image: 'https://picsum.photos/200/200?random=6', rating: 4.9 },
];

export const MOCK_INVENTORY: InventoryItem[] = [
  { id: 'i1', name: 'Dental Implants (Ti)', stock: 5, unit: 'units', minThreshold: 10, category: 'Implants' },
  { id: 'i2', name: 'Anesthetic (Lidocaine)', stock: 45, unit: 'vials', minThreshold: 20, category: 'Medicine' },
  { id: 'i3', name: 'Latex Gloves (M)', stock: 12, unit: 'boxes', minThreshold: 15, category: 'PPE' },
  { id: 'i4', name: 'Composite Resin', stock: 30, unit: 'tubes', minThreshold: 5, category: 'Restorative' },
];

export const MOCK_PATIENTS: Patient[] = [
  {
    id: 'p1', name: 'Alice Johnson', age: 32, gender: 'Female', email: 'alice@example.com',
    history: [
      { id: 'hist1', date: '2023-10-15', procedure: 'Root Canal', doctorName: 'Dr. Sarah Smith', notes: 'Patient tolerated procedure well. Follow up in 2 weeks.', status: 'Completed' },
      { id: 'hist2', date: '2024-01-10', procedure: 'Cleaning', doctorName: 'Dr. John Doe', notes: 'Routine cleaning. No cavities found.', status: 'Completed' }
    ]
  },
  {
    id: 'p2', name: 'Bob Williams', age: 45, gender: 'Male', email: 'bob@example.com',
    history: [
       { id: 'hist3', date: '2024-05-20', procedure: 'Extraction', doctorName: 'Dr. Emily White', notes: 'Wisdom tooth extraction lower right.', status: 'Completed' }
    ]
  }
];

export const MOCK_APPOINTMENTS: Appointment[] = [
  { id: 'a1', patientId: 'p1', doctorId: 'd1', hospitalId: 'h1', date: new Date().toISOString().split('T')[0], timeSlot: '10:00 AM', status: 'Confirmed', type: 'Checkup' },
  { id: 'a2', patientId: 'p2', doctorId: 'd1', hospitalId: 'h1', date: new Date().toISOString().split('T')[0], timeSlot: '02:00 PM', status: 'Confirmed', type: 'Consultation' },
];

export const MOCK_INVOICES: Invoice[] = [
  { id: 'inv1', patientName: 'Alice Johnson', amount: 1200, date: '2024-05-21', status: 'Paid' },
  { id: 'inv2', patientName: 'Bob Williams', amount: 350, date: '2024-05-22', status: 'Pending' },
  { id: 'inv3', patientName: 'Charlie Brown', amount: 150, date: '2024-05-23', status: 'Paid' },
];
