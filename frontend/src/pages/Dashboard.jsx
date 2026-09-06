import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const Dashboard = () => {
    const { user, logout, loading } = useContext(AuthContext);
    const navigate = useNavigate();
    const [protectedMessage, setProtectedMessage] = useState('');

    useEffect(() => {
        if (!loading && !user) {
            navigate('/login');
        }
    }, [user, loading, navigate]);

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const testProtectedEndpoint = async () => {
        try {
            const response = await api.get('/auth/test/');
            setProtectedMessage(response.data.message);
        } catch (err) {
            setProtectedMessage('Failed to access protected endpoint.');
        }
    };

    if (loading) return <p>Loading...</p>;
    if (!user) return null;

    return (
        <div>
            <h2>Dashboard</h2>
            <p>Welcome back, {user.username}!</p>
            
            <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ccc' }}>
                <h3>Protected Endpoint Test</h3>
                <button onClick={testProtectedEndpoint}>Test Endpoint</button>
                {protectedMessage && <p style={{ marginTop: '1rem' }}><strong>Result:</strong> {protectedMessage}</p>}
            </div>

            <div style={{ marginTop: '2rem' }}>
                <button onClick={handleLogout} style={{ background: '#f44336', color: 'white', border: 'none', padding: '0.5rem 1rem', cursor: 'pointer' }}>
                    Logout
                </button>
            </div>
        </div>
    );
};

export default Dashboard;
