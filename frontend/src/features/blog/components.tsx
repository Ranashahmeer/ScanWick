import { Clock, Cpu, ShoppingBag, Target, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import type { BlogPost, PostCategory } from "./posts";

export const categoryIcon: Record<PostCategory, typeof TrendingUp> = {
  Finance: TrendingUp,
  Sales: Target,
  Commerce: ShoppingBag,
  Platform: Cpu,
};

export const categoryTone: Record<PostCategory, string> = {
  Finance: "post-cover-finance",
  Sales: "post-cover-sales",
  Commerce: "post-cover-commerce",
  Platform: "post-cover-platform",
};

export function PostCover({
  category,
  image,
}: {
  category: PostCategory;
  image?: string;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const Icon = categoryIcon[category];

  if (image && !imageFailed) {
    return (
      <div className="post-cover post-cover-photo">
        <img src={image} alt="" loading="lazy" onError={() => setImageFailed(true)} />
      </div>
    );
  }

  return (
    <div className={`post-cover ${categoryTone[category]}`}>
      <Icon size={30} strokeWidth={1.6} />
    </div>
  );
}

export function PostCard({ post }: { post: BlogPost }) {
  return (
    <Link to="/blog/$slug" params={{ slug: post.slug }} className="post-card">
      <PostCover category={post.category} image={post.image} />
      <div className="post-card-body">
        <span className={`post-tag post-tag-${post.category.toLowerCase()}`}>
          {post.category}
        </span>
        <h3>{post.title}</h3>
        <p>{post.excerpt}</p>
        <div className="post-meta">
          <span className="post-author">{post.author}</span>
          <span>{post.date}</span>
          <span className="post-read-time">
            <Clock size={11} strokeWidth={2.4} />
            {post.readTime}
          </span>
        </div>
      </div>
    </Link>
  );
}
