import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import About from "./pages/About";
import Convert from "./pages/Convert";
import Guide from "./pages/Guide";
import Home from "./pages/Home";
import SystemCheck from "./pages/SystemCheck";

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/convert" element={<Convert />} />
        <Route path="/system" element={<SystemCheck />} />
        <Route path="/about" element={<About />} />
        <Route path="/guide" element={<Guide />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
}
