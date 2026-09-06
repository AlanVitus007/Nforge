import { useState, useEffect } from 'react';
import api from '../services/api';

const BackendTest = () => {
  const [status, setStatus] = useState('Checking backend...');
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await api.get('/health/');
        if (response.data.status === 'ok') {
          setStatus('Backend Connected');
        } else {
          setStatus('Backend Connection Failed');
          setError(JSON.stringify(response.data));
        }
      } catch (err) {
        setStatus('Backend Connection Failed');
        setError(err.message);
      }
    };

    checkHealth();
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Backend Connection Test</h1>
      <h2>Status: {status}</h2>
      {error && <p style={{ color: 'red' }}>Error details: {error}</p>}
    </div>
  );
};

export default BackendTest;
