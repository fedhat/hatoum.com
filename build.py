#!/usr/bin/env python3
"""Static site builder for hatoum.com.

Reads templates and content from src/ and writes plain HTML into the repository
root, which GitHub Pages serves as-is. Standard library only:

    python3 build.py            # build the site
    python3 build.py --serve    # build, then preview at http://localhost:8000

Content lives in:
    src/layout.html      page shell (header, footer, <head>)
    src/pages/*.html     standalone pages; front matter `path:` sets the URL
    src/posts/*.html     blog posts; front matter `url:` sets the URL

Front matter is a block of `key: value` lines between two `---` lines at the
top of a file. Everything after it is the page's HTML body.
"""
import html
import json
import math
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo('America/Los_Angeles')  # dates are shown in the site's home time zone
except Exception:  # no tz database available: fall back to UTC
    LOCAL_TZ = timezone.utc

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')

SITE = {
    'name': 'Federico Hatoum',
    'url': 'https://hatoum.com',
    'tagline': 'Software developer, maker & YouTuber',
    'description': 'Federico Hatoum is a software developer, maker and YouTuber in Los Angeles. '
                   'Woodworking, 3D printing and repair write-ups, plus films and commercials.',
    'image': '/assets/img/home/lake.webp',
}

NAV = [('about', 'About', '/about/'), ('blog', 'Blog', '/blog/'), ('films', 'Films', '/films/'),
       ('acting', 'Acting', '/acting/'), ('contact', 'Contact', '/contact/')]

# Old Squarespace URLs that should keep working.
REDIRECTS = {
    '/home/': '/',
    '/more-stuff/': '/',
    '/blog/category/woodworking/': '/blog/',
    '/blog/tag/diy/': '/blog/',
    '/blog/tag/ikea/': '/blog/',
    '/blog/tag/ikeahack/': '/blog/',
    '/blog/tag/prusa/': '/blog/',
    '/blog/tag/3Dprinting/': '/blog/',
}

# Generated directories that are wiped before every build.
GENERATED_DIRS = ['about', 'acting', 'blog', 'contact', 'films', 'home', 'more-stuff']
GENERATED_FILES = ['index.html', '404.html', 'sitemap.xml', 'robots.txt']


# --------------------------------------------------------------------------- helpers

