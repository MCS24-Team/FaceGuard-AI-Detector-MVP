import { useEffect, useRef, useState } from "react";
import { googleAuth } from "@/api/client";
import { GOOGLE_CLIENT_ID } from "@/constants";

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

function loadGoogleIdentityScript() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }

    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID);
    if (existingScript) {
      existingScript.addEventListener("load", resolve, { once: true });
      existingScript.addEventListener("error", reject, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = GOOGLE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

export default function GoogleAuthButton({ onSuccess, onError, label = "Continue with Google" }) {
  const buttonRef = useRef(null);
  const [isUnavailable, setIsUnavailable] = useState(!GOOGLE_CLIENT_ID);
  const [isSigningIn, setIsSigningIn] = useState(false);

  useEffect(() => {
    let isMounted = true;

    if (!GOOGLE_CLIENT_ID) {
      setIsUnavailable(true);
      return undefined;
    }

    loadGoogleIdentityScript()
      .then(() => {
        if (!isMounted || !buttonRef.current) {
          return;
        }

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            setIsSigningIn(true);
            try {
              const authResponse = await googleAuth(response.credential);
              onSuccess?.(authResponse);
            } catch (error) {
              onError?.(error);
              setIsSigningIn(false);
            }
          }
        });

        buttonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "filled_blue",
          size: "large",
          text: "continue_with",
          shape: "pill",
          width: buttonRef.current.offsetWidth || 320
        });
      })
      .catch(() => {
        if (isMounted) {
          setIsUnavailable(true);
          onError?.(new Error("Google sign-in could not be loaded."));
        }
      });

    return () => {
      isMounted = false;
    };
  }, [onError, onSuccess]);

  if (isUnavailable) {
    return (
      <button type="button" className="google-auth-fallback" disabled>
        {label}
      </button>
    );
  }

  return (
    <div className="google-auth-wrap">
      <p className="google-auth-kicker">Recommended sign-in option</p>
      <div
        ref={buttonRef}
        className={isSigningIn ? "google-auth-button google-auth-button-busy" : "google-auth-button"}
        aria-label={label}
      />
      {isSigningIn ? (
        <div className="google-auth-loading" role="status" aria-live="polite">
          <span className="google-auth-spinner" aria-hidden="true" />
          <span>Signing in with Google...</span>
        </div>
      ) : null}
    </div>
  );
}
