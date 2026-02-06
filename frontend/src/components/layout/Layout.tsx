import { Outlet } from "react-router-dom";
import { Header } from "./Header";

export function Layout() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-[1200px] px-8 py-10">
        <Outlet />
      </main>
    </div>
  );
}
