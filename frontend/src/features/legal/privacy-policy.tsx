import { Link } from "@tanstack/react-router";
import { Footer, Header, useScanwickChrome } from "@/features/landing/chrome";

const tocSections = [
  { id: "who-we-are", number: 1, label: "Who We Are" },
  { id: "data-we-collect", number: 2, label: "Data We Collect" },
  { id: "why-we-collect", number: 3, label: "Why We Collect Your Data" },
  { id: "data-sharing", number: 4, label: "Who We Share Data With" },
  { id: "data-retention", number: 5, label: "Data Retention" },
  { id: "international-transfers", number: 6, label: "International Transfers" },
  { id: "your-rights", number: 7, label: "Your Rights" },
  { id: "regional-rights", number: 8, label: "Regional Rights" },
  { id: "cookies", number: 9, label: "Cookies & Tracking" },
  { id: "data-protection", number: 10, label: "How We Protect Data" },
  { id: "children", number: 11, label: "Children" },
  { id: "third-party-links", number: 12, label: "Third-Party Links" },
  { id: "policy-changes", number: 13, label: "Changes to This Policy" },
  { id: "contact-us", number: 14, label: "Contact Us" },
];

function SectionHeading({ number, children }: { number: number; children: string }) {
  return (
    <>
      <span className="legal-section-number">{String(number).padStart(2, "0")}</span>
      <h2>
        {number}. {children}
      </h2>
    </>
  );
}

