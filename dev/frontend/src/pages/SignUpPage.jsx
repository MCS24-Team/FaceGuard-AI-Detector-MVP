import { useState } from "react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { signUp } from "@/api/client";
import { USER_EMAIL_STORAGE_KEY } from "@/constants";
import GoogleAuthButton from "@/components/GoogleAuthButton";
import logo from "@/assets/logo.png";

export default function SignUpPage({ onSignInSuccess }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const submittedEmail = String(formData.get("email") || "").trim();
    const submittedPassword = String(formData.get("password") || "");
    const submittedConfirmPassword = String(formData.get("confirmPassword") || "");

    if (!submittedEmail || !submittedPassword) {
      setIsError(true);
      setMessage("Email and password are required.");
      return;
    }

    if (submittedPassword.length < 6) {
      setIsError(true);
      setMessage("Password must be at least 6 characters.");
      return;
    }

    if (submittedPassword !== submittedConfirmPassword) {
      setIsError(true);
      setMessage("Passwords do not match.");
      return;
    }

    setMessage("");
    setIsError(false);
    setIsSubmitting(true);

    try {
      const response = await signUp({
        email: submittedEmail,
        password: submittedPassword
      });
      setMessage(response.message || "Account created.");
      setEmail(submittedEmail);
      setPassword("");
      setConfirmPassword("");
    } catch (error) {
      setIsError(true);
      setMessage(error.message || "Unable to sign up.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSuccess = (response) => {
    setIsError(false);
    setMessage(response.message || "Google account created and signed in.");
    onSignInSuccess?.();
    if (response?.email) {
      window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, response.email);
    }
    navigate("/", { replace: true });
  };

  const handleGoogleError = (error) => {
    setIsError(true);
    setMessage(error.message || "Unable to continue with Google.");
  };

  return (
    <main className="page auth-page">
      <section className="auth-shell">
        <div className="auth-brand-panel">
          <img src={logo} alt="FaceGuard Logo" className="auth-brand-logo" />
          <p className="auth-brand-kicker">Create Account</p>
          <h1 className="auth-brand-title">Start your FaceGuard workspace</h1>
          <p className="auth-brand-copy">
            Create your account to run profile image authenticity checks with reliable model-backed explainability.
          </p>
          <div className="auth-brand-features">
            <p>Fast detector workflow</p>
            <p>Confidence and AI score insights</p>
            <p>Grad-CAM visual interpretation</p>
          </div>
        </div>

        <div className="auth-form-panel">
          <h2>Create Account</h2>
          <p className="auth-form-subtitle">Set up your access to FaceGuard.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="name@example.com"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                placeholder="At least 6 characters"
                required
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>

            <div className="auth-field">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                placeholder="Repeat password"
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </div>

            <button className="primary-btn auth-submit-btn" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating Account..." : "Sign Up"}
            </button>
          </form>

          <div className="auth-divider">
            <span>or</span>
          </div>

          <GoogleAuthButton onSuccess={handleGoogleSuccess} onError={handleGoogleError} />

          {message ? (
            <p className={isError ? "auth-feedback auth-feedback-error" : "auth-feedback auth-feedback-success"}>
              {message}
            </p>
          ) : null}

          <p className="auth-switch">
            Already have an account? <Link to="/signin">Sign In</Link>
          </p>
        </div>
      </section>
    </main>
  );
}
