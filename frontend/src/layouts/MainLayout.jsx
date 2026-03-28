import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";
import FloatingSupport from "../components/FloatingSupport";

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <Navbar />
      
      <main className="flex-grow w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      
      <FloatingSupport />
    </div>
  );
}
