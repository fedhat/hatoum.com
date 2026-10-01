# hatoum.com

Personal site of Federico Hatoum, migrated from Squarespace to a self-contained
static site for GitHub Pages. There are no external dependencies at runtime:
fonts, icons, images and scripts are all served from this repository. YouTube
videos load from YouTube only when a visitor clicks play.

## Layout

```
build.py            static site generator (Python 3 standard library only)
src/layout.html     shared page shell: <head>, header, footer
src/pages/*.html    Home, About, Films, Acting, Contact, 404
src/posts/*.html    blog posts (34, from 2010 to 2021)
src/comments/*.json the 223 comments from Squarespace, one file per post
src/media-sources.json  original online copy of each image (used by the WordPress export)
assets/             css, js, fonts, icons, images
files/              downloadable PDFs linked from posts
tools/wordpress_export.py  builds the WordPress import file and redirect list
wordpress/          WordPress import file, redirects and step-by-step guide
```

Everything else at the top level (`index.html`, `about/`, `blog/`, `sitemap.xml`,
etc.) is **generated**. Edit files in `src/` and rebuild; don't edit the output.

## Preview and build

```sh
python3 build.py --serve      # build, then open http://localhost:8000
python3 build.py              # build only
```

Commit the generated files along with the sources. GitHub Pages serves the
repository as-is.

## Writing a new post

Create `src/posts/YYYY-MM-DD-some-slug.html`:

```html
---
title: My new post
date: 2026-10-01T12:00:00Z
url: /blog/2026/10/1/my-new-post
excerpt: One or two sentences shown on the blog index and in link previews.
---
<p>Post body in plain HTML.</p>

[[video id="YOUTUBE_ID" title="Video title"]]

<figure>
  <a class="lightbox" href="/assets/img/blog/2026/my-new-post/photo.webp">
    <img src="/assets/img/blog/2026/my-new-post/photo.webp" alt="Describe the photo" width="1600" height="1200" loading="lazy">
  </a>
  <figcaption>Optional caption</figcaption>
</figure>
```

- The first image in the post becomes its thumbnail. Add `image: /assets/...` to the front matter to choose a different one.
- `[[video …]]` shows a local thumbnail and loads the player on click. Save the thumbnail as `assets/img/video/YOUTUBE_ID.webp` (e.g. from `https://i.ytimg.com/vi/YOUTUBE_ID/maxresdefault.jpg`), or pass `thumb="/path.webp"`. Optional: `start="149"` (seconds), `ratio="4/3"`.
- The build regenerates the blog index, RSS feed (`/blog/feed.xml`), sitemap and the home page's "From the blog" cards.

## Publishing on GitHub Pages

1. Create a repository (e.g. `hatoum.com`) and push this folder to its `main` branch.
2. On GitHub, go to **Settings → Pages → Build and deployment**, choose **Deploy from a branch**, then select `main` and `/ (root)`.
3. The `CNAME` file sets the custom domain to `hatoum.com`. At your DNS provider (currently Squarespace Domains):
   - Apex `hatoum.com`: four `A` records pointing to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`. Optionally add `AAAA` records `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`.
   - `www`: a `CNAME` record pointing to `<your-github-username>.github.io`.
   - Remove the old Squarespace records for `@` and `www`.
4. Once DNS has propagated, tick **Enforce HTTPS** in the Pages settings.

To try the site at `<username>.github.io/<repo>/` before switching DNS, delete
`CNAME` for now. All links are relative, so the site works from a sub-path too.

### Keep your Squarespace email and domain in mind

If `mail@hatoum.com` is hosted through Squarespace or Google Workspace, leave
the `MX` (and any `TXT`/SPF/DKIM) records alone when you change DNS. Only the
web records above need to change.

## Comments

The 223 comments from Squarespace appear under their posts as a read-only
archive, threaded, with your replies marked. GitHub Pages can't accept new
comments; see `wordpress/README.md` for the WordPress option.

## Moving to WordPress

`wordpress/hatoum-wordpress.xml` imports everything into WordPress: posts, pages,
comments and images, with content as standard blocks that work with any theme.
`wordpress/redirects.csv` keeps the old URLs working. Follow
[`wordpress/README.md`](wordpress/README.md), and import **before** cancelling
Squarespace. To regenerate after editing posts:

```sh
python3 tools/wordpress_export.py
```

## Contact form

Squarespace's form backend doesn't exist on GitHub Pages. The contact page
(`/contact/`) keeps the same bilingual fields, but on submit it opens the
visitor's email app with the message already filled in, addressed to the
address in `data-user`/`data-domain` on the form (`src/pages/contact.html`). The
address is put together in JavaScript so it doesn't appear in the HTML.

For a form that sends without an email app, sign up with a form service
(Formspree, Basin, Getform…) and set the form's `action` to their endpoint.

## Old URLs

Every old Squarespace URL for pages and posts still works: `/about`, `/films`,
`/acting`, `/blog`, and every `/blog/...` post URL, including the Blogger-era
`.html` ones. `/home`, `/more-stuff` and the old tag/category pages redirect.
The Squarespace test pages (`/login-testing`, `/new-page`, `/new-page-1`,
`/images`) were not migrated. The old feed at `/blog?format=rss` is now
`/blog/feed.xml`.

## Credits

- Fonts: [Fraunces](https://github.com/undercasetype/Fraunces) and [Inter](https://rsms.me/inter/), SIL Open Font License (see `assets/fonts/`).
- Brand icons: [Simple Icons](https://simpleicons.org), CC0.
