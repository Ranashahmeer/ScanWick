import { Moon, Sun } from "lucide-react";
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/hooks/use-auth";
import facebookIcon from "@/assets/facebookIcon.svg";
import instaIcon from "@/assets/instaIcon.svg";
import linkedinIcon from "@/assets/linkedinIcon.svg";
import scanwickLogo from "@/assets/Logos/Full Scanwick Logo Light Green.svg";
import substackIcon from "@/assets/substackIcon.svg";
import tiktokIcon from "@/assets/tiktokIcon.svg";
import xIcon from "@/assets/xIcon.svg";

const socialLinks = [
  { label: "LinkedIn", href: "#linkedin", icon: linkedinIcon },
  { label: "Instagram", href: "https://www.instagram.com/scanwick5?igsh=aWNhNXZsdzBvNDNk", icon: instaIcon },
  { label: "Facebook", href: "https://www.facebook.com/share/1BxWPNoV6G/?mibextid=wwXIfr", icon: facebookIcon },
  { label: "TikTok", href: "https://vt.tiktok.com/ZSCsYSJAn/", icon: tiktokIcon },
  { label: "X", href: "https://x.com/scanwick68111?s=11", icon: xIcon },
  { label: "Substack newsletter", href: "https://open.substack.com/pub/scanwick", icon: substackIcon },
];

export const navLinks = ["Product", "Analyzers", "Pricing", "FAQ"];

export const footerColumns = [
  {
    title: "Legal",
    links: [
      ["Privacy Policy", "/privacy"],
      ["Terms of Service", "/terms"],
      ["Contact Us", "/contact"],
    ],
  },
  {
    title: "Company",
    links: [
      ["About Us", "#about"],
      ["Blog", "/blog"],
      ["How It Works", "#how-it-works"],
    ],
  },
  {
    title: "Resources",
    links: [
      ["FAQ", "#faq"],
      ["Guides", "#guides"],
      ["Support", "#support"],
    ],
  },
  {
    title: "Product",
    links: [
      ["Pricing", "#pricing"],
      ["Account", "/login"],
      ["E-Commerce Analyzer", "#analyzers"],
      ["Bank Statement Analyzer", "#analyzers"],
    ],
  },
];

export type ThemeName = "dark" | "light";

export type HeaderProps = {
  theme: ThemeName;
  onToggleTheme: () => void;
};

export function useScanwickChrome() {
  const [theme, setTheme] = useState<ThemeName>(
    () => (localStorage.getItem("scanwick-theme") as ThemeName | null) ?? "dark",
  );

  const toggleTheme = () => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("scanwick-theme", next);
      return next;
    });
  };

  return { theme, toggleTheme };
}

export function Header({ theme, onToggleTheme }: HeaderProps) {
  const isLight = theme === "light";
  const { status } = useAuth();
  const isAuthenticated = status === "authenticated";

  return (
    <header className="scanwick-header">
      <nav className="scanwick-nav" aria-label="Main navigation">
        <Link className="scanwick-logo-link" to="/" aria-label="Scanwick home">
          <img src={scanwickLogo} alt="Scanwick" className="scanwick-logo" />
        </Link>

        <div className="scanwick-nav-links">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${link.toLowerCase()}`}
              className="scanwick-nav-link"
            >
              {link}
            </a>
          ))}
        </div>

        <div className="scanwick-actions">
          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={isLight ? "Switch to dark theme" : "Switch to light theme"}
            aria-pressed={isLight}
          >
            {isLight ? <Moon size={15} strokeWidth={2.4} /> : <Sun size={15} strokeWidth={2.4} />}
          </button>
          {isAuthenticated ? (
            <Link to="/upload" className="scanwick-sign-in">
              Go to app
            </Link>
          ) : (
            <Link to="/login" className="scanwick-sign-in">
              Sign in
            </Link>
          )}
          <Link to="/upload" className="scanwick-upload">
            Upload CV - It's Free
          </Link>
        </div>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="scanwick-footer" id="contact">
      <div className="footer-inner">
        <div className="footer-grid">
          <div className="footer-panel footer-panel-cta">
            <div className="footer-mini-card">
              <span>
                Limited at $7.5k/mo and turn raw data into valuable insights in
                just three steps. No coding required to start.
              </span>
              <Link to="/upload">Get Started</Link>
            </div>
          </div>

          <div
            className="footer-panel footer-panel-social"
            aria-label="Social links"
          >
            {socialLinks.map((social) =>
              social.href.startsWith("#") ? (
                <a href={social.href} aria-label={social.label} key={social.label}>
                  <img src={social.icon} alt="" />
                </a>
              ) : (
                <a
                  href={social.href}
                  aria-label={social.label}
                  key={social.label}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <img src={social.icon} alt="" />
                </a>
              ),
            )}
          </div>

          {footerColumns.map((column, index) => (
            <nav
              className={`footer-panel footer-panel-links footer-panel-${index + 1}`}
              aria-label={`${column.title} links`}
              key={column.title}
            >
              <h3>{column.title}</h3>
              {column.links.map(([label, href]) =>
                href.startsWith("#") ? (
                  <a href={href} key={label}>
                    {label}
                  </a>
                ) : (
                  <Link to={href} key={label}>
                    {label}
                  </Link>
                ),
              )}
            </nav>
          ))}
        </div>
      </div>
    </footer>
  );
}
