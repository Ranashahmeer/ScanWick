import type { ReactNode } from "react";

export type PostSection = {
  id: string;
  label: string;
};

export type FullPost = {
  deck: string;
  coverTag: string;
  sections: PostSection[];
  tags: string[];
  authorBio: string;
  relatedSlugs: string[];
  body: ReactNode;
};

export const fullPosts: Partial<Record<string, FullPost>> = {
  "bank-statement-business-loan-nigeria": {
    deck:
      "Most SME owners hand over 12 months of raw transactions and hope the loan officer draws the right conclusions. That's usually why strong businesses get rejected.",
    coverTag: "Loan readiness score",
    sections: [
      { id: "what-lenders-look-for", label: "What lenders look for" },
      { id: "problem-with-raw-statements", label: "The problem with raw statements" },
      { id: "how-scanwick-prepares", label: "How Scanwick prepares your statement" },
    ],
    tags: ["Business Loans", "Bank statements", "Nigeria SMEs"],
    authorBio:
      "Writes about SME finance and creditworthiness at Scanwick. Previously built loan-readiness scoring tools for Nigerian microfinance lenders.",
    relatedSlugs: [
      "cash-flow-analysis-african-smes",
      "nigerian-business-owners-using-ai",
      "identify-win-back-at-risk-customers",
    ],
    body: (
      <>
        <p>
          If you have tried to get a business loan from a Nigerian bank or
          microfinance institution, you know that your bank statement is the
          most important document in your application. Lenders use it to
          answer one question: can this business reliably repay what it
          borrows?
        </p>
        <p>
          The problem is that most SME owners submit their bank statements
          without any analysis. They hand over 12 months of raw transaction
          data and hope the loan officer draws the right conclusions. This is
          a mistake - and it is one of the most common reasons good
          businesses with strong cash flow get rejected.
        </p>

        <section id="what-lenders-look-for">
          <h2>What Lenders Actually Look for in Your Bank Statement</h2>
          <p>
            When a loan officer reviews your bank statement, they are not
            reading every transaction. They are looking for specific signals:
          </p>
          <ul>
            <li>
              <strong>Average Monthly Balance (ABM):</strong> the average of
              your daily closing balances over 3, 6, and 12 months. This is
              the single most important metric. A lender wants to see a
              healthy ABM relative to the loan amount you are requesting.
            </li>
            <li>
              <strong>Income stability:</strong> are your monthly inflows
              consistent or highly variable? A business that brings in NGN 2
              million every month is a safer bet than one that brings in NGN 6
              million one month and NGN 400,000 the next.
            </li>
            <li>
              <strong>Expense pattern:</strong> are your outflows predictable?
              Do you have recurring obligations that suggest stable
              operations, or erratic large withdrawals that suggest financial
              stress?
            </li>
            <li>
              <strong>Debt service:</strong> are there existing loan
              repayments visible in the statement, and how much of your
              income goes to servicing existing debt?
            </li>
            <li>
              <strong>Red flags:</strong> round-number transactions that
              suggest cash structuring, balance gaps that suggest missing
              months, large unexplained credits or debits.
            </li>
          </ul>

          <div className="legal-callout">
            <strong>ⓘ What lenders check first</strong>
            <p>
              Average Monthly Balance across 3, 6, and 12 months is the
              single most-watched number on your statement.
            </p>
          </div>
        </section>

        <section id="problem-with-raw-statements">
          <h2>The Problem With Raw Statements</h2>
          <p>
            A raw bank statement is hard to interpret. It is a list of
            transactions with reference numbers, cryptic narrations, and no
            summary. Even a loan officer who reviews hundreds of statements a
            year can miss important patterns if the data is not presented
            clearly.
          </p>
          <p>
            The businesses that get loans are not necessarily the ones with
            the strongest financials. They are the ones who present their
            financials most clearly. A business that walks in with a
            well-structured summary - ABM across three periods, income
            stability score, a clear breakdown of revenue sources and
            recurring expenses, and a professional written creditworthiness
            assessment - gets taken seriously.
          </p>
        </section>

        <section id="how-scanwick-prepares">
          <h2>How Scanwick Prepares Your Bank Statement for a Loan Application</h2>
          <p>
            Scanwick's Bank Statement Analyzer does the analytical work a
            financial analyst would do - automatically, in about 60 seconds.
          </p>
          <p>
            Upload your bank statement PDF or CSV from GTBank, Access Bank,
            Zenith, OPay, or any Nigerian bank. Scanwick calculates your ABM
            for 3, 6, and 12 months, computes a fraud risk score, classifies
            your income stability, and produces a Loan Readiness Score from 0
            to 100 with a full breakdown of what is driving the score.
          </p>
          <p>
            It then generates an AI Lender Brief - a formatted document with
            six sections: business overview, income summary, expense
            summary, risk assessment, creditworthiness assessment, and a
            recommendation paragraph. This document is written in the
            language lenders understand. You can download it as a PDF and
            attach it directly to your loan application.
          </p>
          <p>
            Scanwick also tells you how to improve your score. If your cash
            buffer is the weak point, it tells you exactly how much you need
            to reduce variable expenses to move your score into a better tier
            - and estimates how many points you would gain.
          </p>
          <p>
            For businesses in Nigeria using Mono, you can skip the upload
            entirely and connect your bank account directly. Your analysis
            runs automatically on live transaction data.
          </p>
          <p>
            Your bank statement already tells the story of your business.
            Scanwick helps you present it in a way that gets you the funding
            you deserve.
          </p>
        </section>
      </>
    ),
  },
};
