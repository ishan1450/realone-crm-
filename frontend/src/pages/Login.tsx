import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock, Mail, AlertCircle, ArrowRight, ShieldCheck, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/api';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ email, password });
      navigate('/dashboard');
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.data?.detail?.toLowerCase().includes('pending approval')) {
          navigate('/pending-approval');
          return;
        }
        if (err.data?.detail?.toLowerCase().includes('rejected')) {
          navigate('/rejected-account');
          return;
        }
        setError(err.message);
      } else {
        setError('Login failed. Please check your credentials.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const quickFill = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('Password123!');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-xl bg-blue-600 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-sm">
          RE
        </div>
        <h2 className="mt-4 text-2xl font-bold text-slate-900 tracking-tight">
          Apex Estates CRM
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Sign in to access your leads and assignment rotation
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-xl sm:px-10">
          {error && (
            <div className="mb-5 p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-3 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@realestate.com"
                  className="w-full pl-9 pr-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all disabled:opacity-50"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Logins */}
          <div className="mt-6 pt-6 border-t border-slate-100">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 text-center">
              Quick Fill Demo Accounts
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => quickFill('admin@realestate.com')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-left bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-slate-700 font-medium"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                <span className="truncate">Admin (Alex)</span>
              </button>
              <button
                type="button"
                onClick={() => quickFill('sarah.agent@realestate.com')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-left bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-slate-700 font-medium"
              >
                <User className="w-3.5 h-3.5 text-emerald-600" />
                <span className="truncate">Agent 1 (Sarah)</span>
              </button>
              <button
                type="button"
                onClick={() => quickFill('michael.agent@realestate.com')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-left bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-slate-700 font-medium"
              >
                <User className="w-3.5 h-3.5 text-emerald-600" />
                <span className="truncate">Agent 2 (Michael)</span>
              </button>
              <button
                type="button"
                onClick={() => quickFill('priya.agent@realestate.com')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-left bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded text-slate-700 font-medium"
              >
                <User className="w-3.5 h-3.5 text-emerald-600" />
                <span className="truncate">Agent 3 (Priya)</span>
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-xs text-slate-500">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-blue-600 hover:text-blue-700">
              Register here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
