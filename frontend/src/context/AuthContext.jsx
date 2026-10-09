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

    const login = async (usernameOrEmail, password) => {
        let payload;
        if (typeof usernameOrEmail === 'object' && usernameOrEmail !== null) {
            payload = usernameOrEmail;
        } else {
            payload = { username: usernameOrEmail, password };
        }
        const response = await api.post('/auth/login/', payload);
        localStorage.setItem('token', response.data.token);
        setUser(response.data.user);
        return response.data;
    };

    const register = async (dataOrUsername, email, password, firstName, lastName, confirmPassword) => {
        let payload;
        if (typeof dataOrUsername === 'object' && dataOrUsername !== null) {
            payload = dataOrUsername;
        } else {
            payload = {
                username: dataOrUsername,
                email,
                password,
                first_name: firstName,
                last_name: lastName,
                confirm_password: confirmPassword || password,
            };
        }
        const response = await api.post('/auth/register/', payload);
        return response.data;
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
