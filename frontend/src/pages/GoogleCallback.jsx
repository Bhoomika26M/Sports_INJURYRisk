import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Landing page for the Google OAuth redirect.
 *
 * Google sends the browser here with `?code=...&state=...`. We POST those to the
 * backend, which verifies the state and exchanges the code for an application
 * token. This page is public (it runs before the user is authenticated) and
 * must not be wrapped in PublicRoute, or the post-login redirect would fire
 * before we finish.
 */
const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState('');
  const attempted = useRef(false); // guard against React 18 double-invoke

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const googleError = searchParams.get('error');

    if (googleError) {
      setError('Google sign-in was cancelled or denied.');
      return;
    }
    if (!code || !state) {
      setError('Missing authorization details from Google.');
      return;
    }

    (async () => {
      try {
        await loginWithGoogle(code, state);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Google sign-in failed.');
      }
    })();
  }, [searchParams, loginWithGoogle, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 text-center">
        {error ? (
          <>
            <h2 className="text-2xl font-bold text-gray-900">Sign-in failed</h2>
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" role="alert">
              {error}
            </div>
            <Link to="/login" className="text-blue-600 hover:text-blue-800 text-sm">
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto" />
            <p className="text-gray-600">Finishing Google sign-in...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default GoogleCallback;
