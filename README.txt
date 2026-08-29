SEO FIXES for voxcraft.site
===========================

What was fixed
--------------
1. /activate and /upgrade now have <meta name="robots" content="noindex, follow">
2. /activate and /upgrade removed from sitemap.xml
3. Blog URLs now use readable slugs from the post title
   - Old:  /blog/1787584809831
   - New:  /blog/how-ai-voice-cloning-works
4. Old numeric blog URLs 301-redirect to the new slug (keeps any existing links)
5. Sitemap blog entries use the new slug URLs
6. Includes the earlier clone/ref_text fix in app.py

Files to upload (replace existing)
----------------------------------
app.py                          → project root
templates/base.html
templates/activate.html
templates/upgrade.html
templates/blog_list.html
templates/blog_detail.html
templates/landing.html

After upload
------------
1. Restart the app / gunicorn / systemd service
2. In Google Search Console:
   - Resubmit sitemap: https://voxcraft.site/sitemap.xml
   - Request indexing for homepage + /studio + a few blog posts
3. Optional: open a few old /blog/<number> URLs and confirm they redirect

Notes
-----
- Slugs are auto-generated from the post title. You can also set an explicit
  "slug" field on a blog post in the admin/JSON if you want a custom URL.
- The dark GSC screenshot is still normal for dark themes — ignore it.
