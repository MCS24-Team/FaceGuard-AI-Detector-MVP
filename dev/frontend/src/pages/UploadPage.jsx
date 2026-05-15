import { useEffect, useMemo, useState } from "react";
import FileDropzone from "@/components/FileDropzone";
import BeforeAfterSlider from "@/components/BeforeAfterSlider";
import RadarChart from "@/components/RadarChart";
import useCountUp from "@/hooks/useCountUp";
import { analyzeImage, fetchHealth } from "@/api/client";
import { APP_CONFIG, USER_EMAIL_STORAGE_KEY } from "@/constants";

const LOADING_NARRATION = [
  "Stripping EXIF metadata…",
  "Normalizing image tensor…",
  "Extracting facial signals…",
  "Running detection model…",
  "Computing Grad-CAM overlay…",
  "Building detection report…"
];

function formatModelName(modelName = "") {
  const normalized = String(modelName).toLowerCase();
  if (!normalized) return "Unknown";
  if (normalized.includes("clip")) return "CLIP ViT-L/14";
  if (normalized.includes("vit")) return "ViT-B/16";
  if (normalized === "xception") return "Xception";
  if (normalized === "hybrid_score_fusion") return "ViT + Xception Fusion";
  if (normalized === "pg_fdd") return "PG-FDD";
  return modelName;
}

function severityLabel(severity = "normal") {
  if (severity === "high") return "High";
  if (severity === "warning") return "Warning";
  if (severity === "mild") return "Mild";
  return "Normal";
}

