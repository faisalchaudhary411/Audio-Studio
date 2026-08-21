# VoxCraft — footer, About/How We Test/Pricing content, blog tags

Same repo structure — overwrite these paths. app.py is built on your
uploaded file (CLONE_CHAR_LIMIT = 1400 preserved, confirmed below).

## Files
- app.py (MODIFIED — builds on your uploaded version, not the older one)
- seed_blog_posts.py (MODIFIED — now includes tags + backfill logic)
- templates/base.html (MODIFIED — footer)
- templates/about.html (MODIFIED)
- templates/how_we_test.html (MODIFIED)
- templates/pricing.html (MODIFIED)
- templates/blog_list.html (MODIFIED)
- templates/blog_detail.html (MODIFIED)
- templates/admin/blog.html (MODIFIED)

## A note on how this file was built

I initially built today's changes on an older tracked copy of app.py by
mistake, not the one you uploaded with your CLONE_CHAR_LIMIT = 1400 fix.
Caught it before sending anything — re-extracted today's changes as an
isolated diff (confirmed exactly 2 changes: the blog_list route and the
admin_blog route, nothing else) and re-applied them onto your actual
uploaded file. This app.py has CLONE_CHAR_LIMIT = 1400 intact, plus every
fix from every previous phase (verified — BLOG_TOOL_LINKS, PKR pricing,
notification cache fix, contact form, tool pages, all present), plus
today's additions. Re-ran the full test suite against this exact file
before packaging, not just the version I originally built it on.

## What changed

**Footer (base.html)** — was 6 links (Privacy/Terms/About/How We
Test/Contact/Activate), missing your actual product pages entirely. Now
also links to Voice Studio, Voice Cloning, Tools, Blog, and Pricing. This
is sitewide, so it's the single highest-leverage internal-linking change
in this batch.

**About page** — the "what you can do" list now links each item to its
actual tool page instead of being plain text. Added a "why VoxCraft
exists" section and an FAQ block (is it free, languages, install
required, who built it).

**How We Test** — added a "what we don't do" section (no paid rankings,
no hiding limitations, models change over time) and an FAQ block. Existing
examples now link to the actual tool pages they reference.

**Pricing** — added a 6-question FAQ covering manual payment mechanics,
grace-period expiry, plan switching, device binding, and refunds, plus
FAQPage schema markup.

**Blog tags** — full system, not just a field:
- No DB migration needed — blog posts are stored as JSON, so a new `tags`
  key just works.
- Admin form (`admin/blog.html`) has a tags input, comma-separated,
  prefilled on edit.
- `admin_blog()` route parses/normalizes tags (trim, lowercase, dedupe).
- Public `/blog` page shows clickable tag filter chips; `/blog?tag=X`
  filters to matching posts.
- Each post's detail page shows its tags as links back to the filtered
  list.
- JSON-LD `keywords` field added to blog post schema.
- `seed_blog_posts.py` now assigns tags to all 10 existing posts, AND
  includes a backfill path — if you already ran the old version of this
  script (posts exist but have no tags), running the updated script will
  add tags to those existing posts instead of skipping them or
  duplicating anything.

## Testing performed
- Full syntax check (Python AST) and Jinja2 parse check on every touched
  file, run against the exact final merged app.py — not an earlier draft.
- Ran the updated seed_blog_posts.py against a real SQLite DB that
  already had the 10 posts from before (no tags) — confirmed it correctly
  backfills tags on all 10 without creating duplicates, and confirmed
  re-running it afterward is a clean no-op.
- Rendered blog_list.html unfiltered (confirmed 27 unique tags surfaced
  correctly) and filtered by tag=tutorial (confirmed exactly the 5
  matching posts render).
- Rendered blog_detail.html and confirmed tags render as working filter
  links, and that the JSON-LD keywords field is present.
- Rendered admin/blog.html in edit mode and confirmed a post's tags
  correctly prefill as a comma-separated string in the form field.
- Re-verified BLOG_TOOL_LINKS (22 entries) and PKR/cache-control fixes
  from earlier phases are still intact and functioning in this exact file.
