import { useMemo, useState } from "react";
import { Footer, Header, useScanwickChrome } from "@/features/landing/chrome";
import { PostCard } from "./components";
import { type PostCategory, blogPosts } from "./posts";

const categories: (PostCategory | "All posts")[] = [
  "All posts",
  "Finance",
  "Sales",
  "Commerce",
  "Platform",
];

export function BlogPage() {
  const { theme, toggleTheme } = useScanwickChrome();
  const [activeCategory, setActiveCategory] = useState<PostCategory | "All posts">(
    "All posts",
  );

  const counts = useMemo(() => {
    const base: Record<string, number> = { "All posts": blogPosts.length };
    for (const post of blogPosts) {
      base[post.category] = (base[post.category] ?? 0) + 1;
    }
    return base;
  }, []);

  const visiblePosts = useMemo(
    () =>
      activeCategory === "All posts"
        ? blogPosts
        : blogPosts.filter((post) => post.category === activeCategory),
    [activeCategory],
  );

  return (
    <main className={`scanwick-page blog-page ${theme === "light" ? "theme-light" : ""}`}>
      <Header theme={theme} onToggleTheme={toggleTheme} />

      <section className="blog-hero">
        <div className="blog-inner">
          <span className="legal-badge">
            <i />
            Scanwick Insights
          </span>
          <h1>
            Practical ideas for African SMEs,
            <br />
            backed by real numbers
          </h1>
          <p>
            Breakdowns on margins, cash flow, sales pipelines, and the AI tools
            helping Nigerian business owners make sharper decisions.
          </p>
        </div>
      </section>

      <section className="blog-body">
        <div className="blog-inner">
          <div className="blog-filters" role="tablist" aria-label="Filter posts by category">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                role="tab"
                aria-selected={activeCategory === category}
                className={`blog-filter ${activeCategory === category ? "is-active" : ""}`}
                onClick={() => setActiveCategory(category)}
              >
                {category}
                <span>{counts[category] ?? 0}</span>
              </button>
            ))}
          </div>

          <div className="blog-grid">
            {visiblePosts.map((post) => (
              <PostCard post={post} key={post.slug} />
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
