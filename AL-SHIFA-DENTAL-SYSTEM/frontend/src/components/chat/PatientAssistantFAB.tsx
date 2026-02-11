'use client';
import { Button } from '@/components/ui/button';
import { Bot } from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';

export default function PatientAssistantFAB() {
  const router = useRouter();
  const pathname = usePathname();
  if (pathname === '/patient/ai-chat') return null;

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <Button 
        onClick={() => router.push('/patient/ai-chat')}
        className="h-14 w-14 rounded-full shadow-xl bg-blue-600 hover:bg-blue-700 transition-transform hover:scale-105 flex items-center justify-center"
      >
        <Bot className="h-8 w-8 text-white" />
      </Button>
    </div>
  );
}
