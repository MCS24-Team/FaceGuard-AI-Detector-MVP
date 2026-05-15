import { useState } from "react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { signIn } from "@/api/client";
import GoogleAuthButton from "@/components/GoogleAuthButton";
import logo from "@/assets/logo.png";

export default function SignInPage({ onSignInSuccess }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const submittedEmail = String(formData.get("email") || "").trim();
    const submittedPassword = String(formData.get("password") || "");

    if (!submittedEmail || !submittedPassword) {
      setIsError(true);
      setMessage("Email and password are required.");
      return;
    }

    setMessage("");
    setIsError(false);
    setIsSubmitting(true);

    try {
      const response = await signIn({ email: submittedEmail, password: submittedPassword });
      setMessage(response.message || "Sign in successful.");
      onSignInSuccess?.();
      setEmail(submittedEmail);
      setPassword("");
      navigate("/", { replace: true });
    } catch (error) {
      setIsError(true);
      setMessage(error.message || "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSuccess = (response) => {
    setIsError(false);
    setMessage(response.message || "Google sign in successful.");
    onSignInSuccess?.();
    navigate("/", { replace: true });
  };

  const handleGoogleError = (error) => {
    setIsError(true);
    setMessage(error.message || "Unable to sign in with Google.");
  };

  return (
    <main className="page auth-page">
      <section className="auth-shell">
        <div className="auth-brand-panel">
          <img src={logo} alt="FaceGuard Logo" className="auth-brand-logo" />
          <p className="auth-brand-kicker">Account Login</p>
          <h1 className="auth-brand-title">Welcome back to FaceGuard</h1>
          <p className="auth-brand-copy">
            Sign in to continue your deepfake analysis workflow with model-driven detection and Grad-CAM explainability.
          </p>
          <div className="auth-brand-features">
            <p>Privacy-first image processing</p>
            <p>AI-assisted authenticity scoring</p>
            <p>Visual forensic heatmap analysis</p>
          </div>
        </div>

        <div className="auth-form-panel">
          <h2>Sign In</h2>
          <p className="auth-form-subtitle">Continue to your FaceGuard workspace.</p>

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
                placeholder="Enter your password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>

            <button className="primary-btn auth-submit-btn" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing In..." : "Sign In"}
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
            Need an account? <Link to="/signup">Create one now</Link>
          </p>
        </div>
      </section>
    </main>
  );
}

