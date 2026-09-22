import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import BackendTest from './pages/BackendTest';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetails from "./pages/ProjectDetails";
import PaperDetails from "./pages/PaperDetails";
import MultiPaperComparison from "./pages/MultiPaperComparison";
import ResearchWorkspace from "./pages/ResearchWorkspace";
import { useContext } from 'react';
import { AuthProvider, AuthContext } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import './App.css';

function HomeRoute() {
  const { user, loading } = useContext(AuthContext);
  if (loading) return null;
  return user ? <Dashboard /> : <Landing />;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<HomeRoute />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/backend-test" element={<BackendTest />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id" element={<ProjectDetails />} />
              <Route
                path="/projects/:projectId/compare"
                element={<MultiPaperComparison />}
              />
              <Route
                path="/projects/:projectId/research"
                element={<ResearchWorkspace />}
              />
              <Route
                path="/projects/:projectId/papers/:paperId"
                element={<PaperDetails />}
              />
            </Routes>
          </Layout>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
