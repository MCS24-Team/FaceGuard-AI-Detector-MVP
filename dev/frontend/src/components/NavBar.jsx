import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import logo from "@/assets/logo.png";

const NAV_ITEMS = [
  { to: "/", label: "Home", end: true },
  { to: "/upload", label: "Detector", end: false },
  { to: "/guide", label: "Guide", end: false }
];

export default function NavBar({ onSignOut }) {
  const location = useLocation();
  const menuRef = useRef(null);
  const accountMenuRef = useRef(null);
  const itemRefs = useRef({});
  const [pill, setPill] = useState({ left: 0, width: 0, visible: false });
  const [scrolled, setScrolled] = useState(false);
  const [isAccountOpen, setIsAccountOpen] = useState(false);

  useLayoutEffect(() => {
    const activeItem = NAV_ITEMS.find((item) =>
      item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
    );
    const node = activeItem ? itemRefs.current[activeItem.to] : null;
    const menu = menuRef.current;
    if (!node || !menu) {
      setPill((p) => ({ ...p, visible: false }));
      return;
    }
    const menuRect = menu.getBoundingClientRect();
    const nodeRect = node.getBoundingClientRect();
    setPill({
      left: nodeRect.left - menuRect.left,
      width: nodeRect.width,
      visible: true
    });
  }, [location.pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!isAccountOpen) return undefined;

    const handlePointerDown = (event) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setIsAccountOpen(false);
      }
    };
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsAccountOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isAccountOpen]);

  const handleSignOutClick = () => {
    setIsAccountOpen(false);
    onSignOut?.();
  };

  return (
    <header className={scrolled ? "top-nav is-scrolled" : "top-nav"}>
      <Link to="/" className="brand" aria-label="FaceGuard home">
        <img src={logo} alt="FaceGuard" className="brand-mark" />
      </Link>

      <nav className="menu" ref={menuRef} data-has-pill={pill.visible ? "true" : "false"}>
        <span
          className="nav-pill"
          aria-hidden="true"
          style={{ left: pill.left, width: pill.width }}
        />
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            ref={(node) => {
              if (node) itemRefs.current[item.to] = node;
            }}
            className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="nav-account-menu" ref={accountMenuRef}>
        <button
          type="button"
          className={isAccountOpen ? "account-avatar-btn account-avatar-btn-open" : "account-avatar-btn"}
          aria-label="Open account menu"
          aria-haspopup="menu"
          aria-expanded={isAccountOpen}
          onClick={() => setIsAccountOpen((open) => !open)}
        >
          <span aria-hidden="true">FG</span>
        </button>

        {isAccountOpen ? (
          <div className="account-dropdown" role="menu">
            <NavLink
              to="/profile"
              role="menuitem"
              className="account-dropdown-item"
              onClick={() => setIsAccountOpen(false)}
            >
              Profile
            </NavLink>
            <button
              type="button"
              role="menuitem"
              className="account-dropdown-item account-dropdown-danger"
              onClick={handleSignOutClick}
            >
              Sign Out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
