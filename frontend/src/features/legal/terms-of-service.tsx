import { Link } from "@tanstack/react-router";
import { Footer, Header, useScanwickChrome } from "@/features/landing/chrome";

const tocSections = [
  { id: "about", number: 1, label: "About Scanwick" },
  { id: "eligibility", number: 2, label: "Eligibility" },
  { id: "account", number: 3, label: "Your Account" },
  { id: "acceptable-use", number: 4, label: "Acceptable Use" },
  { id: "plans-and-pricing", number: 5, label: "Plans and Pricing" },
  { id: "your-data", number: 6, label: "Your Data and Content" },
  { id: "outputs", number: 7, label: "Outputs We Generate" },
  { id: "ip", number: 8, label: "Intellectual Property" },
  { id: "privacy", number: 9, label: "Privacy & Data Protection" },
  { id: "availability", number: 10, label: "Availability of Services" },
  { id: "warranties", number: 11, label: "Warranties & Disclaimers" },
  { id: "liability", number: 12, label: "Limitation of Liability" },
  { id: "indemnification", number: 13, label: "Indemnification" },
  { id: "term", number: 14, label: "Term and Termination" },
  { id: "changes", number: 15, label: "Changes to These Terms" },
  { id: "governing-law", number: 16, label: "Governing Law & Disputes" },
  { id: "general", number: 17, label: "General" },
  { id: "contact-us", number: 18, label: "Contact Us" },
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

export function TermsOfServicePage() {
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
            <span aria-current="page">Terms of Service</span>
          </nav>

          <span className="legal-badge">
            <i />
            Legal · Agreement
          </span>

          <h1>Terms of Service</h1>

          <p className="legal-intro">
            These Terms of Service ("Terms") are a legal agreement between you and
            Scanwick. They govern your use of our website at scanwick.com and all
            products and services we provide, including Scanwick BI (collectively,
            the "Services").
          </p>

          <p className="legal-dates">
            Effective Date: <strong>26 April 2026</strong>
            <span className="legal-dates-divider" />
            Last Updated: <strong>26 April 2026</strong>
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
              Please read these Terms carefully before you use our Services. By
              creating an account, activating a plan, or using any part of our
              platform, you confirm that you have read, understood, and agreed to
              be bound by these Terms.
            </p>
            <p>
              If you are using the Services on behalf of an organisation, you
              confirm that you have the authority to bind that organisation to
              these Terms. In that case, "you" refers to both you and that
              organisation.
            </p>

            <div className="legal-callout">
              <strong>! Please note</strong>
              <p>If you do not agree to these Terms, please do not use our Services.</p>
            </div>

            <section id="about">
              <SectionHeading number={1}>About Scanwick and Our Products</SectionHeading>
              <p>
                Scanwick is a technology company headquartered in Lagos, Nigeria.
                We build tools that help people make better decisions with data.
                We operate one product:
              </p>
              <p>
                <strong>Scanwick BI</strong> is a business intelligence platform
                for small and medium-sized enterprises. It provides analytical
                tools across multiple industry templates, offering descriptive,
                diagnostic, predictive, and prescriptive analytics on a monthly
                subscription basis.
              </p>
              <p>Scanwick BI is available through scanwick.com.</p>
            </section>

            <section id="eligibility">
              <SectionHeading number={2}>Eligibility</SectionHeading>
              <p>To use our Services you must:</p>
              <ul>
                <li>
                  Be at least 18 years of age, or the age of majority in your
                  country, whichever is higher
                </li>
                <li>Have the legal capacity to enter into a binding contract</li>
                <li>
                  Not be prohibited from using our Services under the laws of
                  your country or jurisdiction
                </li>
              </ul>
              <p>
                By using our Services, you confirm that you meet all of these
                requirements. We may ask you to verify your eligibility at any
                time.
              </p>
            </section>

            <section id="account">
              <SectionHeading number={3}>Your Account</SectionHeading>

              <h3>3.1 Creating an Account</h3>
              <p>
                Most features of our Services require a registered account. When
                you register, you agree to provide accurate, current, and
                complete information. You must update your information promptly
                if anything changes.
              </p>

              <h3>3.2 Keeping Your Account Secure</h3>
              <p>You are responsible for everything that happens under your account. This means:</p>
              <ul>
                <li>Choosing a strong, unique password and keeping it confidential</li>
                <li>Not sharing your login details with anyone else</li>
                <li>Logging out of shared or public devices after each session</li>
                <li>
                  Contacting us immediately at{" "}
                  <a href="mailto:support@scanwick.com">support@scanwick.com</a> if
                  you think your account has been accessed without your permission
                </li>
              </ul>
              <p>
                We are not responsible for any loss or harm resulting from
                unauthorised access to your account where that access was caused
                by your failure to keep your credentials secure.
              </p>

              <h3>3.3 One Account Per User</h3>
              <p>
                You may not create multiple accounts to circumvent restrictions,
                bypass a suspension, or gain access to features you would not
                otherwise have. We reserve the right to merge or close duplicate
                accounts.
              </p>
            </section>

            <section id="acceptable-use">
              <SectionHeading number={4}>Acceptable Use</SectionHeading>
              <p>
                We want Scanwick to be a platform that works well for everyone. By
                using our Services, you agree not to:
              </p>
              <ul>
                <li>
                  Use the Services for any unlawful purpose or in any way that
                  violates applicable law, including Nigeria's Cybercrimes
                  (Prohibition, Prevention, etc.) Act 2015 and the NDPA 2023
                </li>
                <li>Upload or process any data that you do not have the legal right to use or share</li>
                <li>
                  Copy, reproduce, resell, or sublicense any part of our platform
                  without our written permission
                </li>
                <li>Attempt to reverse engineer, decompile, or extract the source code of our software</li>
                <li>
                  Use automated tools, bots, or scrapers to access or extract
                  content from our platform without authorisation
                </li>
                <li>Upload or transmit malware, viruses, or any other harmful or malicious code</li>
                <li>Interfere with, disrupt, or overload our platform or the systems of other users</li>
                <li>
                  Attempt to access another user's account or any part of our
                  systems that you are not authorised to access
                </li>
                <li>Use the Services to produce or distribute misleading, fraudulent, or defamatory content</li>
                <li>Impersonate any person or entity or misrepresent your affiliation with any person or entity</li>
              </ul>
              <p>
                We may suspend or terminate your account immediately and without
                notice if we determine that you have violated any of the above.
                We will tell you why we took that action unless we are legally
                prevented from doing so.
              </p>
            </section>

            <section id="plans-and-pricing">
              <SectionHeading number={5}>Plans and Pricing</SectionHeading>

              <h3>5.1 Scanwick</h3>
              <p>Scanwick is available on the following monthly plans:</p>
              <ul>
                <li><strong>Free:</strong> No charge. Access to a limited feature set. No time limit.</li>
                <li><strong>Basic:</strong> $8.99 per month. Expanded access to analytics tools and industry templates.</li>
                <li>
                  <strong>Premium:</strong> $16.99 per month. Full access to all
                  Scanwick BI features, including advanced analytics, the complete
                  library of industry templates, and priority support.
                </li>
              </ul>
              <p>
                Scanwick subscriptions renew automatically each month. By
                subscribing, you authorise us to charge your payment method on
                your monthly renewal date. You will not receive a separate
                invoice for each renewal unless you request one.
              </p>

              <h3>5.2 Payments</h3>
              <p>
                All payments are processed by a third-party payment provider. We
                do not store your full card number on our servers. Fees are
                quoted in US Dollars (USD). You are responsible for any taxes,
                duties, or levies applicable in your country on top of the stated
                price.
              </p>

              <h3>5.3 Price Changes</h3>
              <p>
                We may change our plan pricing at any time. For active Scanwick
                subscribers, any price increase will take effect no earlier than
                the start of the next billing cycle following at least 30 days'
                written notice to your registered email address. If you do not
                agree with a price change, you may cancel your subscription
                before it takes effect. Continuing to use the Service after the
                new price takes effect means you accept the change.
              </p>

              <h3>5.4 Refunds</h3>
              <p>
                Because our Services are digital and access is granted
                immediately on payment, we do not offer refunds as a standard
                practice. This means:
              </p>
              <ul>
                <li>
                  <strong>Scanwick:</strong> We do not give pro-rata refunds if
                  you cancel mid-cycle. You will keep access until the end of the
                  period you have paid for.
                </li>
              </ul>
              <p>We do make exceptions in two situations:</p>
              <ul>
                <li>
                  a complete outrage of a core feature of the Service (as defined
                  in the application plan description) that continues for more
                  than 72 consecutive hours and that Scanwick fails to resolve
                  within 5 business days after receiving a detailed report from
                  you; or
                </li>
                <li>
                  where the law in your country gives you a right to a refund
                  that we cannot exclude by contract.
                </li>
              </ul>
              <p>
                If you believe you qualify for a refund, please email{" "}
                <a href="mailto:support@scanwick.com">support@scanwick.com</a>{" "}
                within 7 days of your payment date with a clear description of the
                issue. We will assess your request fairly and respond promptly.
              </p>

              <h3>5.5 Cancelling Scanwick</h3>
              <p>
                You can cancel your Scanwick BI subscription at any time through
                your account settings or by emailing{" "}
                <a href="mailto:support@scanwick.com">support@scanwick.com</a>.
                Cancellation takes effect at the end of your current billing
                cycle. You will not be charged again after cancellation, and you
                will retain access to your paid plan features until the cycle
                ends. We do not charge a cancellation fee.
              </p>
            </section>

            <section id="your-data">
              <SectionHeading number={6}>Your Data and Content</SectionHeading>

              <h3>6.1 You Own Your Data</h3>
              <p>
                You retain full ownership of all data, files, and content you
                upload to our Services ("Customer Data"). We do not claim any
                ownership over your Customer Data.
              </p>

              <h3>6.2 What We Are Allowed to Do With It</h3>
              <p>
                By uploading Customer Data, you grant Scanwick a limited,
                non-exclusive, royalty-free licence to access and process your
                data for the sole purpose of providing you with the Services,
                specifically, to generate the analytical outputs you request. We
                do not use your Customer Data to train our systems, build
                datasets for sale, create benchmarks using your identifiable
                data, or share it with third parties for their own purposes.
              </p>

              <h3>6.3 Your Responsibility for Your Data</h3>
              <p>You confirm that:</p>
              <ul>
                <li>You have the legal right to upload the Customer Data to our platform</li>
                <li>Your Customer Data does not infringe the intellectual property rights of any third party</li>
                <li>
                  Where your Customer Data contains personal data about other
                  people, you have a lawful basis for sharing it with us under
                  the NDPA 2023 or the data protection law applicable in your
                  jurisdiction
                </li>
                <li>Your Customer Data does not contain malware or any harmful code</li>
                <li>
                  You are solely responsible for maintaining backup copies of
                  your Customer Data. Scanwick does not guarantee that it can
                  restore lost or corrupted data, and you acknowledge that your
                  failure to keep backups may result in permanent data loss.
                </li>
              </ul>
              <p>
                You are responsible for the accuracy and completeness of your
                Customer Data. The outputs our platform generates are only as
                reliable as the data you put in. We are not responsible for
                decisions you make based on outputs derived from incorrect or
                incomplete data.
              </p>

              <h3>6.4 When You Are the Data Controller</h3>
              <p>
                If your Customer Data contains personal data about third parties,
                you are the data controller for that personal data under the
                NDPA 2023 and applicable law. Scanwick acts as your data
                processor. You are responsible for ensuring you have the legal
                authority to engage Scanwick to process that data on your behalf.
                Our Privacy Policy governs how we handle it.
              </p>
            </section>

            <section id="outputs">
              <SectionHeading number={7}>The Outputs We Generate</SectionHeading>

              <h3>7.1 What Outputs Are For</h3>
              <p>
                The reports, dashboards, charts, and statistical results
                generated by our Services ("Outputs") are produced by automated
                analytical processes based on the data and instructions you
                provide. They are intended to support your decision-making, not
                to replace professional judgment.
              </p>
              <p>
                Outputs from Scanwick BI are not financial advice, legal advice,
                investment advice, or accounting advice. You should verify
                material Outputs with a qualified professional before relying on
                them for significant decisions.
              </p>

              <h3>7.2 You Own Your Outputs</h3>
              <p>
                Subject to these Terms and full payment of applicable fees, the
                Outputs we generate from your Customer Data belong to you. You
                may use them for any lawful purpose.
              </p>
            </section>

            <section id="ip">
              <SectionHeading number={8}>Intellectual Property</SectionHeading>

              <h3>8.1 What Belongs to Scanwick</h3>
              <p>
                Everything that makes up the Scanwick platform, the software,
                code, algorithms, databases, design, brand, trademarks, and all
                related content, is owned by Scanwick or our licensors. Nothing
                in these Terms transfers any of that ownership to you.
              </p>
              <p>
                We grant you a limited, non-exclusive, non-transferable,
                revocable licence to use the Services during the term of your
                account or active plan, strictly in accordance with these Terms.
                You may not use our name, logo, or brand in any way without our
                prior written consent.
              </p>

              <h3>8.2 Feedback</h3>
              <p>
                If you send us feedback, suggestions, or ideas about how to
                improve our Services, you agree that we can use them freely
                without any obligation to pay you or give you credit. This does
                not affect your ownership of any Customer Data or Outputs.
              </p>
            </section>

            <section id="privacy">
              <SectionHeading number={9}>Privacy and Data Protection</SectionHeading>
              <p>
                How we collect and use your personal data is set out in our
                Privacy Policy at scanwick.com/privacy. The Privacy Policy is
                part of these Terms. By agreeing to these Terms, you also
                acknowledge our Privacy Policy.
              </p>
              <p>
                Scanwick processes personal data in compliance with the Nigeria
                Data Protection Act 2023 (NDPA) and the General Application and
                Implementation Directive 2025 (GAID). For users in the European
                Economic Area or United Kingdom, we also comply with the GDPR and
                UK GDPR respectively. For users in other jurisdictions, we
                respect applicable local data protection laws.
              </p>
            </section>

            <section id="availability">
              <SectionHeading number={10}>Availability of the Services</SectionHeading>
              <p>
                We aim to keep the Scanwick platform available and reliable. We
                will do our best to notify you in advance of planned maintenance
                that will cause significant downtime. However, we do not
                guarantee that the Services will be available at all times,
                error-free, or uninterrupted. Occasional downtime may occur due
                to maintenance, technical issues, or circumstances beyond our
                control.
              </p>
              <p>
                We may add, change, or remove features of the Services at any
                time. Where a material change would significantly reduce the
                functionality available under your paid plan, we will give you
                at least 30 days' notice and, if you choose not to continue,
                offer you a pro-rata refund for the unused portion of your paid
                period.
              </p>
            </section>

            <section id="warranties">
              <SectionHeading number={11}>Warranties and Disclaimers</SectionHeading>
              <p>
                We will deliver our Services with reasonable skill and care. We
                will take commercially reasonable steps to keep the platform
                secure and operational.
              </p>
              <p>
                Beyond that, the Services are provided on an "as is" and "as
                available" basis. We do not make any other warranties, whether
                express, implied, or statutory, including any implied warranties
                of merchantability, fitness for a particular purpose, accuracy,
                or non-infringement, to the extent permitted by applicable law.
              </p>
              <p>
                We do not warrant that our platform is completely free from bugs,
                errors, or interruptions, or that the Outputs it produces will be
                accurate, complete, or suitable for any specific purpose. We do
                not warrant that the platform is free from security
                vulnerabilities, though we take reasonable steps to prevent
                them.
              </p>
              <p>
                You may not use the Services in any situation where failure or
                inaccuracy of the Services could lead to death, personal injury,
                catastrophic property damage, or large-scale financial loss.
                Prohibited uses include, without limitation: medical diagnosis or
                treatment decisions, operation of nuclear facilities, air traffic
                control, emergency response systems, or any critical
                infrastructure. Scanwick disclaims all liability, and you assume
                all risk, for any such prohibited use.
              </p>
              <p className="legal-note">
                These disclaimers do not affect any statutory rights you have as
                a consumer under the law of your country that cannot be excluded
                by contract.
              </p>
            </section>

            <section id="liability">
              <SectionHeading number={12}>Limitation of Liability</SectionHeading>
              <p>
                We are not liable to you for any loss of profits, loss of
                revenue, loss of data, loss of goodwill, or any indirect,
                incidental, special, consequential, or punitive damages, however
                caused and whether based in contract, tort, negligence, statute,
                or otherwise, even if we have been told such losses were
                possible.
              </p>
              <p>
                Where we are liable to you for direct losses, our total liability
                for all claims arising from these Terms or your use of the
                Services, in any 12-month period, will not exceed the greater of:
                (a) the total fees you paid to Scanwick in the three months
                before the event giving rise to the claim; or (b) USD 50.00.
              </p>
              <p>
                These limitations reflect the pricing of our Services and a fair
                allocation of risk between us. They apply to the fullest extent
                permitted by law in your jurisdiction.
              </p>
              <p className="legal-note">
                Nothing in this section excludes or limits liability for death or
                personal injury caused by our negligence, for fraud, or for any
                other liability that cannot be excluded under the law of your
                country.
              </p>
            </section>

            <section id="indemnification">
              <SectionHeading number={13}>Indemnification</SectionHeading>
              <p>
                You agree to defend, indemnify, and hold harmless Scanwick and our
                officers, directors, employees, agents, and partners from any
                claim, demand, liability, damages, loss, or expense (including
                reasonable legal fees) brought by a third party and arising out
                of:
              </p>
              <ul>
                <li>Your use of the Services in breach of these Terms</li>
                <li>Customer Data you upload, including any claim that it infringes a third party's rights</li>
                <li>Your breach of any applicable law in connection with your use of the Services</li>
                <li>Any misrepresentation you make in these Terms</li>
              </ul>
            </section>

            <section id="term">
              <SectionHeading number={14}>Term and Termination</SectionHeading>

              <h3>14.1 Duration</h3>
              <p>
                These Terms apply from the moment you first access our Services
                and continue until your account is closed or these Terms are
                otherwise terminated.
              </p>

              <h3>14.2 Closing Your Account</h3>
              <p>
                You can close your account and end these Terms at any time by
                going to your account settings or emailing{" "}
                <a href="mailto:support@scanwick.com">support@scanwick.com</a>.
                Closing your account does not entitle you to a refund of prepaid
                fees, except as described in Section 5.5 or as required by law.
              </p>

              <h3>14.3 When We May Suspend or Terminate</h3>
              <p>We may suspend or close your account with or without prior notice in any of the following situations:</p>
              <ul>
                <li>You have breached these Terms or our acceptable use standards</li>
                <li>Your payment has not been received within 7 days of the due date</li>
                <li>We are required to do so by law, regulation, or a valid court or regulatory order</li>
                <li>Your use of the Services poses a risk to the security or integrity of our platform or other users</li>
              </ul>
              <p>
                Where possible, we will give you prior notice and an opportunity
                to remedy the issue before suspending or closing your account.
                Where immediate action is necessary to protect security or comply
                with law, we may act without prior notice and explain the reason
                afterwards.
              </p>

              <h3>14.4 What Happens When Your Account Closes</h3>
              <p>
                When your account is closed for any reason: your licence to use
                the Services ends immediately; we will retain your Customer Data
                for 30 days after account closure, after which it will be deleted
                from our active systems and backups, except where Scanwick is
                legally required to retain specific records (such as for tax or
                regulatory compliance). You may request earlier deletion by
                emailing{" "}
                <a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a> and
                Scanwick will comply within a reasonable time, not exceeding 14
                days. Any fees already accrued remain payable. The following
                sections of these Terms survive termination: 6.3, 8, 9, 11, 12,
                13, and 16.
              </p>
            </section>

            <section id="changes">
              <SectionHeading number={15}>Changes to These Terms</SectionHeading>
              <p>
                We may update these Terms from time to time. When we make
                material changes, we will update the "Last Updated" date, post a
                notice on our website for at least 30 days before the changes
                take effect, and send an email to your registered address.
              </p>
              <p>
                If you continue to use the Services after the revised Terms take
                effect, you have accepted the changes. If you do not agree with
                the revised Terms, you may close your account before the
                effective date.
              </p>
            </section>

            <section id="governing-law">
              <SectionHeading number={16}>Governing Law and Disputes</SectionHeading>

              <h3>16.1 Governing Law</h3>
              <p>
                These Terms are governed by and interpreted in accordance with
                the laws of the Federal Republic of Nigeria, including the NDPA
                2023 and the Cybercrimes (Prohibition, Prevention, etc.) Act
                2015. This applies regardless of where you are located.
              </p>
              <p>
                Nothing in this section removes any mandatory rights you have
                under the consumer protection or data protection laws of your own
                country. If a provision of these Terms conflicts with a mandatory
                right you have under local law, that local mandatory right takes
                precedence to the extent of the conflict.
              </p>

              <h3>16.2 Informal Resolution First</h3>
              <p>
                Before starting any formal legal proceedings, both parties agree
                to try to resolve the issue informally. If you have a dispute
                with us, please email{" "}
                <a href="mailto:legal@scanwick.com">legal@scanwick.com</a> with a
                clear description of the issue and what outcome you are seeking.
                We will respond within 15 business days and make a genuine effort
                to find a resolution.
              </p>

              <h3>16.3 Formal Proceedings</h3>
              <p>
                If we cannot resolve the dispute informally within 30 days,
                either party may pursue formal legal proceedings. Both parties
                submit to the jurisdiction of the courts of Nigeria for the
                resolution of any such dispute. This does not prevent either
                party from seeking urgent injunctive relief from a court of
                competent jurisdiction in any country to prevent irreparable
                harm.
              </p>
            </section>

            <section id="general">
              <SectionHeading number={17}>General</SectionHeading>
              <p>
                <strong>Entire Agreement:</strong> These Terms, together with our
                Privacy Policy, form the complete agreement between you and
                Scanwick regarding the Services and replace all prior
                discussions, representations, and agreements on the same
                subject.
              </p>
              <p>
                <strong>Severability:</strong> If any part of these Terms is
                found to be invalid or unenforceable by a court, that part will
                be modified to the minimum extent necessary to make it valid, and
                the rest of the Terms will continue in full force.
              </p>
              <p>
                <strong>No Waiver:</strong> If we do not enforce a provision of
                these Terms at any time, that does not mean we have waived the
                right to enforce it later.
              </p>
              <p>
                <strong>No Partnership:</strong> These Terms do not create any
                partnership, joint venture, agency, or employment relationship
                between you and Scanwick.
              </p>
              <p>
                <strong>Assignment:</strong> You may not transfer your rights or
                obligations under these Terms to anyone else without our written
                consent. We may transfer ours to an affiliate, successor, or
                acquirer, with reasonable notice to you.
              </p>
              <p>
                <strong>Force Majeure:</strong> We are not liable for any delay or
                failure to perform our obligations caused by circumstances beyond
                our reasonable control, such as natural disasters, power
                failures, internet outages, acts of government, or other events
                we could not have reasonably anticipated or prevented. We will
                notify you as soon as practicable and resume performance as soon
                as we are able.
              </p>
              <p>
                <strong>Language:</strong> These Terms are written in English. If
                they are translated into another language for convenience, the
                English version governs in the event of any conflict.
              </p>
              <p>
                <strong>Export Control and Sanctions:</strong> You represent and
                warrant that you are not located in, under the control of, or a
                national or resident of any country that is subject to
                comprehensive trade sanctions imposed by the United Nations, the
                United States, the European Union, or the Federal Republic of
                Nigeria (including but not limited to North Korea, Syria, Crimea,
                and Iran). You also represent that you are not listed on any
                sanctions-related restricted party list. You will not use the
                Services to export, re-export, or transfer any software or data
                in violation of applicable export control laws.
              </p>
            </section>

            <section id="contact-us">
              <SectionHeading number={18}>Contact Us</SectionHeading>
              <p>If you have any questions about these Terms or our Services, please reach out:</p>
              <dl className="legal-contact-list">
                <div>
                  <dt>Legal Enquiries</dt>
                  <dd><a href="mailto:legal@scanwick.com">legal@scanwick.com</a></dd>
                </div>
                <div>
                  <dt>General Support</dt>
                  <dd><a href="mailto:support@scanwick.com">support@scanwick.com</a></dd>
                </div>
                <div>
                  <dt>Privacy Matters</dt>
                  <dd><a href="mailto:privacy@scanwick.com">privacy@scanwick.com</a></dd>
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

              <p className="legal-copyright">© 2026 Scanwick. All rights reserved.</p>
            </section>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
