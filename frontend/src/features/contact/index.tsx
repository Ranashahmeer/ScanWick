import { Mail } from "lucide-react";
import type { FormEvent } from "react";
import { Footer, Header, useScanwickChrome } from "@/features/landing/chrome";

const CONTACT_EMAIL = "contact@scanwick.com";

function ContactSection() {
  // No backend endpoint exists for this form yet — it used to just call
  // preventDefault() and silently discard whatever the user typed, with no
  // indication anything had gone wrong. Falls back to opening the user's
  // own mail client with the message pre-filled, so submitting actually
  // does something real instead of a silent no-op.
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const fullName = (form.elements.namedItem("fullName") as HTMLInputElement)?.value ?? "";
    const email = (form.elements.namedItem("email") as HTMLInputElement)?.value ?? "";
    const message = (form.elements.namedItem("message") as HTMLTextAreaElement)?.value ?? "";

    const subject = `Contact form message from ${fullName || "Scanwick website"}`;
    const body = `${message}\n\n—\n${fullName}\n${email}`;
    window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <section className="contact-section" aria-label="Contact Scanwick">
      <div className="contact-inner">
        <div className="contact-card">
          <div className="contact-copy">
            <span className="contact-eyebrow">Contact Us</span>
            <h1>
              Need help with
              <br />
              your data?
            </h1>
            <p>
              Our team is here to guide you, answer questions, and help you
              get the most out of your insights.
            </p>
            <a className="contact-email" href={`mailto:${CONTACT_EMAIL}`}>
              <Mail size={13} strokeWidth={2.4} />
              {CONTACT_EMAIL}
            </a>
          </div>

          <form className="contact-form" onSubmit={handleSubmit}>
            <label>
              Full Name
              <input
                type="text"
                name="fullName"
                placeholder="Enter your full name"
                required
              />
            </label>

            <label>
              Email Address
              <input
                type="email"
                name="email"
                placeholder="Enter your email address"
                required
              />
            </label>

            <label>
              Message
              <textarea
                name="message"
                placeholder="Leave a message"
                required
              />
            </label>

            <button type="submit" className="contact-submit">
              Submit
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}

export function ContactPage() {
  const { theme, toggleTheme } = useScanwickChrome();

  return (
    <main className={`scanwick-page ${theme === "light" ? "theme-light" : ""}`}>
      <Header theme={theme} onToggleTheme={toggleTheme} />

      <ContactSection />

      <Footer />
    </main>
  );
}
