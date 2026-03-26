import { Navigate, Route, Routes } from "react-router-dom";
import RunDetailPage from "./pages/RunDetailPage";
import RunsPage from "./pages/RunsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RunsPage />} />
      <Route path="/runs/:id" element={<RunDetailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
