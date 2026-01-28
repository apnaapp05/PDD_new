import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { Role } from './types';

// CORRECTED IMPORTS: Pointing to 'components' folder instead of 'pages'
import { Auth } from './components/Auth';
import { PatientDashboard } from './components/PatientDashboard';
import { DoctorLayout } from './components/DoctorLayout';
import { DoctorDashboard } from './components/DoctorDashboard';
import { Schedule } from './components/Schedule';
import { Patients } from './components/Patients';
import { Inventory } from './components/Inventory';
import { Finance } from './components/Finance';

const AppRoutes: React.FC = () => {
  const { user } = useApp();

  // 1. If no user is logged in, show Auth (Login/Signup)
  if (!user) {
    return <Auth />;
  }

  // 2. If user is a Patient, show Patient Dashboard
  if (user.role === Role.PATIENT) {
    return <PatientDashboard />;
  }

  // 3. If user is a Doctor, show Doctor Layout with nested routes
  if (user.role === Role.DOCTOR) {
    return (
      <Routes>
        <Route path="/" element={<DoctorLayout />}>
          <Route index element={<Navigate to="dashboard" />} />
          <Route path="dashboard" element={<DoctorDashboard />} />
          <Route path="schedule" element={<Schedule />} />
          <Route path="patients" element={<Patients />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="finance" element={<Finance />} />
        </Route>
      </Routes>
    );
  }

  return <Auth />;
};

const App: React.FC = () => {
  return (
    <AppProvider>
      <HashRouter>
         <AppRoutes />
      </HashRouter>
    </AppProvider>
  );
};

export default App;