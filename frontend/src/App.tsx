import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { StreamPage } from "./pages/StreamPage";
import { MomentDetailPage } from "./pages/MomentDetailPage";
import { SkillsPage } from "./pages/SkillsPage";
import { SourcesPage } from "./pages/SourcesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/stream" replace />} />
        <Route path="/stream" element={<StreamPage />} />
        <Route path="/moments/:momentId" element={<MomentDetailPage />} />
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/sources" element={<SourcesPage />} />
      </Route>
    </Routes>
  );
}
