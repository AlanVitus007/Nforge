import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import BackendTest from './pages/BackendTest';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetails from "./pages/ProjectDetails";
import PaperDetails from "./pages/PaperDetails";
import { AuthProvider, AuthContext } from './context/AuthContext';
import { useContext } from 'react';
import './App.css';

const Navigation = () => {
  const { user } = useContext(AuthContext);
  return (
    <nav style={{ marginBottom: '2rem' }}>
      <Link to="/" style={{ marginRight: '1rem' }}>Home</Link>
      {!user && <Link to="/login" style={{ marginRight: '1rem' }}>Login</Link>}
      {!user && <Link to="/register" style={{ marginRight: '1rem' }}>Register</Link>}
      {user && <Link to="/dashboard" style={{ marginRight: '1rem' }}>Dashboard</Link>}
      <Link to="/projects">Projects</Link>
      <Link to="/backend-test">Test Backend Connection</Link>
    </nav>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          <Navigation />

          <Routes>
            <Route path="/" element={
              <div>
                <h1>NForge Frontend</h1>
                <p>Welcome to NForge. The UI will be built in later phases.</p>
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
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
