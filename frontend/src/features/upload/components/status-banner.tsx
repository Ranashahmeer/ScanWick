import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

export type BannerVariant = "success" | "warning" | "error";

const bannerIcon: Record<BannerVariant, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
};

export function StatusBanner({
  variant,
  heading,
  description,
  action,
}: {
  variant: BannerVariant;
  heading: string;
  description: string;
  action?: { label: string; onClick: () => void };
}) {
  const Icon = bannerIcon[variant];

  return (
    <div className={`dqr-banner dqr-banner-${variant}`}>
      <Icon size={16} strokeWidth={2.4} />
      <p>
        <strong>{heading}</strong> {description}
      </p>
      {action ? (
        <button type="button" className="dqr-banner-action" onClick={action.onClick}>
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
