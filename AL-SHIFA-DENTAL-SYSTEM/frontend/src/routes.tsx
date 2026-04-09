
import React from 'react';
import { Routes, Route, Outlet } from 'react-router-dom';
import C0 from '@/app/layout';
import C1 from '@/app/page';
import C2 from '@/app/admin/layout';
import C3 from '@/app/admin/dashboard/page';
import C4 from '@/app/admin/doctors/page';
import C5 from '@/app/admin/organizations/page';
import C6 from '@/app/admin/patients/page';
import C7 from '@/app/auth/layout';
import C8 from '@/app/auth/admin/page';
import C9 from '@/app/auth/admin/dashboard/page';
import C10 from '@/app/auth/admin/doctors/page';
import C11 from '@/app/auth/admin/login/page';
import C12 from '@/app/auth/admin/organizations/page';
import C13 from '@/app/auth/doctor/forgot-password/page';
import C14 from '@/app/auth/doctor/login/page';
import C15 from '@/app/auth/doctor/signup/page';
import C16 from '@/app/auth/organization/forgot-password/page';
import C17 from '@/app/auth/organization/login/page';
import C18 from '@/app/auth/organization/signup/page';
import C19 from '@/app/auth/patient/appointments/new/page';
import C20 from '@/app/auth/patient/forgot-password/page';
import C21 from '@/app/auth/patient/login/page';
import C22 from '@/app/auth/patient/signup/page';
import C23 from '@/app/auth/role-selection/page';
import C24 from '@/app/auth/verify-otp/page';
import C25 from '@/app/doctor/layout';
import C26 from '@/app/doctor/ai-agents/page';
import C27 from '@/app/doctor/dashboard/page';
import C28 from '@/app/doctor/finance/page';
import C29 from '@/app/doctor/inventory/page';
import C30 from '@/app/doctor/patients/page';
import C31 from '@/app/doctor/patients/[id]/page';
import C32 from '@/app/doctor/profile/page';
import C33 from '@/app/doctor/schedule/page';
import C34 from '@/app/doctor/treatments/page';
import C35 from '@/app/organization/layout';
import C36 from '@/app/organization/appointments/page';
import C37 from '@/app/organization/dashboard/page';
import C38 from '@/app/organization/doctors/page';
import C39 from '@/app/organization/profile/page';
import C40 from '@/app/organization/treatments/page';
import C41 from '@/app/patient/layout';
import C42 from '@/app/patient/ai-chat/page';
import C43 from '@/app/patient/appointments/page';
import C44 from '@/app/patient/appointments/new/page';
import C45 from '@/app/patient/dashboard/page';
import C46 from '@/app/patient/emergency/page';
import C47 from '@/app/patient/invoices/page';
import C48 from '@/app/patient/profile/page';
import C49 from '@/app/patient/records/page';
import C50 from '@/app/shared/profile/page';


export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<C1 />} />
<Route path="admin" element={<C2><Outlet /></C2>}>
<Route path="dashboard">
<Route index element={<C3 />} />
</Route>
<Route path="doctors">
<Route index element={<C4 />} />
</Route>
<Route path="organizations">
<Route index element={<C5 />} />
</Route>
<Route path="patients">
<Route index element={<C6 />} />
</Route>
</Route>
<Route path="auth" element={<C7><Outlet /></C7>}>
<Route path="admin">
<Route index element={<C8 />} />
<Route path="dashboard">
<Route index element={<C9 />} />
</Route>
<Route path="doctors">
<Route index element={<C10 />} />
</Route>
<Route path="login">
<Route index element={<C11 />} />
</Route>
<Route path="organizations">
<Route index element={<C12 />} />
</Route>
</Route>
<Route path="doctor">
<Route path="forgot-password">
<Route index element={<C13 />} />
</Route>
<Route path="login">
<Route index element={<C14 />} />
</Route>
<Route path="signup">
<Route index element={<C15 />} />
</Route>
</Route>
<Route path="organization">
<Route path="forgot-password">
<Route index element={<C16 />} />
</Route>
<Route path="login">
<Route index element={<C17 />} />
</Route>
<Route path="signup">
<Route index element={<C18 />} />
</Route>
</Route>
<Route path="patient">
<Route path="appointments">
<Route path="new">
<Route index element={<C19 />} />
</Route>
</Route>
<Route path="forgot-password">
<Route index element={<C20 />} />
</Route>
<Route path="login">
<Route index element={<C21 />} />
</Route>
<Route path="signup">
<Route index element={<C22 />} />
</Route>
</Route>
<Route path="role-selection">
<Route index element={<C23 />} />
</Route>
<Route path="verify-otp">
<Route index element={<C24 />} />
</Route>
</Route>
<Route path="doctor" element={<C25><Outlet /></C25>}>
<Route path="ai-agents">
<Route index element={<C26 />} />
</Route>
<Route path="dashboard">
<Route index element={<C27 />} />
</Route>
<Route path="finance">
<Route index element={<C28 />} />
</Route>
<Route path="inventory">
<Route index element={<C29 />} />
</Route>
<Route path="patients">
<Route index element={<C30 />} />
<Route path="[id]">
<Route index element={<C31 />} />
</Route>
</Route>
<Route path="profile">
<Route index element={<C32 />} />
</Route>
<Route path="schedule">
<Route index element={<C33 />} />
</Route>
<Route path="treatments">
<Route index element={<C34 />} />
</Route>
</Route>
<Route path="organization" element={<C35><Outlet /></C35>}>
<Route path="appointments">
<Route index element={<C36 />} />
</Route>
<Route path="dashboard">
<Route index element={<C37 />} />
</Route>
<Route path="doctors">
<Route index element={<C38 />} />
</Route>
<Route path="profile">
<Route index element={<C39 />} />
</Route>
<Route path="treatments">
<Route index element={<C40 />} />
</Route>
</Route>
<Route path="patient" element={<C41><Outlet /></C41>}>
<Route path="ai-chat">
<Route index element={<C42 />} />
</Route>
<Route path="appointments">
<Route index element={<C43 />} />
<Route path="new">
<Route index element={<C44 />} />
</Route>
</Route>
<Route path="dashboard">
<Route index element={<C45 />} />
</Route>
<Route path="emergency">
<Route index element={<C46 />} />
</Route>
<Route path="invoices">
<Route index element={<C47 />} />
</Route>
<Route path="profile">
<Route index element={<C48 />} />
</Route>
<Route path="records">
<Route index element={<C49 />} />
</Route>
</Route>
<Route path="shared">
<Route path="profile">
<Route index element={<C50 />} />
</Route>
</Route>

    </Routes>
  );
}
