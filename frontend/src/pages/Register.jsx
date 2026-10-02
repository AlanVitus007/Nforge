import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';

const Register = () => {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { register, login } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await register(username, email, password);
            await login(username, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.username?.[0] || 'Registration failed. Please try again.');
        }
    };

    return (
        <div style={{ maxWidth: '420px', margin: '4rem auto' }}>
            <Card className="card-glass">
                <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                    <h2>Create an Account</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>Join NForge to start managing your research</p>
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
                        placeholder="Choose a username" 
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                    />
                    <Input 
                        label="Email Address"
                        id="email"
                        type="email" 
                        placeholder="name@example.com (Optional)" 
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    <Input 
                        label="Password"
                        id="password"
                        type="password" 
                        placeholder="Create a password" 
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    <Button type="submit" style={{ width: '100%', marginTop: '0.5rem', padding: '0.75rem' }}>
                        Create Account
                    </Button>
                </form>
                
                <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Already have an account? <Link to="/login" style={{ color: 'var(--accent-primary)', fontWeight: '500' }}>Log in</Link>
                </div>
            </Card>
        </div>
    );
};

export default Register;
