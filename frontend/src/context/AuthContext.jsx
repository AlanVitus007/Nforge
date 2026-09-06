import React, { createContext, useState, useEffect } from 'react';
import api from '../services/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const response = await api.get('/auth/me/');
                    setUser(response.data);
                } catch (error) {
                    console.error("Failed to fetch user", error);
                    localStorage.removeItem('token');
                }
            }
            setLoading(false);
        };
        fetchUser();
    }, []);

    const login = async (username, password) => {
        const response = await api.post('/auth/login/', { username, password });
        localStorage.setItem('token', response.data.token);
        setUser(response.data.user);
    };

    const register = async (username, email, password) => {
        await api.post('/auth/register/', { username, email, password });
        // Automatically login after successful registration or let user login manually
        // We'll let them login manually for simplicity, or just login here:
        // await login(username, password);
    };

    const logout = async () => {
        try {
            await api.post('/auth/logout/');
        } catch (error) {
            console.error("Failed to logout on server", error);
        }
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};
