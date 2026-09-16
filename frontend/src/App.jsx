import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import BackendTest from './pages/BackendTest';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetails from "./pages/ProjectDetails";
import PaperDetails from "./pages/PaperDetails";
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import './App.css';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={
                <div style={{ textAlign: 'center', padding: '4rem 0' }}>
                  <h1 style={{ fontSize: '3rem', marginBottom: '1rem', background: 'linear-gradient(to right, var(--accent-primary), var(--accent-secondary))', WebkitBackgroundClip: 'text', color: 'transparent' }}>
                    Forge Your Research
                  </h1>
                  <p style={{ fontSize: '1.25rem', maxWidth: '600px', margin: '0 auto', color: 'var(--text-secondary)' }}>
                    A modern platform to manage, analyze, and synthesize your academic papers and research projects.
                  </p>
                </div>
              } />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/backend-test" element={<BackendTest />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id" element={<ProjectDetails />} />
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
