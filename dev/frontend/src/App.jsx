import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "@/components/NavBar";
import HomePage from "@/pages/HomePage";
import GuidePage from "@/pages/GuidePage";
import SignInPage from "@/pages/SignInPage";
import SignUpPage from "@/pages/SignUpPage";
import UploadPage from "@/pages/UploadPage";
import { USER_EMAIL_STORAGE_KEY } from "@/constants";

const AUTH_STORAGE_KEY = "faceguard:isAuthenticated";

function ProtectedRoute({ isAuthenticated, children }) {
  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;
  }

  return children;
}

function PublicAuthRoute({ isAuthenticated, children }) {
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const storedAuth = window.localStorage.getItem(AUTH_STORAGE_KEY);
    setIsAuthenticated(storedAuth === "true");
  }, []);

  const handleSignInSuccess = () => {
    window.localStorage.setItem(AUTH_STORAGE_KEY, "true");
    setIsAuthenticated(true);
  };

  const handleSignOut = () => {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
    setIsAuthenticated(false);
  };

  return (
    <div className="app-shell">
      {isAuthenticated ? <NavBar onSignOut={handleSignOut} /> : null}
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/guide"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <GuidePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/upload"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <UploadPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/signin"
          element={
            <PublicAuthRoute isAuthenticated={isAuthenticated}>
              <SignInPage onSignInSuccess={handleSignInSuccess} />
            </PublicAuthRoute>
          }
        />
        <Route
          path="/signup"
          element={
            <PublicAuthRoute isAuthenticated={isAuthenticated}>
              <SignUpPage onSignInSuccess={handleSignInSuccess} />
            </PublicAuthRoute>
          }
        />
        <Route path="*" element={<Navigate to={isAuthenticated ? "/" : "/signin"} replace />} />
      </Routes>
    </div>
  );
}