function DataTable({ rows }: { rows: [string, string][] }) {
  return (
    <div className="legal-table">
      {rows.map(([label, value]) => (
        <div className="legal-table-row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </div>
  );
}

export function PrivacyPolicyPage() {
  const { theme, toggleTheme } = useScanwickChrome();

  return (
    <main className={`scanwick-page legal-page ${theme === "light" ? "theme-light" : ""}`}>
      <Header theme={theme} onToggleTheme={toggleTheme} />

      <section className="legal-hero">
        <div className="legal-inner">
          <nav className="legal-breadcrumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span>/</span>
            <span>Legal</span>
            <span>/</span>
            <span aria-current="page">Privacy Policy</span>
          </nav>

          <span className="legal-badge">
            <i />
            Legal · Data Protection
          </span>

          <h1>Privacy Policy</h1>

          <p className="legal-intro">
            This Privacy Policy explains what personal data we collect, why we
            collect it, how we use and protect it, and what rights you have over
            it. It applies to everyone who uses our website or Services,
            regardless of where you are located in the world.
          </p>

          <p className="legal-dates">
            Effective Date: <strong>10 July 2026</strong>
            <span className="legal-dates-divider" />
            Last Updated: <strong>10 July 2026</strong>
          </p>
        </div>
      </section>

      <section className="legal-body">
        <div className="legal-inner legal-layout">
          <aside className="legal-toc" aria-label="Table of contents">
            <span>On this page</span>
            <ol>
              {tocSections.map((section) => (
                <li key={section.id}>
                  <a href={`#${section.id}`}>
                    {section.number}. {section.label}
                  </a>
                </li>
              ))}
            </ol>
          </aside>

          <div className="legal-content">
            <p>
              Scanwick ("we," "our," or "us") is a data analytics and business
              intelligence company headquartered in Lagos, Nigeria, operating the
              platform at scanwick.com. We offer two products: Scanwick BI, a
              business intelligence platform for small and medium-sized
              enterprises, and Scanwick Research, a statistical analysis platform
              for students and academic researchers around the world.
            </p>
            <p>
              We have written this policy to be clear and readable. If you have
              questions after reading it, please contact us at{" "}
              <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a>.
            </p>
            <p className="legal-note">
              This Privacy Policy is issued in compliance with the Nigeria Data
              Protection Act 2023 (NDPA), the General Application and
              Implementation Directive 2025 (GAID) issued by the Nigeria Data
              Protection Commission (NDPC), and, where applicable, the EU General
              Data Protection Regulation (GDPR) and other regional data
              protection frameworks.
            </p>

            <section id="who-we-are">
              <SectionHeading number={1}>Who We Are (Data Controller)</SectionHeading>
              <p>
                Scanwick is the data controller for the personal data we collect
                and process in connection with our Services. This means we are
                responsible for deciding how and why your personal data is used.
              </p>
              <DataTable
                rows={[
                  ["Company", "Scanwick"],
                  ["Website", "scanwick.com"],
                  ["Location", "Lagos, Nigeria"],
                  ["Privacy Contact", "privacy@scanwick.com"],
                  ["Regulator", "Nigeria Data Protection Commission (NDPC) - ndpc.gov.ng"],
                ]}
              />
            </section>

            <section id="data-we-collect">
              <SectionHeading number={2}>What Personal Data We Collect</SectionHeading>
              <p>
                We only collect data that is necessary for a specific,
                legitimate purpose. Here is what we collect and how:
              </p>

              <h3>2.1 Data You Give Us</h3>
              <p>When you create an account, subscribe to a plan, or interact with us, you may provide:</p>
              <ul>
                <li>Your name and email address</li>
                <li>Your institution name, business name, industry, or country</li>
                <li>
                  Payment details, processed securely by our payment provider;
                  we never store your full card number
                </li>
                <li>Login credentials (your password is stored in encrypted form only)</li>
                <li>
                  Any data files, datasets, financial records, bank statements,
                  survey responses, or research data you upload to our platform
                  for analysis ("Customer Data")
                </li>
                <li>Messages you send us through support or contact forms</li>
              </ul>

              <h3>2.2 Data We Collect Automatically</h3>
              <p>When you visit our website or use our platform, we automatically collect:</p>
              <ul>
                <li>Your IP address and approximate location derived from it</li>
                <li>Browser type and version, operating system, and device type</li>
                <li>Pages you visit, features you use, and how long you spend on them</li>
                <li>Referring website and session information</li>
                <li>Error logs and technical diagnostics</li>
              </ul>
              <p>
                This data is collected using cookies and similar technologies.
                See Section 9 for details on how we handle cookies.
              </p>

              <h3>2.3 Data About Customer Data You Upload</h3>
              <p>
                Scanwick allow you to upload data files for processing. This
                data may include personal data about other people, for example,
                employee records in a business dataset, or survey respondents'
                answers in a research dataset.
              </p>
              <p>
                When you upload such data, you remain the data controller for
                that data. Scanwick acts only as a data processor, processing it
                solely to generate the outputs you request. We do not analyse,
                sell, share, or use your uploaded data for any other purpose,
                including training our systems.
              </p>
            </section>

            <section id="why-we-collect">
              <SectionHeading number={3}>Why We Collect Your Data (Purposes and Legal Bases)</SectionHeading>
              <p>
                We must have a lawful reason to process your personal data.
                Below is a clear breakdown of what we do with your data and the
                legal basis we rely on for each purpose:
              </p>
              <ul className="legal-purpose-list">
                <li>
                  <strong>To create and manage your account.</strong> Legal
                  basis: Performance of contract. We need this to provide the
                  Services you signed up for.
                </li>
                <li>
                  <strong>To process payments and manage your subscription or
                  pass.</strong> Legal basis: Performance of contract. We cannot
                  activate your plan without processing your payment.
                </li>
                <li>
                  <strong>To generate the analytical outputs you request.</strong>{" "}
                  Legal basis: Performance of contract. This is the core of what
                  Scanwick does.
                </li>
                <li>
                  <strong>
                    To send you important service communications (account
                    updates, security alerts, policy changes).
                  </strong>{" "}
                  Legal basis: Legitimate interests. These are not marketing
                  messages; they are necessary to keep you informed about your
                  account.
                </li>
                <li>
                  <strong>To send you marketing emails and product
                  announcements.</strong> Legal basis: Consent. We only send
                  these if you have opted in. You can unsubscribe at any time.
                </li>
                <li>
                  <strong>To monitor platform usage and improve our
                  products.</strong> Legal basis: Legitimate interests. We use
                  aggregated, de-identified data to understand how the platform
                  is used and where it can be improved.
                </li>
                <li>
                  <strong>To detect fraud, abuse, and security threats.</strong>{" "}
                  Legal basis: Legitimate interests and legal obligation.
                  Protecting the platform and our users is a core
                  responsibility.
                </li>
                <li>
                  <strong>To comply with legal and regulatory
                  obligations.</strong> Legal basis: Legal obligation. For
                  example, retaining financial records as required by Nigerian
                  tax law.
                </li>
              </ul>
            </section>

            <section id="data-sharing">
              <SectionHeading number={4}>Who We Share Your Data With</SectionHeading>
              <p>
                We do not sell your personal data. We do not rent it or trade
                it. We share it only in the following limited, necessary
                circumstances:
              </p>

              <h3>4.1 Service Providers (Data Processors)</h3>
              <p>
                We work with carefully selected third-party companies to help us
                operate our platform. These include cloud hosting providers,
                payment processors, email delivery services, and analytics
                tools. Each of these providers processes your data only on our
                instructions and under a written contract that prohibits them
                from using it for any other purpose.
              </p>

              <h3>4.2 Legal and Regulatory Disclosures</h3>
              <p>
                We may be required to disclose personal data to government
                authorities, regulatory bodies, law enforcement agencies, or
                courts where required by law or valid legal process. Where
                permitted by law, we will notify you before disclosing your
                data.
              </p>

              <h3>4.3 Protection of Rights and Safety</h3>
              <p>
                We may share data where we reasonably believe it is necessary to
                prevent fraud, protect the safety of a person, or enforce our
                Terms of Service.
              </p>

              <h3>4.4 Business Transfers</h3>
              <p>
                If Scanwick is involved in a merger, acquisition, or sale of
                assets, your personal data may be transferred as part of that
                transaction. We will give you notice before your data becomes
                subject to a different privacy policy, and you will have the
                opportunity to delete your account if you do not agree.
              </p>
            </section>

            <section id="data-retention">
              <SectionHeading number={5}>How Long We Keep Your Data</SectionHeading>
              <p>We keep your data only for as long as is genuinely necessary. Here is our general schedule:</p>
              <ul>
                <li>
                  <strong>Account and profile data:</strong> kept for the
                  duration of your account, and for up to 12 months after you
                  close it, solely to allow for account restoration if you
                  request to reopen it within that period, or for dispute
                  resolution. After 12 months, the account data is permanently
                  deleted.
                </li>
                <li>
                  <strong>Billing and transaction records:</strong> kept for a
                  minimum of 6 years, as required by Nigerian financial and tax
                  regulations
                </li>
                <li>
                  <strong>Customer Data uploaded for analysis:</strong> kept for
                  up to 90 days after your active plan or pass expires, then
                  permanently deleted. The 90-day retention period begins on the
                  day your pass expires. You may request earlier deletion at any
                  time by emailing{" "}
                  <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a>.
                </li>
                <li><strong>Usage and technical logs:</strong> kept for up to 12 months</li>
                <li><strong>Support communications:</strong> kept for up to 3 years</li>
              </ul>
              <p>
                When we no longer need data, we delete it securely or anonymise
                it so it can no longer be linked to you.
              </p>
              <p>
                Anonymised data from which you cannot be identified may be kept
                indefinitely for product improvement, security research, and
                analytical purposes.
              </p>
            </section>

            <section id="international-transfers">
              <SectionHeading number={6}>International Data Transfers</SectionHeading>
              <p>
                Scanwick is based in Nigeria and our primary data processing
                takes place here. However, some of our service providers, such
                as cloud hosting and email delivery platforms, may process data
                in other countries, including countries in the EU, UK, and the
                United States.
              </p>
              <p>
                Where we transfer personal data outside Nigeria, we ensure that
                the receiving country or organisation provides an adequate level
                of data protection, consistent with Part VIII of the Nigeria
                Data Protection Act 2023 and Schedule 5 of the GAID 2025.
                Safeguards we use include standard contractual clauses and
                transfers only to jurisdictions with recognised adequacy
                standards.
              </p>
              <p>
                For users in the European Economic Area (EEA) or United
                Kingdom, transfers of your personal data outside the EEA or UK
                are governed by the appropriate GDPR transfer mechanisms,
                including Standard Contractual Clauses where applicable.
              </p>
            </section>

            <section id="your-rights">
              <SectionHeading number={7}>Your Rights</SectionHeading>
              <p>
                You have meaningful rights over your personal data. These rights
                apply to all Scanwick users. Depending on where you are located,
                additional rights may also apply, see Section 8 for
                region-specific rights.
              </p>
              <ul className="legal-purpose-list">
                <li>
                  <strong>Right to Access:</strong> You can ask us to confirm
                  whether we hold data about you, and to receive a copy of it
                  along with information about how it is used.
                </li>
                <li>
                  <strong>Right to Correction:</strong> You can ask us to
                  correct any data we hold about you that is inaccurate or
                  incomplete.
                </li>
                <li>
                  <strong>Right to Deletion:</strong> You can ask us to delete
                  your personal data. We will do so where we are not required
                  by law to keep it.
                </li>
                <li>
                  <strong>Right to Restrict Processing:</strong> You can ask us
                  to pause how we use your data in certain situations, for
                  example while a dispute is being resolved.
                </li>
                <li>
                  <strong>Right to Data Portability:</strong> You can ask us to
                  provide your data in a structured, machine-readable format so
                  you can transfer it to another service.
                </li>
                <li>
                  <strong>Right to Object:</strong> You can object to us
                  processing your data where we rely on legitimate interests.
                  You can also opt out of direct marketing at any time, with no
                  justification required.
                </li>
                <li>
                  <strong>Right to Withdraw Consent:</strong> Where we rely on
                  your consent to process data (for example, for marketing
                  emails or non-essential cookies), you can withdraw that
                  consent at any time. Withdrawal does not affect the
                  lawfulness of processing that took place before you
                  withdrew.
                </li>
                <li>
                  <strong>Right to Complain:</strong> If you believe we have
                  handled your data unlawfully, you have the right to lodge a
                  complaint with the Nigeria Data Protection Commission (NDPC)
                  at ndpc.gov.ng or with the data protection authority in your
                  country of residence.
                </li>
              </ul>
              <p>
                To exercise any of these rights, email us at{" "}
                <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a>.
                We will acknowledge your request within 5 business days and
                respond fully within 30 days. If your request is complex, we
                may extend this by a further 30 days and will tell you why.
              </p>
            </section>

            <section id="regional-rights">
              <SectionHeading number={8}>Additional Rights for Users in Specific Regions</SectionHeading>

              <h3>8.1 Users in the European Economic Area (EEA) and United Kingdom</h3>
              <p>
                If you are located in the EEA or UK, the General Data Protection
                Regulation (GDPR) or UK GDPR applies to your personal data. In
                addition to the rights in Section 7, you have the right not to
                be subject to a decision based solely on automated processing
                that produces legal or similarly significant effects, and the
                right to lodge a complaint with your local supervisory
                authority (for example, the ICO in the UK or your national DPA
                in the EU).
              </p>
              <p>
                Our lawful bases for processing under the GDPR mirror those
                described in Section 3: contract performance, legal obligation,
                legitimate interests (with a balancing test applied), and
                consent.
              </p>

              <h3>8.2 Users in Other African Jurisdictions</h3>
              <p>
                Many African countries, including Ghana (Data Protection Act
                2012), Kenya (Data Protection Act 2019), South Africa (POPIA
                2020), and others, have their own data protection laws. Where
                those laws grant you additional rights beyond those described in
                this Policy, we will honour them. Contact us at{" "}
                <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a>{" "}
                and specify your jurisdiction so we can assist you
                appropriately.
              </p>

              <h3>8.3 All Other International Users</h3>
              <p>
                Regardless of where you are located, nothing in this Privacy
                Policy limits or removes any rights you have under the
                mandatory consumer protection or data protection laws of your
                country of residence.
              </p>
            </section>

            <section id="cookies">
              <SectionHeading number={9}>Cookies and Tracking</SectionHeading>
              <p>
                We use cookies and similar tracking technologies on our website
                and platform. In line with Article 19 of the GAID 2025, we ask
                for your consent before placing any non-essential cookie on
                your device.
              </p>
              <ul className="legal-purpose-list">
                <li>
                  <strong>Essential cookies:</strong> Required for the platform
                  to function. They handle login sessions, security, and core
                  features. These run without your consent because the
                  platform cannot work without them.
                </li>
                <li>
                  <strong>Analytics cookies:</strong> Help us understand how
                  users navigate the platform. We use this data in aggregate
                  and de-identified form. These require your consent.
                </li>
                <li>
                  <strong>Preference cookies:</strong> Remember your settings
                  across sessions. These require your consent.
                </li>
                <li>
                  <strong>Marketing cookies:</strong> Used only if you have
                  explicitly opted in to marketing communications.
                </li>
              </ul>
              <p>
                You can change your cookie preferences at any time through our
                cookie settings centre or your browser settings. Changing
                cookie preferences will not affect your ability to use core
                platform features.
              </p>
            </section>

            <section id="data-protection">
              <SectionHeading number={10}>How We Protect Your Data</SectionHeading>
              <p>
                We take data security seriously. The technical and
                organisational measures we have in place include:
              </p>
              <ul>
                <li>Encrypted data transmission using TLS/HTTPS on all connections</li>
                <li>Encryption of sensitive data at rest</li>
                <li>Role-based access controls so only authorised team members can access personal data</li>
                <li>Regular security reviews and vulnerability assessments</li>
                <li>Documented incident response procedures</li>
              </ul>
              <p>
                <strong>Data Breach Notification:</strong> If a data breach
                occurs that is likely to affect your rights, we will notify the
                Nigeria Data Protection Commission (NDPC) within 72 hours of
                becoming aware of it, as required by Section 40 of the NDPA
                2023. If the breach poses a high risk to your personal data, we
                will also notify you directly within 72 hours of confirming the
                breach.
              </p>
              <p>
                No system connected to the internet is completely immune to
                security risk. We encourage you to use a strong, unique
                password for your Scanwick account and to contact us
                immediately at{" "}
                <a href="mailto:support@scanwick.com">support@scanwick.com</a>{" "}
                if you suspect any unauthorised access.
              </p>
            </section>

            <section id="children">
              <SectionHeading number={11}>Children</SectionHeading>
              <p>
                Our Services are intended for users who are 18 years of age or
                older. We do not knowingly collect personal data from anyone
                under 18. If we discover that we have inadvertently collected
                data from a minor, we will delete it promptly. If you believe a
                minor's data has been submitted to our platform, please notify
                us at{" "}
                <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a>.
              </p>
            </section>

            <section id="third-party-links">
              <SectionHeading number={12}>Third-Party Links</SectionHeading>
              <p>
                Our platform may contain links to third-party websites or
                services. We are not responsible for the privacy practices of
                those third parties. We encourage you to read the privacy
                policy of any third-party service you use. A link on our
                platform does not constitute an endorsement.
              </p>
            </section>

            <section id="policy-changes">
              <SectionHeading number={13}>Changes to This Policy</SectionHeading>
              <p>
                We may update this Privacy Policy from time to time to reflect
                changes in our practices, our products, or applicable law. When
                we make material changes, we will:
              </p>
              <ul>
                <li>Update the "Last Updated" date at the top of this document</li>
                <li>Post a clear notice on our website for at least 30 days before the change takes effect</li>
                <li>
                  Send an email notification to all registered users where the
                  change materially affects how we process their data
                </li>
              </ul>
              <p>
                Continuing to use our Services after a revised Policy takes
                effect means you accept the changes. If you do not agree, you
                may close your account before the effective date.
              </p>
            </section>

            <section id="contact-us">
              <SectionHeading number={14}>How to Contact Us</SectionHeading>
              <p>
                We genuinely want to hear from you if you have any questions or
                concerns about this Policy or your data.
              </p>

              <dl className="legal-contact-list">
                <div>
                  <dt>Privacy Enquiries</dt>
                  <dd><a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a></dd>
                </div>
                <div>
                  <dt>General Support</dt>
                  <dd><a href="mailto:support@scanwick.com">support@scanwick.com</a></dd>
                </div>
                <div>
                  <dt>Website</dt>
                  <dd>scanwick.com</dd>
                </div>
                <div>
                  <dt>Address</dt>
                  <dd>Lagos, Nigeria</dd>
                </div>
              </dl>

              <p>
                If you are not satisfied with our response, you have the right
                to contact the Nigeria Data Protection Commission (NDPC) at
                ndpc.gov.ng, or your local data protection authority.
              </p>

              <h3>15. Data Processing Agreement</h3>
              <p>
                If you are a controller and upload personal data to our
                platform (for example, as a business using Scanwick BI or a
                researcher using Scanwick Research), the Scanwick Data
                Processing Agreement (available at scanwick.com/dpa) forms part
                of this Privacy Policy and our Terms of Service. It governs how
                Scanwick processes Customer Data on your behalf and supplements
                this Policy.
              </p>

              <p className="legal-copyright">© 2026 Scanwick. All rights reserved.</p>
            </section>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
