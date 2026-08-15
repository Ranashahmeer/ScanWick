import { Lock } from "lucide-react";

export interface DisabledFeatureItem {
  name: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function DisabledFeaturesList({ items }: { items: DisabledFeatureItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="dqr-disabled">
      <h2 className="dqr-disabled-title">Disabled features — and what unlocks them</h2>

      <div className="dqr-disabled-list">
        {items.map((item) => (
          <div className="dqr-disabled-row" key={item.name}>
            <div className="dqr-disabled-name">
              <Lock size={12} strokeWidth={2.4} />
              <strong>{item.name}</strong>
            </div>
            <p className="dqr-disabled-desc">
              {item.description}{" "}
              {item.actionLabel ? (
                <button type="button" className="dqr-disabled-action" onClick={item.onAction}>
                  {item.actionLabel}
                </button>
              ) : null}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
