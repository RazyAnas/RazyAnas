"""
update_blogs.py
───────────────
Fetches the latest 5 Medium articles from @anasrazy and injects them
into README.md between the sentinel comment tags:

    <!-- BLOG-POST-LIST:START -->
    <!-- BLOG-POST-LIST:END -->
"""

import sys
import re
import feedparser
from dateutil import parser as date_parser
from datetime import timezone

MEDIUM_RSS   = "https://medium.com/feed/@anasrazy"
README_PATH  = "README.md"
MAX_POSTS    = 5
START_TAG    = "<!-- BLOG-POST-LIST:START -->"
END_TAG      = "<!-- BLOG-POST-LIST:END -->"

ICONS = ["✦", "✦", "✦", "✦", "✦"]   # one icon per post slot


def fetch_posts(url: str, limit: int) -> list[dict]:
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        print(f"⚠️  Could not fetch RSS feed: {url}")
        sys.exit(1)

    posts = []
    for entry in feed.entries[:limit]:
        # Parse publish date safely
        published = ""
        if hasattr(entry, "published"):
            try:
                dt = date_parser.parse(entry.published)
                published = dt.astimezone(timezone.utc).strftime("%b %d, %Y")
            except Exception:
                published = entry.get("published", "")

        posts.append(
            {
                "title":     entry.title,
                "link":      entry.link,
                "published": published,
                "summary":   getattr(entry, "summary_detail", None),
            }
        )

    return posts


def build_markdown(posts: list[dict]) -> str:
    if not posts:
        return (
            f"{START_TAG}\n"
            "_No blog posts yet — check back soon!_\n"
            f"{END_TAG}"
        )

    lines = [START_TAG, ""]
    lines.append("## 📰 Latest Blog Posts")
    lines.append("")
    lines.append(
        "> Auto-updated daily · Published on [Medium](https://medium.com/@anasrazy)"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, post in enumerate(posts):
        icon      = ICONS[i % len(ICONS)]
        title     = post["title"].strip()
        link      = post["link"].strip()
        published = post["published"]

        date_badge = f"`{published}`" if published else ""

        lines.append(f"### {icon} [{title}]({link})")
        if date_badge:
            lines.append(f"&nbsp;&nbsp;🗓 {date_badge}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_🔔 Want more? Follow me on [Medium →](https://medium.com/@anasrazy)_"
    )
    lines.append("")
    lines.append(END_TAG)

    return "\n".join(lines)


def inject_into_readme(new_block: str, readme_path: str) -> None:
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # If no README exists yet, create a minimal one with the sentinels
        content = (
            "# Hi, I'm Anas 👋\n\n"
            f"{START_TAG}\n{END_TAG}\n"
        )

    pattern = re.compile(
        re.escape(START_TAG) + r".*?" + re.escape(END_TAG),
        re.DOTALL,
    )

    if pattern.search(content):
        updated = pattern.sub(new_block, content)
    else:
        # Append sentinels if they don't exist yet
        updated = content.rstrip() + "\n\n" + new_block + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅  README updated with {MAX_POSTS} blog post(s).")


def main() -> None:
    print(f"📡  Fetching RSS from {MEDIUM_RSS} …")
    posts = fetch_posts(MEDIUM_RSS, MAX_POSTS)
    print(f"   Found {len(posts)} post(s).")

    new_block = build_markdown(posts)
    inject_into_readme(new_block, README_PATH)


if __name__ == "__main__":
    main()
