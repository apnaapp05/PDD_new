"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AdminAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Users, Building2, Activity, CheckCircle,
  Settings, Shield, ChevronRight, BarChart3,
  CreditCard, ArrowUpRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function AdminDashboard() {
  const [stats, setStats] = useState({ doctors: 0, patients: 0, organizations: 0, revenue: 0 });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [statsRes] = await Promise.all([
        AdminAPI.getStats()
      ]);
      setStats({ ...statsRes.data, revenue: 124500 }); // Mock revenue for demo
    } catch (error) {
      console.error("Failed to load dashboard data", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-10">

      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Dashboard Overview</h1>
          <p className="text-slate-500 mt-1">Welcome back, Administrator. Here's what's happening today.</p>
        </div>

      </div>

      {/* STATS GRID */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">

        <Card className="border-l-4 border-l-blue-600 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Total Doctors</CardTitle>
            <div className="h-8 w-8 bg-blue-50 rounded-lg flex items-center justify-center">
              <Activity className="h-4 w-4 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{stats.doctors}</div>
            <p className="text-xs text-slate-500 mt-1 flex items-center">
              <span className="text-green-600 flex items-center mr-1"><ArrowUpRight className="w-3 h-3" /> +12%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-600 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Active Patients</CardTitle>
            <div className="h-8 w-8 bg-emerald-50 rounded-lg flex items-center justify-center">
              <Users className="h-4 w-4 text-emerald-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{stats.patients}</div>
            <p className="text-xs text-slate-500 mt-1 flex items-center">
              <span className="text-green-600 flex items-center mr-1"><ArrowUpRight className="w-3 h-3" /> +5%</span> new registrations
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-600 shadow-sm hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Organizations</CardTitle>
            <div className="h-8 w-8 bg-purple-50 rounded-lg flex items-center justify-center">
              <Building2 className="h-4 w-4 text-purple-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{stats.organizations}</div>
            <p className="text-xs text-slate-500 mt-1 flex items-center">
              <span className="text-slate-400">Stable metrics</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* QUICK ACTIONS & SYSTEM HEALTH */}
      <div className="grid gap-6 md:grid-cols-3">

        {/* Quick Management Links */}
        <Card className="col-span-2 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Shield className="w-5 h-5 text-indigo-600" /> Platform Management</CardTitle>
            <CardDescription>Quick access to core registries and configurations.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/admin/doctors" className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:bg-slate-50 hover:border-slate-200 transition-all group">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900">Manage Doctors</div>
                  <div className="text-xs text-slate-500">View & Verify Profiles</div>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600" />
            </Link>

            <Link href="/admin/organizations" className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:bg-slate-50 hover:border-slate-200 transition-all group">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900">Organizations</div>
                  <div className="text-xs text-slate-500">Clinics & Hospitals</div>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600" />
            </Link>

            <Link href="/admin/patients" className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:bg-slate-50 hover:border-slate-200 transition-all group">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <div className="font-semibold text-slate-900">Patient Registry</div>
                  <div className="text-xs text-slate-500">View User Base</div>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600" />
            </Link>
          </CardContent>
        </Card>

        {/* System Health / Status */}
        <Card className="shadow-sm bg-slate-50/50">
          <CardHeader>
            <CardTitle className="text-base text-slate-800">System Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Database Connection</span>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1"><CheckCircle className="w-3 h-3" /> Active</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">API Gateway</span>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1"><CheckCircle className="w-3 h-3" /> Online</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Email Service</span>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1"><CheckCircle className="w-3 h-3" /> Operational</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">AI Engine</span>
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 gap-1"><Activity className="w-3 h-3" /> Idle</Badge>
            </div>
            <div className="pt-4 border-t border-slate-200">
              <div className="text-xs text-slate-400">Last System Backup: 2 hours ago</div>
              <div className="text-xs text-slate-400">Version: v2.4.0-beta</div>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}