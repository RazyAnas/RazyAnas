"""
update_blogs.py
───────────────
Fetches the latest 5 Medium articles from @anasrazy and injects them
into README.md between the sentinel comment tags:

    <!-- BLOG-POST-LIST:START -->
    <!-- BLOG-POST-LIST:END -->

Each post renders as:
    [thumbnail]  Title (linked)
                 Short description
"""

import sys
import re
import html
import feedparser
from dateutil import parser as date_parser
from datetime import timezone

MEDIUM_RSS  = "https://medium.com/feed/@anasrazy"
README_PATH = "README.md"
MAX_POSTS   = 5
START_TAG   = "<!-- BLOG-POST-LIST:START -->"
END_TAG     = "<!-- BLOG-POST-LIST:END -->"
THUMB_SIZE  = 60   # px — small square thumbnail


# ── helpers ──────────────────────────────────────────────────────────────────

def extract_thumbnail(entry) -> str:
    """Return the best available image URL from an RSS entry, or ''."""

    # 1. media:thumbnail (most common on Medium)
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")

    # 2. media:content with medium="image"
    if hasattr(entry, "media_content"):
        for m in entry.media_content:
            if m.get("medium") == "image" or m.get("type", "").startswith("image"):
                return m.get("url", "")

    # 3. First <img> inside the content / summary HTML
    content_html = ""
    if hasattr(entry, "content") and entry.content:
        content_html = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content_html = entry.summary

    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
    if img_match:
        return img_match.group(1)

    return ""


def extract_description(entry) -> str:
    """Return a clean plain-text excerpt (~120 chars) from the entry summary."""
    raw = ""
    if hasattr(entry, "summary"):
        raw = entry.summary

    clean = re.sub(r"<[^>]+>", "", raw)
    clean = html.unescape(clean).strip()
    clean = re.sub(r"\s+", " ", clean)

    if len(clean) > 120:
        clean = clean[:117].rsplit(" ", 1)[0] + "…"

    return clean


def clean_medium_link(url: str) -> str:
    """Strip RSS tracking params from Medium URLs so they look clean."""
    # Remove everything from '?' onward (e.g. ?source=rss-...)
    return url.split("?")[0]


def fetch_posts(url: str, limit: int) -> list[dict]:
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        print(f"⚠️  Could not fetch RSS feed: {url}")
        sys.exit(1)

    posts = []
    for entry in feed.entries[:limit]:
        published = ""
        if hasattr(entry, "published"):
            try:
                dt = date_parser.parse(entry.published)
                published = dt.astimezone(timezone.utc).strftime("%b %d, %Y")
            except Exception:
                published = entry.get("published", "")

        posts.append(
            {
                "title":       entry.title.strip(),
                "link":        clean_medium_link(entry.link.strip()),  # ← clean URL
                "published":   published,
                "thumbnail":   extract_thumbnail(entry),
                "description": extract_description(entry),
            }
        )

    return posts


# ── markdown builder ──────────────────────────────────────────────────────────

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
        "> Auto-updated daily · Published on "
        "[Medium](https://medium.com/@anasrazy)"
    )
    lines.append("")
    lines.append("<br>")
    lines.append("")

    for post in posts:
        title       = html.escape(post["title"])   # escape < > & in titles
        link        = post["link"]
        description = html.escape(post["description"])
        thumbnail   = post["thumbnail"]
        published   = post["published"]

        if thumbnail:
            img_html = (
                f'<img src="{thumbnail}" '
                f'width="{THUMB_SIZE}" height="{THUMB_SIZE}" '
                f'style="border-radius:6px;object-fit:cover;" '
                f'align="left" />'
            )
        else:
            img_html = (
                f'<img src="https://miro.medium.com/v2/resize:fill:{THUMB_SIZE}:{THUMB_SIZE}/1*sHhtYhaCe2Uc3IU0IgKwIQ.png" '
                f'width="{THUMB_SIZE}" height="{THUMB_SIZE}" '
                f'style="border-radius:6px;object-fit:cover;" '
                f'align="left" />'
            )

        # FIX: Use <strong> + <a> instead of **[title](link)**
        #      Use <sub> for date instead of backtick code syntax
        #      Both render correctly inside HTML table cells on GitHub
        date_str = f' &nbsp;<sub>{published}</sub>' if published else ""

        block = (
            "<table><tr><td valign=\"top\" width=\"70\">\n"
            f"{img_html}\n"
            "</td><td valign=\"top\">\n"
            f"<strong><a href=\"{link}\">{title}</a></strong>{date_str}<br>\n"
            f"<sub>{description}</sub>\n"
            "</td></tr></table>\n"
        )

        lines.append(block)
        lines.append("")


    lines.append(END_TAG)

    return "\n".join(lines)


# ── readme injector ───────────────────────────────────────────────────────────

def inject_into_readme(new_block: str, readme_path: str) -> None:
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
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
        updated = content.rstrip() + "\n\n" + new_block + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅  README updated with {MAX_POSTS} blog post(s).")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print(f"📡  Fetching RSS from {MEDIUM_RSS} …")
    posts = fetch_posts(MEDIUM_RSS, MAX_POSTS)
    print(f"   Found {len(posts)} post(s).")
    for p in posts:
        thumb_status = "✔ thumbnail" if p["thumbnail"] else "✘ no thumbnail"
        print(f"   • {p['title'][:60]} [{thumb_status}]")

    new_block = build_markdown(posts)
    inject_into_readme(new_block, README_PATH)


if __name__ == "__main__":
    main()
