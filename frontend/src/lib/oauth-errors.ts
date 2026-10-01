// Stable error codes the backend puts in /login?error=... after a failed Google sign-in.
const MESSAGES: Record<string, string> = {
  oauth_state_mismatch: "Google sign-in could not be verified (security check failed). Please try again.",
  oauth_denied: "Google sign-in was cancelled.",
  oauth_missing_code: "Google sign-in did not complete. Please try again.",
  oauth_code_invalid: "The Google sign-in expired or was rejected. Please try again.",
  oauth_provider_unavailable: "Google is unavailable right now. Please try again shortly.",
  oauth_userinfo_failed: "Google is unavailable right now. Please try again shortly.",
  oauth_email_unverified: "Your Google account email is not verified, so it cannot be used to sign in.",
  oauth_account_conflict: "This email is already linked to a different Google account.",
  oauth_account_disabled: "This account is deactivated. Contact your administrator.",
  oauth_session_failed: "Signed in with Google, but the session could not be started. Please try again.",
};

export function oauthErrorMessage(code: string | null): string {
  if (!code) return "";
  return MESSAGES[code] ?? "Google sign-in failed. Please try again.";
}
