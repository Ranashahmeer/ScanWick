import aiFinancialDecisionsImg from "@/assets/images/ai-financial-decisions.png";
import atRiskCustomersImg from "@/assets/images/at-risk-customers.png";
import bankStatementLoanImg from "@/assets/images/bank-statement-loan.png";
import cashFlowAnalysisImg from "@/assets/images/cash-flow-analysis.png";
import cloudDataSafetyImg from "@/assets/images/cloud-data-safety.png";
import ecommerceLosingMoneyImg from "@/assets/images/ecommerce-losing-money.png";
import salesForecastWrongImg from "@/assets/images/sales-forecast-wrong.png";
import salesPipelineImg from "@/assets/images/sales-pipeline.png";
import stockOutsAdsImg from "@/assets/images/stock-outs-ads.png";

export type PostCategory = "Finance" | "Sales" | "Commerce" | "Platform";

export type BlogPost = {
  slug: string;
  title: string;
  excerpt: string;
  category: PostCategory;
  author: string;
  date: string;
  readTime: string;
  image: string;
};

export const blogPosts: BlogPost[] = [
  {
    slug: "why-your-ecommerce-business-is-losing-money",
    title: "Why Your E-Commerce Business Is Losing Money Even When Sales Are Up",
    excerpt:
      "You look at your sales dashboard and the numbers look good. Revenue is up. Orders are growing. But when you check your bank account, the money just isn't there...",
    category: "Commerce",
    author: "Tom Martins",
    date: "19 Jun 2026",
    readTime: "3 min read",
    image: ecommerceLosingMoneyImg,
  },
  {
    slug: "bank-statement-business-loan-nigeria",
    title: "How to Use Your Bank Statement to Get a Business Loan in Nigeria",
    excerpt:
      "If you have tried to get a loan from a Nigerian bank or microfinance institution, you know that your bank statement is the most important document in y...",
    category: "Finance",
    author: "Tom Martins",
    date: "16 Jun 2026",
    readTime: "3 min read",
    image: bankStatementLoanImg,
  },
  {
    slug: "sales-pipeline-problems-killing-revenue",
    title: "5 Sales Pipeline Problems That Are Killing Your Revenue (And How to Fix Them)",
    excerpt:
      "A sales pipeline is supposed to give you visibility and control. In practice, for most growing sales teams, it gives you a false sense of security. Deals sit in...",
    category: "Sales",
    author: "Tom Martins",
    date: "11 Jun 2026",
    readTime: "4 min read",
    image: salesPipelineImg,
  },
  {
    slug: "stock-outs-killing-ad-campaigns",
    title: "How to Stop Running Out of Stock and Killing Ad Campaigns at the Wrong Time",
    excerpt:
      "Running out of stock while your ads are still running is one of the most expensive mistakes an e-commerce business can make. You are paying to acquire customers...",
    category: "Commerce",
    author: "Tom Martins",
    date: "9 Jun 2026",
    readTime: "3 min read",
    image: stockOutsAdsImg,
  },
  {
    slug: "cash-flow-analysis-african-smes",
    title: "Cash Flow Analysis for African SMEs: What Your Bank Statement Is Really Telling You",
    excerpt:
      "Cash flow is the single most important indicator of a business's financial health - more important than profit on paper. A business...",
    category: "Finance",
    author: "Tom Martins",
    date: "5 Jun 2026",
    readTime: "3 min read",
    image: cashFlowAnalysisImg,
  },
  {
    slug: "nigerian-business-owners-using-ai",
    title: "How Nigerian Business Owners Are Using AI to Make Better Financial Decisions",
    excerpt:
      "Artificial intelligence in business used to mean enterprise software with six-figure implementation costs and a team of consultants. That is no longer true. A n...",
    category: "Platform",
    author: "Tom Martins",
    date: "29 May 2026",
    readTime: "3 min read",
    image: aiFinancialDecisionsImg,
  },
  {
    slug: "why-sales-forecast-always-wrong",
    title: "Why Your Sales Forecast Is Always Wrong - And How to Fix It",
    excerpt:
      "Ask any sales manager how accurate their last quarter's forecast was. Most will give you a number that is either embarrassingly optimistic or embarrassingly pes...",
    category: "Sales",
    author: "Tom Martins",
    date: "26 May 2026",
    readTime: "3 min read",
    image: salesForecastWrongImg,
  },
  {
    slug: "identify-win-back-at-risk-customers",
    title: "How to Identify and Win Back At-Risk Customers Before They Leave",
    excerpt:
      "Acquiring a new customer costs between five and seven times more than retaining an existing one. Every e-commerce business knows this in principle. Very few do anything about it systematically because identifying which customers are actually at risk of churning before they leave requires data analysis that most small businesses do not have time to do manually.",
    category: "Commerce",
    author: "Tom Martins",
    date: "2 Jun 2026",
    readTime: "3 min read",
    image: atRiskCustomersImg,
  },
  {
    slug: "ecommerce-product-level-data-analytics",
    title: "Why E-Commerce Businesses in Africa Need Product-Level Data Analytics",
    excerpt:
      "The African e-commerce market is one of the fastest-growing in the world. Nigeria's e-commerce sector alone is projected to exceed $10 billion in annual revenue...",
    category: "Commerce",
    author: "Tom Martins",
    date: "19 May 2026",
    readTime: "3 min read",
    image: ecommerceLosingMoneyImg,
  },
  {
    slug: "is-your-financial-data-safe-in-the-cloud",
    title: "Is Your Business Financial Data Safe in the Cloud? What to Look For in AI Analytics Tools",
    excerpt:
      "When you upload your bank statement, your sales data, or your order history to a cloud analytics platform, you are sharing some of your most sensitive...",
    category: "Platform",
    author: "Tom Martins",
    date: "22 May 2026",
    readTime: "3 min read",
    image: cloudDataSafetyImg,
  },
];