def read_source(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    meta = {}
    if text.startswith('---\n'):
        end = text.index('\n---\n', 4)
        for line in text[4:end].splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                meta[key.strip()] = value.strip()
        text = text[end + 5:]
    return meta, text


def esc(s):
    return html.escape(s or '', quote=True)


def out_file(url_path):
    """'/about/' -> about/index.html, '/blog/2014/03/x.html' -> blog/2014/03/x.html"""
    rel = url_path.lstrip('/')
    if rel == '' or rel.endswith('/'):
        rel += 'index.html'
    elif not rel.endswith(('.html', '.xml', '.txt')):
        rel += '/index.html'
    return rel


def relativize(doc, url_path):
    """Rewrite root-relative href/src so the site also works from a sub-path (e.g. user.github.io/repo/)."""
    depth = out_file(url_path).count('/')
    prefix = '../' * depth or './'

    def fix_tag(tag):
        t = tag.group(0)
        t = re.sub(r'\b(href|src|poster|data-src)=(["\'])/(?!/)', lambda m: f'{m.group(1)}={m.group(2)}{prefix}', t)
        t = re.sub(r'\bsrcset=(["\'])([^"\']*)\1',
                   lambda m: 'srcset=' + m.group(1) + re.sub(r'(^|,\s*)/(?!/)', r'\1' + prefix, m.group(2)) + m.group(1), t)
        return t
    # Only rewrite inside real tags, never in text such as escaped code samples.
    return re.sub(r'<[a-zA-Z][^<>]*>', fix_tag, doc)


def absolutize(doc):
    """Make root-relative URLs absolute (for feeds)."""
    return re.sub(r'\b(href|src)=(["\'])/(?!/)', r'\1=\2' + SITE['url'] + '/', doc)


def open_in_new_tab(doc):
    """Make links to other sites, and to downloadable files, open in a new tab so visitors keep this site open."""
    def fix_tag(tag):
        t = tag.group(0)
        href = re.search(r'\bhref=(["\'])(.*?)\1', t)
        if not href or re.search(r'\btarget=', t):
            return t
        url = href.group(2)
        host = re.match(r'(?:https?:)?//([^/?#]+)', url, re.I)
        if host:
            if re.fullmatch(r'(www\.)?hatoum\.com', host.group(1), re.I):
                return t
        elif not url.startswith('/files/'):
            return t
        rel = re.search(r'\brel=(["\'])(.*?)\1', t)
        if rel:
            if 'noopener' not in rel.group(2).split():
                t = t[:rel.start(2)] + rel.group(2) + ' noopener' + t[rel.end(2):]
            return t[:-1] + ' target="_blank">'
        return t[:-1] + ' target="_blank" rel="noopener">'
    return re.sub(r'<a\s[^<>]*>', fix_tag, doc)


def write(url_path, doc, relative=True):
    if not url_path.endswith(('.xml', '.txt')):
        doc = open_in_new_tab(doc)
    if relative:
        doc = relativize(doc, url_path)
    path = os.path.join(ROOT, out_file(url_path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(doc)


def parse_date(s):
    """'2021-12-17T19:22:08Z' (UTC) -> aware datetime in the site's local time zone."""
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)


def human_date(d):
    return f'{d:%B} {d.day}, {d.year}'


def reading_time(body):
    words = len(re.sub(r'<[^>]+>', ' ', body).split())
    return max(1, math.ceil(words / 230))


def icon(name):
    return f'<svg class="icon" aria-hidden="true" focusable="false"><use href="/assets/icons/icons.svg#{name}"></use></svg>'


def video(vid, title, thumb=None, start=None, caption=True, ratio=None):
    """YouTube 'facade': a thumbnail link that site.js swaps for the player on click."""
    thumb = thumb or f'/assets/img/video/{vid}.webp'
    t = f'&amp;t={start}s' if start else ''
    start_attr = f' data-start="{start}"' if start else ''
    cap = f'<figcaption>{esc(title)}</figcaption>' if caption else ''
    style = f' style="aspect-ratio: {ratio}"' if ratio else ''
    return (f'<figure class="video"><a class="yt" href="https://www.youtube.com/watch?v={vid}{t}" data-yt="{vid}"{start_attr}{style} '
            f'data-title="{esc(title)}"><img src="{thumb}" alt="" width="640" height="360" loading="lazy" decoding="async">'
            f'<span class="yt-play" aria-hidden="true"></span><span class="visually-hidden">Play video: {esc(title)}</span></a>'
            f'{cap}</figure>')


def expand_shortcodes(body):
    """[[video id="..." title="..." thumb="..." start="..." ratio="4/3"]] and [[icon name]]"""
    def v(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        return video(attrs['id'], html.unescape(attrs.get('title', '')), attrs.get('thumb'), attrs.get('start'),
                     attrs.get('caption', 'yes') != 'no', attrs.get('ratio'))
    body = re.sub(r'\[\[video ([^\]]+)\]\]', v, body)
    body = re.sub(r'\[\[icon (\w[\w-]*)\]\]', lambda m: icon(m.group(1)), body)
    return body


def label_lightboxes(body):
    """Give image-only lightbox links an accessible name."""
    def add(m):
        alt = re.search(r'alt="([^"]*)"', m.group(2))
        if alt and alt.group(1):
            return m.group(0)
        return f'{m.group(1)}{m.group(2)}<span class="visually-hidden">View full-size image</span></a>'
    return re.sub(r'(<a class="lightbox"[^>]*>)(<img[^>]*>)</a>', add, body)


# --------------------------------------------------------------------------- rendering

with open(os.path.join(SRC, 'layout.html'), encoding='utf-8') as _f:
    LAYOUT = _f.read()


def render(content, *, title, url_path, description=None, section='', image=None, body_class='',
           og_type='website', head_extra=''):
    full_title = SITE['name'] if title == SITE['name'] else f'{title} · {SITE["name"]}'
    nav = []
    for key, label, href in NAV:
        cur = ' aria-current="page"' if key == section else ''
        nav.append(f'<a href="{href}"{cur}>{label}</a>')
    image = image or SITE['image']
    values = {
        'title': esc(full_title),
        'description': esc(description or SITE['description']),
        'canonical': SITE['url'] + url_path,
        'og_type': og_type,
        'og_image': SITE['url'] + image,
        'nav': '\n        '.join(nav),
        'content': content,
        'body_class': body_class,
        'year': str(datetime.now().year),
        'head_extra': head_extra,
    }
    return re.sub(r'\{\{(\w+)\}\}', lambda m: values.get(m.group(1), m.group(0)), LAYOUT)


def load_posts():
    posts = []
    for name in sorted(os.listdir(os.path.join(SRC, 'posts'))):
        if not name.endswith('.html'):
            continue
        meta, body = read_source(os.path.join(SRC, 'posts', name))
        meta['body'] = label_lightboxes(expand_shortcodes(body))
        meta['date_obj'] = parse_date(meta['date'])
        if not meta.get('image'):
            # Use the first image in the post (photo or video thumbnail) as its cover.
            m = re.search(r'<img[^>]+src="(/assets/[^"]+)"', meta['body'])
            if m:
                meta['image'] = m.group(1)
        # Squarespace-era URLs have no trailing slash; they become folders, so link to the folder form.
        if not meta['url'].endswith(('/', '.html')):
            meta['url'] += '/'
        meta['src'] = name
        posts.append(meta)
    posts.sort(key=lambda p: p['date_obj'], reverse=True)
    return posts


def post_card(p, heading='h3'):
    img = (f'<img src="{p["image"]}" alt="" loading="lazy" decoding="async" width="600" height="400">'
           if p.get('image') else '<span class="card-placeholder" aria-hidden="true"></span>')
    return (f'<article class="card post-card"><a class="card-link" href="{p["url"]}">'
            f'<div class="card-media">{img}</div><div class="card-body">'
            f'<time datetime="{p["date"]}">{human_date(p["date_obj"])}</time>'
            f'<{heading} class="card-title">{esc(p["title"])}</{heading}>'
            f'<p>{esc(p["excerpt"])}</p></div></a></article>')


def load_comments(post_src):
    path = os.path.join(SRC, 'comments', post_src.replace('.html', '.json'))
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def render_comments(comments):
    """Read-only archive of comments imported from Squarespace, threaded by parent id."""
    if not comments:
        return ''
    children = {}
    for c in comments:
        children.setdefault(c['parent'], []).append(c)

    def render(c):
        d = parse_date(c['date'])
        name = esc(c['author'])
        if c['url']:
            name = f'<a href="{esc(c["url"])}" rel="nofollow ugc">{name}</a>'
        badge = ' <span class="comment-badge">Author</span>' if c['owner'] else ''
        replies = ''.join(render(r) for r in children.get(c['id'], []))
        replies = f'<ol class="comment-replies">{replies}</ol>' if replies else ''
        cls = 'comment is-owner' if c['owner'] else 'comment'
        return (f'<li class="{cls}" id="comment-{esc(c["id"])}"><article>'
                f'<header class="comment-meta"><span class="comment-author">{name}</span>{badge}'
                f'<a class="comment-date" href="#comment-{esc(c["id"])}"><time datetime="{c["date"]}">{human_date(d)}</time></a></header>'
                f'<div class="comment-body">{c["body"]}</div></article>{replies}</li>')
    items = ''.join(render(c) for c in children.get('', []))
    n = len(comments)
    return f'''<section class="comments" aria-labelledby="comments-title">
    <h2 id="comments-title">{n} comment{"s" if n != 1 else ""}</h2>
    <p class="comments-note">Comments are closed. These were left on the previous version of this site. Questions? <a href="/contact/">Get in touch</a>.</p>
    <ol class="comment-list">{items}</ol>
  </section>'''


def build_post(p, newer, older):
    d = p['date_obj']
    pager = []
    if older:
        pager.append(f'<a class="pager-prev" href="{older["url"]}"><span>Older</span>{esc(older["title"])}</a>')
    if newer:
        pager.append(f'<a class="pager-next" href="{newer["url"]}"><span>Newer</span>{esc(newer["title"])}</a>')
    ld = {
        '@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': p['title'],
        'datePublished': p['date'], 'author': {'@type': 'Person', 'name': SITE['name'], 'url': SITE['url']},
        'mainEntityOfPage': SITE['url'] + p['url'],
    }
    if p.get('image'):
        ld['image'] = SITE['url'] + p['image']
    head_extra = ('<script type="application/ld+json">' + json.dumps(ld).replace('</', '<\\/') + '</script>\n'
                  f'  <meta property="article:published_time" content="{p["date"]}">')
    content = f'''<article class="post wrap-narrow">
  <header class="post-header">
    <p class="post-kicker"><a href="/blog/">Blog</a></p>
    <h1>{esc(p["title"])}</h1>
    <p class="post-meta"><time datetime="{p["date"]}">{human_date(d)}</time> · {reading_time(p["body"])} min read</p>
  </header>
  <div class="prose">
{p["body"]}
  </div>
  {render_comments(load_comments(p["src"]))}
  <nav class="pager" aria-label="More posts">
    {"".join(pager)}
  </nav>
</article>'''
    write(p['url'], render(content, title=p['title'], url_path=p['url'], description=p['excerpt'],
                           section='blog', image=p.get('image'), og_type='article', head_extra=head_extra))


def build_blog_index(posts):
    by_year = {}
    for p in posts:
        by_year.setdefault(p['date_obj'].year, []).append(p)
    groups = []
    for year, items in by_year.items():
        rows = []
        for p in items:
            thumb = (f'<img src="{p["image"]}" alt="" loading="lazy" decoding="async" width="160" height="120">'
                     if p.get('image') else '<span class="card-placeholder" aria-hidden="true"></span>')
            rows.append(f'<li class="post-row"><a href="{p["url"]}">'
                        f'<span class="post-row-thumb">{thumb}</span>'
                        f'<span class="post-row-text"><span class="post-row-title">{esc(p["title"])}</span>'
                        f'<span class="post-row-excerpt">{esc(p["excerpt"])}</span></span>'
                        f'<time datetime="{p["date"]}">{p["date_obj"]:%b} {p["date_obj"].day}</time></a></li>')
        groups.append(f'<section class="year-group" aria-labelledby="y{year}"><h2 id="y{year}">{year}</h2>'
                      f'<ul class="post-list">{"".join(rows)}</ul></section>')
    content = f'''<div class="wrap page-head">
  <h1>Blog</h1>
  <p class="lede">Notes on making, fixing and programming things, from 2010 to today.</p>
  <div class="blog-tools">
    <label class="search" for="post-filter">{icon("search")}<span class="visually-hidden">Filter posts</span>
      <input id="post-filter" type="search" placeholder="Filter {len(posts)} posts…" autocomplete="off"></label>
    <a class="rss-link" href="/blog/feed.xml">{icon("rss")} RSS feed</a>
  </div>
</div>
<div class="wrap blog-index" data-filter-scope>
  {"".join(groups)}
  <p class="empty-state" hidden>No posts match that filter.</p>
</div>'''
    write('/blog/', render(content, title='Blog', url_path='/blog/', section='blog',
                           description='Posts by Federico Hatoum about woodworking, 3D printing, electronics repair and programming.',
                           head_extra='<link rel="alternate" type="application/rss+xml" title="Federico Hatoum — Blog" href="/blog/feed.xml">'))


def build_feed(posts):
    items = []
    for p in posts[:20]:
        items.append(f'''  <item>
    <title>{esc(p["title"])}</title>
    <link>{SITE["url"]}{p["url"]}</link>
    <guid isPermaLink="true">{SITE["url"]}{p["url"]}</guid>
    <pubDate>{format_datetime(p["date_obj"])}</pubDate>
    <description>{esc(absolutize(p["body"]))}</description>
  </item>''')
    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{SITE["name"]} — Blog</title>
  <link>{SITE["url"]}/blog/</link>
  <atom:link href="{SITE["url"]}/blog/feed.xml" rel="self" type="application/rss+xml"/>
  <description>{esc(SITE["description"])}</description>
  <language>en-us</language>
  <lastBuildDate>{format_datetime(posts[0]["date_obj"])}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
'''
    write('/blog/feed.xml', feed, relative=False)


def build_pages(posts):
    pages_dir = os.path.join(SRC, 'pages')
    urls = []
    for name in sorted(os.listdir(pages_dir)):
        if not name.endswith('.html'):
            continue
        meta, body = read_source(os.path.join(pages_dir, name))
        body = expand_shortcodes(body)
        if '{{latest_posts}}' in body:
            # Skip posts whose video is already featured on the same page.
            shown = set(re.findall(r'data-yt="([^"]+)"', body))
            fresh = [p for p in posts if not shown & set(re.findall(r'data-yt="([^"]+)"', p['body']))]
            body = body.replace('{{latest_posts}}', ''.join(post_card(p) for p in fresh[:3]))
        path = meta['path']
        doc = render(body, title=meta.get('title', SITE['name']), url_path=path, description=meta.get('description'),
                     section=meta.get('section', ''), image=meta.get('image'), body_class=meta.get('body_class', ''))
        # 404.html is served from any URL depth, so it keeps root-relative links.
        write(path, doc, relative=(path != '/404.html'))
        if meta.get('sitemap', 'yes') != 'no':
            urls.append(path)
    return urls


def build_redirects():
    for old, new in REDIRECTS.items():
        rel_new = '../' * out_file(old).count('/') + new.lstrip('/')
        doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Redirecting…</title>
<link rel="canonical" href="{SITE["url"]}{new}"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={rel_new}"></head>
<body><p>This page has moved to <a href="{new}">{SITE["url"]}{new}</a>.</p></body></html>
'''
        write(old, doc)


def build_sitemap(urls):
    entries = '\n'.join(f'  <url><loc>{SITE["url"]}{u}</loc></url>' for u in urls)
    write('/sitemap.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
''', relative=False)
    write('/robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE["url"]}/sitemap.xml\n', relative=False)


def clean():
    for d in GENERATED_DIRS:
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    for f in GENERATED_FILES:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            os.remove(p)


def main():
    clean()
    posts = load_posts()
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        build_post(p, newer, older)
    build_blog_index(posts)
    build_feed(posts)
    urls = build_pages(posts)
    build_redirects()
    build_sitemap(sorted(urls) + ['/blog/'] + [p['url'] for p in posts])
    print(f'Built {len(posts)} posts and {len(urls)} pages.')

    if '--serve' in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        print('Serving at http://localhost:8000 (Ctrl+C to stop)')
        http.server.ThreadingHTTPServer(('', 8000), handler).serve_forever()


if __name__ == '__main__':
    main()
