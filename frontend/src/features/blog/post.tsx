import { Link2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import linkedinIcon from "@/assets/linkedinIcon.svg";
import xIcon from "@/assets/xIcon.svg";
import { Footer, Header, useScanwickChrome } from "@/features/landing/chrome";
import { PostCard, PostCover } from "./components";
import { fullPosts } from "./full-posts";
import { blogPosts } from "./posts";

function useActiveSection(sectionIds: string[]) {
  const [activeId, setActiveId] = useState(sectionIds[0]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((entry) => entry.isIntersecting);
        if (visible) setActiveId(visible.target.id);
      },
      { rootMargin: "-96px 0px -70% 0px" },
    );

    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [sectionIds]);

  return activeId;
}

function FullPostView({ slug }: { slug: string }) {
  const post = blogPosts.find((candidate) => candidate.slug === slug);
  const fullPost = fullPosts[slug];

  const sectionIds = fullPost?.sections.map((section) => section.id) ?? [];
  const activeId = useActiveSection(sectionIds);

  if (!post || !fullPost) return null;

  const relatedPosts = fullPost.relatedSlugs
    .map((relatedSlug) => blogPosts.find((candidate) => candidate.slug === relatedSlug))
    .filter((candidate): candidate is NonNullable<typeof candidate> => Boolean(candidate));

  return (
    <>
      <section className="blog-post-hero">
        <div className="blog-inner">
          <span className={`post-tag post-tag-${post.category.toLowerCase()}`}>
            {post.category}
          </span>
          <h1>{post.title}</h1>
          <p className="blog-post-deck">{fullPost.deck}</p>

          <div className="blog-post-byline">
            <span className="blog-post-avatar" aria-hidden="true" />
            <div>
              <strong>{post.author}</strong>
              <span>
                Published {post.date} · {post.readTime}
              </span>
            </div>
            <div className="blog-post-share">
              <button type="button" aria-label="Copy link">
                <Link2 size={13} strokeWidth={2.2} />
              </button>
              <a href="#linkedin" aria-label="Share on LinkedIn">
                <img src={linkedinIcon} alt="" />
              </a>
              <a href="#x" aria-label="Share on X">
                <img src={xIcon} alt="" />
              </a>
            </div>
          </div>

          <div className="blog-post-cover">
            <PostCover category={post.category} image={post.image} />
            <span className="blog-post-cover-tag">{fullPost.coverTag}</span>
          </div>
        </div>
      </section>

      <section className="blog-body">
        <div className="blog-inner legal-layout">
          <aside className="legal-toc" aria-label="Table of contents">
            <span>On this page</span>
            <ol>
              {fullPost.sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    className={activeId === section.id ? "is-active" : ""}
                  >
                    {section.label}
                  </a>
                </li>
              ))}
            </ol>
          </aside>

          <div className="legal-content blog-post-content">
            {fullPost.body}

            <div className="blog-post-tags">
              {fullPost.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>

            <div className="blog-post-author-card">
              <span className="blog-post-avatar" aria-hidden="true" />
              <div>
                <strong>{post.author}</strong>
                <p>{fullPost.authorBio}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {relatedPosts.length ? (
        <section className="blog-body blog-related">
          <div className="blog-inner">
            <h2>Related reading</h2>
            <div className="blog-grid">
              {relatedPosts.map((relatedPost) => (
                <PostCard post={relatedPost} key={relatedPost.slug} />
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}

function ComingSoonView({ slug }: { slug: string }) {
  const post = blogPosts.find((candidate) => candidate.slug === slug);

  return (
    <>
      <section className="blog-hero blog-post-hero">
        <div className="blog-inner">
          <nav className="legal-breadcrumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span>/</span>
            <Link to="/blog">Insights</Link>
            <span>/</span>
            <span aria-current="page">{post?.title ?? "Post not found"}</span>
          </nav>

          <span className="legal-badge">
            <i />
            {post ? post.category : "Scanwick Insights"}
          </span>

          <h1>{post?.title ?? "This post isn't ready yet"}</h1>

          <p>
            {post
              ? "This article is coming soon. We're still writing it up - check back shortly."
              : "We couldn't find that post. It may have been moved or the link is out of date."}
          </p>
        </div>
      </section>

      <section className="blog-body">
        <div className="blog-inner">
          <Link to="/blog" className="blog-back-link">
            ← Back to Insights
          </Link>
        </div>
      </section>
    </>
  );
}

export function BlogPostPage() {
  const { theme } = useScanwickChrome();
  const { slug } = useParams({ from: "/blog/$slug" });
  const hasFullPost = Boolean(fullPosts[slug]);

  return (
    <main className={`scanwick-page blog-page ${theme === "light" ? "theme-light" : ""}`}>
      <Header />

      {hasFullPost ? <FullPostView slug={slug} /> : <ComingSoonView slug={slug} />}

      <Footer />
    </main>
  );
}
