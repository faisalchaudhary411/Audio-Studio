# VoxCraft — canonical URL fix (Search Console "Duplicate without user-selected canonical")

2 files, same repo structure. app.py is built on the correctly-merged
file — CLONE_CHAR_LIMIT = 1400 preserved and confirmed below, re-tested
against this exact file.

## Files
- app.py (MODIFIED)
- templates/base.html (MODIFIED)

## What caused the Search Console warning

The site had zero canonical tags anywhere — checked every template,
confirmed none existed. Without one, Google decides on its own which
version of a page to index when the same content is reachable at more
than one URL, and flags it as "Duplicate without user-selected canonical"
when it can't confidently pick.

Two real duplicate-content pairs exist on the site right now, both
self-inflicted from earlier phases:

- **/blog?tag=X** — every tag chip on every blog post and the blog list
  page itself links to a tag-filtered URL (e.g. /blog?tag=urdu,
  /blog?tag=tutorial). With ~15+ unique tags across the 10 posts, that's
  15+ crawlable URLs nearly identical to plain /blog.
- **/upgrade?plan=pro** vs **/upgrade?plan=pro_plus** — linked from the
  Pricing page's "Get Pro"/"Get Pro+" buttons and the landing page's CTA.
  Same page, just pre-selects which plan radio button is checked.

## The fix

One rule, applied sitewide via the existing context processor in app.py:
canonical URL = the current request's absolute path, with any query
string dropped. This single rule correctly resolves both cases above
(and any future query-string variant of any page) without needing a
special case for either — /blog?tag=urdu canonicalizes to /blog,
/upgrade?plan=pro_plus canonicalizes to /upgrade, and every page with no
query string canonicalizes to itself.

A `<link rel="canonical">` tag was added to base.html's `<head>`, pulling
from this value — present on every page sitewide, no per-template changes
needed anywhere else.

The app already runs `ProxyFix` with `x_proto=1, x_host=1` (confirmed in
app.py), so this correctly reports `https://voxcraft.site/...` even
running behind Nginx, not an internal `http://127.0.0.1:.../...` — no
additional proxy configuration needed.

## What to expect after deploying

This doesn't retroactively fix already-indexed duplicate URLs — Google
needs to recrawl and notice the new canonical tag. In Search Console:
after deploying, you can use the URL Inspection tool on one of the
affected URLs and request indexing to speed this up, but the warning
itself should clear on its own over the following days/weeks as Google
recrawls normally.

## Testing performed
- Python AST syntax check against the exact final merged file.
- Jinja2 parse check on base.html.
- A real Flask app test (using the actual templates and the actual
  context-processor logic) hitting 8 different paths — including both
  real duplicate-content pairs with multiple query string variations —
  and confirming the rendered `<link rel="canonical">` tag correctly
  strips the query string in every case while leaving query-string-free
  pages (like /tools/transcribe-audio-to-text) canonicalizing to
  themselves.
- Regression check: re-confirmed the pronunciation dictionary and all 22
  BLOG_TOOL_LINKS entries from previous phases still work correctly in
  this exact file.