function DetectionReportPanel({ report }) {
  const score = Number(report?.overall_forgery_score || 0);
  const animatedScore = useCountUp(score, { duration: 900, decimals: 1 });

  if (!report) return null;

  const scoreTone =
    score >= 67 ? "report-score-risk" : score >= 34 ? "report-score-caution" : "report-score-safe";
  const breakdown = report.breakdown || [];

  return (
    <section className="panel report-panel">
      <div className="report-panel-header">
        <div className="report-panel-header-top">
          <div>
            <p className="report-kicker">Detection Report</p>
            <h3>{report.image_type || "Uploaded Image"}</h3>
          </div>
          <div className={`report-score ${scoreTone}`}>
            <span>Overall Forgery Score</span>
            <strong className="num">{animatedScore.toFixed(1)}%</strong>
          </div>
        </div>
        <p className="report-panel-lead">{report.summary}</p>
      </div>

      <div className="report-body">
        {breakdown.length ? (
          <div className="report-radar">
            <div className="report-radar-head">
              <p className="report-section-title" style={{ margin: 0 }}>
                Signal Radar
              </p>
              <div className="report-radar-legend">
                <span className="legend-image">This image</span>
                <span className="legend-baseline">Typical natural photo</span>
              </div>
            </div>
            <RadarChart items={breakdown} baseline={30} size={460} />
          </div>
        ) : null}

        <div className="report-breakdown">
          <p className="report-section-title">Detailed Breakdown</p>
          <div className="report-breakdown-grid">
            {breakdown.map((item) => (
              <article
                className={`report-item report-item-${item.severity || "normal"}`}
                key={item.title}
              >
                <div className="report-item-header">
                  <div>
                    <span className={`report-severity report-severity-${item.severity || "normal"}`}>
                      {severityLabel(item.severity)}
                    </span>
                    <h5>{item.title}</h5>
                  </div>
                  <strong className="num">{Number(item.score || 0).toFixed(1)}%</strong>
                </div>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function HeatmapPanel({ previewUrl, heatmapSrc }) {
  if (!heatmapSrc) return null;
  return (
    <section className="panel heatmap-panel-full">
      <div className="heatmap-panel-head">
        <div>
          <p className="report-kicker">Explainability</p>
          <h3>Grad-CAM Overlay</h3>
          <p className="panel-note-small">
            The heatmap highlights image regions that most influenced the model's decision.
            Drag the handle left or right to compare the original with the overlay.
          </p>
        </div>
      </div>
      <BeforeAfterSlider
        beforeSrc={previewUrl}
        afterSrc={heatmapSrc}
        beforeLabel="Original"
        afterLabel="Heatmap"
      />
    </section>
  );
}

function AnalysisMetrics({ confidence, probability, modelName }) {
  const animatedConfidence = useCountUp(confidence * 100, { duration: 900, decimals: 2 });
  const animatedProbability = useCountUp(probability * 100, { duration: 900, decimals: 2 });

  return (
    <div className="analysis-metrics">
      <div className="metric-tile">
        <p className="metric-label">Confidence</p>
        <p className="metric-value">{animatedConfidence.toFixed(2)}%</p>
      </div>
      <div className="metric-tile">
        <p className="metric-label">Probability</p>
        <p className="metric-value">{animatedProbability.toFixed(2)}%</p>
      </div>
      <div className="metric-tile">
        <p className="metric-label">Model</p>
        <p className="metric-value" style={{ fontSize: "0.95rem" }}>
          {formatModelName(modelName)}
        </p>
      </div>
    </div>
  );
}

function ScoreGauge({ aiScore }) {
  const animatedScore = useCountUp(aiScore * 100, { duration: 900, decimals: 2 });
  const toneClass =
    aiScore < 0.34 ? "score-fill-safe" : aiScore < 0.67 ? "score-fill-caution" : "score-fill-risk";

  return (
    <div className="score-gauge">
      <div className="score-gauge-row">
        <span>AI Score</span>
        <strong className="num">{animatedScore.toFixed(2)}%</strong>
      </div>
      <div className="score-track">
        <div
          className={`score-fill ${toneClass}`}
          style={{ width: `${Math.min(100, Math.max(0, aiScore * 100))}%` }}
        />
      </div>
    </div>
  );
}

function LoadingNarration() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((current) => (current + 1) % LOADING_NARRATION.length);
    }, 900);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="analysis-spinner" />
      <p className="loading-narration">{LOADING_NARRATION[index]}</p>
      <p className="loading-subtle">This usually takes a few seconds on CPU.</p>
    </>
  );
}

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [health, setHealth] = useState({ status: "checking", model_ready: false });

  useEffect(() => {
    fetchHealth()
      .then((payload) => setHealth({ status: "ok", ...payload }))
      .catch(() => setHealth({ status: "down", model_ready: false }));
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const healthMeta = useMemo(() => {
    if (health.status === "checking") return { label: "Backend: Checking…", cls: "status-checking" };
    if (health.status === "down") return { label: "Backend: Offline", cls: "status-down" };
    return {
      label: health.model_ready ? "Model: Ready" : "Model: Not Loaded",
      cls: ""
    };
  }, [health]);

  const panelToneClass = useMemo(() => {
    if (!result) return "";
    return result.label === "FAKE" ? "analysis-pane-fake" : "analysis-pane-real";
  }, [result]);

  const displayProbability = useMemo(() => {
    if (!result) return 0;
    return result.label === "FAKE" ? result.fake_probability : 1 - result.fake_probability;
  }, [result]);

  const aiScore = result?.fake_probability ?? 0;

  const verdictSummary = useMemo(() => {
    if (!result) return "";
    return result.label === "FAKE"
      ? "Likely AI-generated profile image"
      : "Likely real profile image";
  }, [result]);

  const clearSelection = () => {
    setSelectedFile(null);
    setResult(null);
    setError("");
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError("Please select an image file for analysis.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const storedEmail = window.localStorage.getItem(USER_EMAIL_STORAGE_KEY);
      const payload = await analyzeImage(selectedFile, storedEmail || "");
      setResult(payload);
    } catch (requestError) {
      setError(requestError.message || "An unexpected error occurred during analysis.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page upload-page">
      <section className="panel panel-upload">
        <div className="panel-header">
          <h2>Deepfake Detector</h2>
          <span className={`status-pill ${healthMeta.cls}`.trim()}>{healthMeta.label}</span>
        </div>

        <div className="upload-workspace">
          <div className="workspace-left">
            <FileDropzone
              onFileSelected={setSelectedFile}
              acceptedFormats={APP_CONFIG.allowedFormats}
              previewUrl={previewUrl}
              fileName={selectedFile?.name || ""}
              isAnalyzing={loading}
              onClear={clearSelection}
            />
            <button
              className="primary-btn analyze-btn"
              type="button"
              onClick={handleAnalyze}
              disabled={loading || !selectedFile}
            >
              {loading ? "Analyzing Image…" : "Analyze Image"}
            </button>
            <p className="panel-note-small">
              Max upload size: {APP_CONFIG.maxUploadMb} MB. Images are processed in memory and not retained.
            </p>
          </div>

          <aside
            className={`analysis-pane ${panelToneClass}`.trim()}
            aria-live="polite"
            aria-busy={loading}
          >
            <div className="analysis-pane-header">
              <h3>Analysis Result</h3>
              {result ? (
                <span
                  className={
                    result.label === "FAKE"
                      ? "classification-pill pill-fake"
                      : "classification-pill pill-real"
                  }
                >
                  {result.label}
                </span>
              ) : null}
            </div>

            {loading ? (
              <div className="analysis-state analysis-state-loading">
                <LoadingNarration />
              </div>
            ) : null}

            {!loading && error ? <p className="error-text">{error}</p> : null}

            {!loading && !error && !result ? (
              <div className="analysis-state">
                <p>
                  Upload an image and click <strong>Analyze Image</strong> to view the verdict,
                  forensic breakdown, and Grad-CAM explanation.
                </p>
              </div>
            ) : null}

            {!loading && !error && result ? (
              <div className="analysis-content">
                <div
                  className={
                    result.label === "FAKE"
                      ? "verdict-banner verdict-banner-fake"
                      : "verdict-banner verdict-banner-real"
                  }
                >
                  <p className="verdict-label">{result.label}</p>
                  <p className="verdict-summary">{verdictSummary}</p>
                </div>

                <AnalysisMetrics
                  confidence={result.confidence}
                  probability={displayProbability}
                  modelName={result.model_name}
                />

                <ScoreGauge aiScore={aiScore} />

                <p className="result-explanation">{result.explanation}</p>
              </div>
            ) : null}
          </aside>
        </div>
      </section>

      {!loading && !error && result?.heatmap_overlay ? (
        <HeatmapPanel previewUrl={previewUrl} heatmapSrc={result.heatmap_overlay} />
      ) : null}

      {!loading && !error && result?.report ? (
        <DetectionReportPanel report={result.report} />
      ) : null}
    </main>
  );
}
