import React, { useState } from 'react';
import { GoogleLogin, useGoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import { AlertCircle } from 'lucide-react';

export const GoogleAuthButton = ({ role = 'athlete', onSuccess, onError }) => {
  const { loginGoogle, loginOAuth } = useAuth();
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(false);

  // Fallback direct OAuth popup/redirect trigger via Google Identity Services
  const handleDirectGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        setLoading(true);
        setAuthError('');
        // Fetch verified userinfo from Google with the access token
        const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        });
        if (!res.ok) {
          throw new Error('Failed to retrieve user profile from Google.');
        }
        const profile = await res.json();
        await loginOAuth({
          provider: 'google',
          email: profile.email,
          full_name: profile.name || profile.given_name || profile.email.split('@')[0],
          role: role,
        });
        if (onSuccess) onSuccess();
      } catch (err) {
        const msg = err.response?.data?.detail || err.message || 'Google authentication failed';
        setAuthError(msg);
        if (onError) onError(msg);
      } finally {
        setLoading(false);
      }
    },
    onError: (err) => {
      setLoading(false);
      const msg = err?.error_description || 'Google sign-in was cancelled or encountered an issue.';
      setAuthError(msg);
      if (onError) onError(msg);
    },
  });

  const handleRealGoogleSuccess = async (credentialResponse) => {
    try {
      setLoading(true);
      setAuthError('');
      if (!credentialResponse?.credential) {
        throw new Error('No credential received from Google Identity Services.');
      }
      await loginGoogle(credentialResponse.credential, role);
      if (onSuccess) onSuccess();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Google authentication failed';
      setAuthError(msg);
      if (onError) onError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRealGoogleError = () => {
    // If the GIS iframe encounters an issue or was closed, trigger direct OAuth flow
    handleDirectGoogleLogin();
  };

  return (
    <div className="w-full space-y-3">
      {authError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          <span>{authError}</span>
        </div>
      )}

      {/* Official Google Identity Services Button */}
      <div className="w-full flex justify-center">
        <GoogleLogin
          onSuccess={handleRealGoogleSuccess}
          onError={handleRealGoogleError}
          useOneTap={false}
          theme="outline"
          size="large"
          text="continue_with"
          shape="rectangular"
          width="100%"
        />
      </div>

      {loading && (
        <div className="text-center text-xs text-slate-500 animate-pulse">
          Connecting to Google account...
        </div>
      )}
    </div>
  );
};
