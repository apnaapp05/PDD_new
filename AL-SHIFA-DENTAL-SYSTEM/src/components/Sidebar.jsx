"use client";

import React, { useState, useEffect } from "react";
import RoleSwitcher from "./RoleSwitcher";
import RoleNavigation from "./RoleNavigation";
import { X, ShieldCheck, User, LogOut } from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { AuthAPI } from "@/lib/api";

export default function Sidebar({ isOpen, onClose }) {
  const router = useRouter();
  const pathname = usePathname();
  const [role, setRole] = useState(null);

  // 1. Fetch User Role when Sidebar opens (to send them to the right profile)
  useEffect(() => {
    if (isOpen) { 
      const fetchUser = async () => {
        try {
          const res = await AuthAPI.getMe();
          setRole(res.data.role);
        } catch (error) {
          console.error("Sidebar user fetch error", error);
        }
      };
      fetchUser();
    }
  }, [isOpen]);

  // 2. Profile Navigation Logic
  const handleProfileClick = () => {
    onClose(); // Close sidebar first
    
    if (role === 'doctor') router.push('/doctor/profile');
    else if (role === 'patient') router.push('/patient/profile');
    else if (role === 'organization') router.push('/organization/profile');
    else if (role === 'admin') router.push('/admin/dashboard');
    else {
      // Fallback: Guess based on URL or go to login
      if (pathname.includes('/doctor')) router.push('/doctor/profile');
      else router.push('/auth/login');
    }
  };

  // 3. Logout Logic
  const handleLogout = () => {
    localStorage.removeItem("token"); // Clear Auth Token
    router.push("/auth/login"); // Redirect to Login
    onClose();
  };

  // Prevent background scrolling when open
  useEffect(() => {
    if (isOpen) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "unset";
  }, [isOpen]);

  return (
    <>
      {/* BACKDROP OVERLAY 
         - 'pointer-events-none' when closed is CRITICAL. 
         It ensures clicks pass through to the Header/Page when the sidebar is hidden.
      */}
      <div 
        className={`fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* SIDEBAR PANEL */}
      <aside 
        className={`fixed top-0 left-0 z-50 h-full w-[85%] max-w-[320px] bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        
        {/* HEADER */}
        <div className="px-6 py-5 bg-gradient-to-r from-blue-600 to-blue-700 text-white flex items-center justify-between shadow-md">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-6 w-6 text-blue-200" />
            <div>
              <h2 className="text-lg font-bold leading-none">Al-Shifa</h2>
              <p className="text-[10px] text-blue-100 uppercase tracking-wider font-medium opacity-80 mt-1">
                Secure Portal
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 bg-white/10 hover:bg-white/20 rounded-full transition-colors">
            <X className="h-5 w-5 text-white" />
          </button>
        </div>

        {/* CONTENT */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <RoleSwitcher onItemClick={onClose} />
          <div>
            <p className="px-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Menu
            </p>
            <RoleNavigation onItemClick={onClose} />
          </div>
        </div>

        {/* FOOTER (Profile & Logout) */}
        <div className="p-4 bg-slate-50 border-t border-slate-100">
          <div className="space-y-2">
            
            {/* My Profile Button */}
            <button 
              onClick={handleProfileClick}
              className="flex items-center w-full px-4 py-3 text-sm font-medium text-slate-700 rounded-lg hover:bg-white hover:text-blue-600 hover:shadow-sm transition-all border border-transparent hover:border-slate-200"
            >
              <User className="h-5 w-5 mr-3 text-slate-400" />
              My Profile
            </button>

            {/* Logout Button */}
            <button 
              onClick={handleLogout}
              className="flex items-center w-full px-4 py-3 text-sm font-medium text-red-600 rounded-lg hover:bg-red-50 hover:shadow-sm transition-all border border-transparent hover:border-red-100"
            >
              <LogOut className="h-5 w-5 mr-3" />
              Logout
            </button>

          </div>
          <p className="mt-4 text-[10px] text-center text-slate-400">
            Powered by <span className="font-semibold text-slate-600">Al-Shifa v2.1</span>
          </p>
        </div>

      </aside>
    </>
  );
}