// src/pages/SignUp/components/signup.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { signupUser, googleAuth } from '../../../api';
import { User, Mail, Lock, AlertCircle, UserPlus } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';

export default function SignupComponent() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) return setError('Passwords do not match');
    setLoading(true);
    setError('');
    try {
      const result = await signupUser({
        full_name: fullName,
        email,
        password
      });
      if (result.access_token) {
        login(result.user, result.access_token);
        navigate('/');
      }
    } catch (err) {
      setError(err.message || 'Signup failed.');
    } finally {
      setLoading(false);
    }
  };

  const googleLogin = useGoogleLogin({
    flow: 'implicit',
    onSuccess: async (response) => {
      try {
        const result = await googleAuth({ credential: response.access_token });
        if (result.access_token) {
          login(result.user, result.access_token);
          navigate('/');
        }
      } catch {
        setError('Google signup failed.');
      }
    },
    onError: () => setError('Google signup failed.'),
  });

  return (
    <div className="min-h-screen pt-24 flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">

        <div className="text-center mb-8">
          <div className="w-16 h-16 flex items-center justify-center bg-gradient-to-br from-blue-500 to-blue-700 rounded-full mx-auto shadow-lg">
            <UserPlus className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold mt-4">Create Account</h1>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 p-3 border rounded flex gap-2 text-sm text-red-700">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <Input icon={<User className="w-5 h-5" />} placeholder="Full Name" value={fullName} onChange={setFullName} disabled={loading} />
          <Input icon={<Mail className="w-5 h-5" />} placeholder="Email" type="email" value={email} onChange={setEmail} disabled={loading} />
          <Input icon={<Lock className="w-5 h-5" />} placeholder="Password" type="password" value={password} onChange={setPassword} disabled={loading} />
          <Input icon={<Lock className="w-5 h-5" />} placeholder="Confirm Password" type="password" value={confirmPassword} onChange={setConfirmPassword} disabled={loading} />

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 text-white bg-gradient-to-r from-blue-600 to-blue-800 rounded-lg font-semibold shadow hover:shadow-blue-500/50 transition disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="my-8 flex items-center">
          <div className="flex-grow border-t"></div>
          <span className="mx-4 text-sm text-gray-500">or sign up with</span>
          <div className="flex-grow border-t"></div>
        </div>

        <div className="flex justify-center">
          <div className="relative group">
            <div className="absolute -inset-1 bg-blue-500 blur opacity-0 group-hover:opacity-100 transition"></div>
            <button
              type="button"
              onClick={() => googleLogin()}
              disabled={loading}
              className="relative w-16 h-16 bg-white rounded-full shadow-xl flex items-center justify-center hover:shadow-blue-400/50 transition disabled:opacity-50"
            >
              <svg className="w-8 h-8" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-sm">
          Already have an account?{' '}
          <Link className="text-blue-600 font-semibold hover:underline" to="/login">Sign in</Link>
        </div>

      </div>
    </div>
  );
}

function Input({ icon, placeholder, value, onChange, type = 'text', disabled = false }) {
  return (
    <div className="relative">
      <div className="absolute left-3 top-3 text-gray-400">{icon}</div>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full pl-10 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        required
      />
    </div>
  );
}
