import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Card from '../components/Card';
import Button from '../components/Button';

const Dashboard = () => {
    const { user, loading } = useContext(AuthContext);
    const navigate = useNavigate();
    const [protectedMessage, setProtectedMessage] = useState('');

    useEffect(() => {
        if (!loading && !user) {
            navigate('/login');
        }
    }, [user, loading, navigate]);

    const testProtectedEndpoint = async () => {
        try {
            const response = await api.get('/auth/test/');
            setProtectedMessage(response.data.message);
        } catch (err) {
            setProtectedMessage('Failed to access protected endpoint.');
        }
    };

    if (loading) return <div style={{ textAlign: 'center', padding: '2rem' }}>Loading...</div>;
    if (!user) return null;

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Dashboard</h2>
            <Card className="card-glass" style={{ marginBottom: '2rem' }}>
                <h3 style={{ marginTop: 0 }}>Welcome back, {user.username}!</h3>
                <p style={{ color: 'var(--text-secondary)' }}>You are successfully logged in to NForge.</p>
            </Card>
            
            <Card>
                <h3 style={{ marginTop: 0 }}>Protected Endpoint Test</h3>
                <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                    Test your authentication token against the backend API.
                </p>
                <Button onClick={testProtectedEndpoint}>Test Endpoint</Button>
                {protectedMessage && (
                    <div style={{ 
                        marginTop: '1rem', 
                        padding: '1rem', 
                        background: 'var(--bg-tertiary)', 
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-color)'
                    }}>
                        <strong style={{ color: 'var(--accent-primary)' }}>Result:</strong> {protectedMessage}
                    </div>
                )}
            </Card>
        </div>
    );
};

export default Dashboard;
