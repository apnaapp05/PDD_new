"use client";
import { useEffect, useState } from "react";
import { AdminAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Building2, Activity, CheckCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function AdminDashboard() {
  const [stats, setStats] = useState({ doctors: 0, patients: 0, organizations: 0, revenue: 0 });
  const [pendingRequests, setPendingRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      // Fetch Stats and Pending Requests in parallel
      const [statsRes, pendingRes] = await Promise.all([
        AdminAPI.getStats(), // Assumes existing getStats endpoint
        AdminAPI.getPendingRequests()
      ]);
      setStats(statsRes.data);
      setPendingRequests(pendingRes.data);
    } catch (error) {
      console.error("Failed to load dashboard data", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApprove = async (id: number, type: string) => {
    try {
      await AdminAPI.approveAccount(id, type);
      fetchData(); // Refresh list after approval
    } catch (error) {
      alert("Failed to approve account");
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <h1 className="text-3xl font-bold text-slate-800">Admin Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Total Doctors</CardTitle>
            <Activity className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.doctors}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Total Patients</CardTitle>
            <Users className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.patients}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Organizations</CardTitle>
            <Building2 className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.organizations}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Pending Requests</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{pendingRequests.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals Section */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4 text-slate-800">Pending Approvals</h2>
        
        {loading ? (
          <p>Loading...</p>
        ) : pendingRequests.length === 0 ? (
          <div className="p-8 border rounded-lg bg-slate-50 text-center text-slate-500">
            No pending requests found.
          </div>
        ) : (
          <div className="grid gap-4">
            {pendingRequests.map((req) => (
              <Card key={`${req.type}-${req.id}`} className="flex items-center justify-between p-4">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-full ${req.type === 'doctor' ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'}`}>
                    {req.type === 'doctor' ? <Users className="h-5 w-5" /> : <Building2 className="h-5 w-5" />}
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800">{req.name}</h3>
                    <p className="text-sm text-slate-500">{req.type.toUpperCase()} • {req.email}</p>
                    <p className="text-xs text-slate-400 mt-1">{req.info}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                   <Button onClick={() => handleApprove(req.id, req.type)} size="sm" className="bg-green-600 hover:bg-green-700">
                     <CheckCircle className="h-4 w-4 mr-2" />
                     Approve
                   </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}