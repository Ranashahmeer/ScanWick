const RADIUS = 84;
const STROKE = 16;
const CIRCUMFERENCE = Math.PI * RADIUS;

function bandForScore(score: number) {
  if (score <= 30) return { label: "Low risk", color: "#7fc7a3" };
  if (score <= 80) return { label: "Moderate risk", color: "#f0b060" };
  return { label: "High risk", color: "#f06060" };
}

export function RiskGauge({ score }: { score: number }) {
  const band = bandForScore(score);
  const progress = Math.min(Math.max(score, 0), 100) / 100;
  const dashOffset = CIRCUMFERENCE * (1 - progress);
  const size = (RADIUS + STROKE) * 2;

  return (
    <div className="fi-gauge-wrap">
      <svg width={size} height={size / 2 + STROKE / 2} viewBox={`0 0 ${size} ${size / 2 + STROKE / 2}`}>
        <path
          d={`M ${STROKE / 2} ${size / 2} A ${RADIUS} ${RADIUS} 0 0 1 ${size - STROKE / 2} ${size / 2}`}
          fill="none"
          stroke="rgba(148, 163, 184, 0.18)"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />
        <path
          d={`M ${STROKE / 2} ${size / 2} A ${RADIUS} ${RADIUS} 0 0 1 ${size - STROKE / 2} ${size / 2}`}
          fill="none"
          stroke={band.color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
        />
      </svg>

      <div className="fi-gauge-value">
        <strong>{score}</strong>
        <span>/ 100</span>
      </div>

      <span className="fi-gauge-band" style={{ color: band.color, background: `${band.color}26` }}>
        {band.label}
      </span>

      <div className="fi-gauge-scale">
        <span className="fi-gauge-scale-item">
          <span className="fi-gauge-scale-dot" style={{ background: "#7fc7a3" }} />
          0–30 Low
        </span>
        <span className="fi-gauge-scale-item">
          <span className="fi-gauge-scale-dot" style={{ background: "#f0b060" }} />
          31–80 Moderate
        </span>
        <span className="fi-gauge-scale-item">
          <span className="fi-gauge-scale-dot" style={{ background: "#f06060" }} />
          81–100 High
        </span>
      </div>
    </div>
  );
}
