import { useEffect, useMemo, useState } from "react";
import { fetchUserProfile } from "@/api/client";
import { USER_EMAIL_STORAGE_KEY } from "@/constants";
import useCountUp from "@/hooks/useCountUp";

const DISPLAY_TIME_ZONE = "Asia/Singapore";

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat("en", {
    timeZone: DISPLAY_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatShortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "-";
  return new Intl.DateTimeFormat("en", {
    timeZone: DISPLAY_TIME_ZONE,
    month: "short",
    day: "2-digit"
  }).format(date);
}

function StatCard({ label, value, helper, tone = "default" }) {
  return (
    <article className={`profile-stat-card profile-stat-${tone}`}>
      <p>{label}</p>
      <strong className="num">{value}</strong>
      {helper ? <span>{helper}</span> : null}
    </article>
  );
}

function ProfileAvatar({ initials }) {
  return (
    <div className="profile-avatar-placeholder" aria-hidden="true">
      <div className="profile-avatar-ring">
        <span>{initials || "FG"}</span>
      </div>
    </div>
  );
}

function RealFakeDonut({ realCount, fakeCount }) {
  const total = realCount + fakeCount;
  const fakePercent = total ? (fakeCount / total) * 100 : 0;
  const realPercent = total ? (realCount / total) * 100 : 0;
  const animatedFake = useCountUp(fakePercent, { duration: 800, decimals: 1 });
  const animatedReal = useCountUp(realPercent, { duration: 800, decimals: 1 });

  return (
    <section className="panel profile-card">
      <div className="profile-card-head">
        <p className="profile-kicker">Prediction Mix</p>
        <h3>Real vs Fake</h3>
      </div>
      <div className="donut-layout">
        <div
          className="profile-donut"
          style={{
            background: `conic-gradient(var(--red-400) 0 ${fakePercent}%, var(--green-400) ${fakePercent}% 100%)`
          }}
        >
          <div>
            <strong className="num">{total}</strong>
            <span>Total scans</span>
          </div>
        </div>
        <div className="donut-legend">
          <div>
            <span className="legend-dot legend-real" />
            <p>Real</p>
            <strong className="num">{realCount}</strong>
            <em>{animatedReal.toFixed(1)}%</em>
          </div>
          <div>
            <span className="legend-dot legend-fake" />
            <p>Fake</p>
            <strong className="num">{fakeCount}</strong>
            <em>{animatedFake.toFixed(1)}%</em>
          </div>
        </div>
      </div>
    </section>
  );
}

function RiskDistribution({ stats }) {
  const risks = [
    { key: "low", label: "Low Risk", count: stats.low_risk_count || 0, cls: "risk-low" },
    { key: "medium", label: "Medium Risk", count: stats.medium_risk_count || 0, cls: "risk-medium" },
    { key: "high", label: "High Risk", count: stats.high_risk_count || 0, cls: "risk-high" }
  ];
  const total = Math.max(1, risks.reduce((sum, item) => sum + item.count, 0));

  return (
    <section className="panel profile-card">
      <div className="profile-card-head">
        <p className="profile-kicker">Risk Distribution</p>
        <h3>Forgery Score Ranges</h3>
      </div>
      <div className="risk-list">
        {risks.map((item) => {
          const percent = (item.count / total) * 100;
          return (
            <div className="risk-row" key={item.key}>
              <div className="risk-row-top">
                <span>{item.label}</span>
                <strong className="num">{item.count}</strong>
              </div>
              <div className="risk-track">
                <div className={`risk-fill ${item.cls}`} style={{ width: `${percent}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ActivityChart({ points }) {
  const maxCount = Math.max(1, ...points.map((item) => item.count || 0));

  return (
    <section className="panel profile-card profile-activity-card">
      <div className="profile-card-head">
        <p className="profile-kicker">Activity</p>
        <h3>Recent Scan Activity</h3>
      </div>
      {points.length ? (
        <div className="activity-bars">
          {points.map((item) => (
            <div className="activity-bar-item" key={item.date}>
              <div className="activity-bar-wrap">
                <div
                  className="activity-bar-fill"
                  style={{ height: `${Math.max(10, (item.count / maxCount) * 100)}%` }}
                />
              </div>
              <strong className="num">{item.count}</strong>
              <span>{formatShortDate(item.date)}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="profile-empty">No scan activity has been recorded yet.</p>
      )}
    </section>
  );
}

function RecentHistory({ items }) {
  return (
    <section className="panel profile-card profile-history-card">
      <div className="profile-card-head">
        <p className="profile-kicker">History</p>
        <h3>Recent Analysis Results</h3>
      </div>
      {items.length ? (
        <div className="history-table">
          <div className="history-row history-row-head">
            <span>Date</span>
            <span>Result</span>
            <span>Forgery Score</span>
            <span>Risk</span>
          </div>
          {items.map((item) => (
            <div className="history-row" key={`${item.created_at}-${item.fake_probability}`}>
              <span>{formatDate(item.created_at)}</span>
              <strong className={item.label === "FAKE" ? "history-fake" : "history-real"}>
                {item.label}
              </strong>
              <span className="num">{(Number(item.fake_probability || 0) * 100).toFixed(1)}%</span>
              <span className={`risk-chip risk-chip-${item.risk_level || "low"}`}>
                {item.risk_level || "low"}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="profile-empty">Analyze an image to start building your private usage history.</p>
      )}
    </section>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const email = window.localStorage.getItem(USER_EMAIL_STORAGE_KEY);
    if (!email) {
      setError("No signed-in email was found. Please sign in again.");
      setLoading(false);
      return;
    }

    fetchUserProfile(email)
      .then((payload) => {
        setProfile(payload);
        setError("");
      })
      .catch((requestError) => {
        setError(requestError.message || "Unable to load profile.");
      })
      .finally(() => setLoading(false));
  }, []);

  const stats = profile?.stats || {};
  const totalScans = stats.total_scans || 0;
  const averageScore = Number(stats.average_forgery_score || 0);
  const animatedTotal = useCountUp(totalScans, { duration: 800, decimals: 0 });
  const animatedAverage = useCountUp(averageScore, { duration: 800, decimals: 1 });

  const initials = useMemo(() => {
    const source = profile?.name || profile?.email || "U";
    return source
      .split(/\s|@/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("");
  }, [profile]);

  if (loading) {
    return (
      <main className="page profile-page">
        <section className="panel profile-loading">
          <div className="analysis-spinner" />
          <p>Loading your profile analytics...</p>
        </section>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page profile-page">
        <p className="error-text">{error}</p>
      </main>
    );
  }

  return (
    <main className="page profile-page">
      <section className="panel profile-hero">
        <div className="profile-identity">
          <ProfileAvatar initials={initials} />
          <div>
            <p className="profile-kicker">User Profile</p>
            <h1>{profile.name || "FaceGuard User"}</h1>
            <p>{profile.email}</p>
            <div className="profile-meta-row">
              <span>{profile.auth_provider === "google" ? "Google sign-in" : "Email account"}</span>
              <span>Created {formatDate(profile.created_at)}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="profile-stat-grid">
        <StatCard label="Total scans" value={animatedTotal.toFixed(0)} helper="Images analyzed" tone="default" />
        <StatCard label="Real results" value={stats.real_count || 0} helper="Predicted authentic" tone="real" />
        <StatCard label="Fake results" value={stats.fake_count || 0} helper="Predicted suspicious" tone="fake" />
        <StatCard
          label="Average forgery score"
          value={`${animatedAverage.toFixed(1)}%`}
          helper="Across recent scans"
          tone="score"
        />
      </section>

      <section className="profile-grid">
        <RealFakeDonut realCount={stats.real_count || 0} fakeCount={stats.fake_count || 0} />
        <RiskDistribution stats={stats} />
        <ActivityChart points={profile.activity_by_day || []} />
        <section className="panel profile-card profile-privacy-card">
          <div className="profile-card-head">
            <p className="profile-kicker">Privacy</p>
            <h3>What We Store</h3>
          </div>
          <p>
            Uploaded images are processed in memory and are not stored permanently. Your profile stores
            analysis metadata only, such as result label, forgery score, model name, and timestamp.
          </p>
          <p className="profile-last-scan">
            Last scan: <strong>{formatDate(stats.last_analysis_at)}</strong>
          </p>
        </section>
      </section>

      <RecentHistory items={profile.recent_analyses || []} />
    </main>
  );
}
