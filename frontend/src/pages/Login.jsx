import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await login(username, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.error || 'Login failed. Please check your credentials.');
        }
    };

    return (
        <div style={{ maxWidth: '420px', margin: '4rem auto' }}>
            <Card className="card-glass">
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <h2>Welcome Back</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Log in to access your research projects</p>
                </div>
                
                {error && (
                    <div style={{ 
                        padding: '0.75rem', 
                        marginBottom: '1.5rem', 
                        background: 'rgba(239, 68, 68, 0.1)', 
                        border: '1px solid var(--danger)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--danger)',
                        fontSize: '0.875rem'
                    }}>
                        {error}
                    </div>
                )}
                
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <Input 
                        label="Username"
                        id="username"
                        type="text" 
                        placeholder="Enter your username" 
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                    />
                    <Input 
                        label="Password"
                        id="password"
                        type="password" 
                        placeholder="Enter your password" 
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    <Button type="submit" style={{ width: '100%', marginTop: '0.5rem', padding: '0.75rem' }}>
                        Sign In
                    </Button>
                </form>
                
                <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Don't have an account? <Link to="/register" style={{ color: 'var(--accent-primary)', fontWeight: '500' }}>Sign up</Link>
                </div>
            </Card>
        </div>
    );
};

export default Login;
