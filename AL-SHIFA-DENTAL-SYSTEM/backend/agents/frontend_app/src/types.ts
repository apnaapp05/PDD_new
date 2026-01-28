export enum Role {
  DOCTOR = 'DOCTOR',
  PATIENT = 'PATIENT'
}

export interface Hospital {
  id: string;
  name: string;
  address: string;
  image: string;
}

export interface Doctor {
  id: string;
  name: string;
  specialization: string;
  hospitalId: string;
  image: string;
  rating: number;
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Male' | 'Female' | 'Other';
  email: string;
  history: MedicalHistoryItem[];
}

export interface MedicalHistoryItem {
  id: string;
  date: string;
  procedure: string;
  doctorName: string;
  notes: string;
  status: 'Completed' | 'Pending' | 'Scheduled';
}

export interface Appointment {
  id: string;
  patientId: string;
  doctorId: string;
  hospitalId: string;
  date: string; // ISO string
  timeSlot: string;
  status: 'Confirmed' | 'Completed' | 'Cancelled';
  type: string;
}

export interface InventoryItem {
  id: string;
  name: string;
  stock: number;
  unit: string;
  minThreshold: number;
  category: string;
}

export interface Invoice {
  id: string;
  patientName: string;
  amount: number;
  date: string;
  status: 'Paid' | 'Pending';
}

// Context Types
export interface AppState {
  user: { role: Role; id: string; name: string; hospitalId?: string } | null;
  hospitals: Hospital[];
  doctors: Doctor[];
  patients: Patient[];
  appointments: Appointment[];
  inventory: InventoryItem[];
  invoices: Invoice[];
}

export interface AppContextType extends AppState {
  login: (role: Role, id: string) => void;
  logout: () => void;
  bookAppointment: (appt: Omit<Appointment, 'id' | 'status'>) => void;
  updateStock: (itemId: string, newStock: number) => void;
  addNoteToPatient: (patientId: string, note: MedicalHistoryItem) => void;
}
