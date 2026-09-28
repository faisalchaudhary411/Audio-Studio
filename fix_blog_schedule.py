"""
fix_blog_schedule.py — diagnose + repair scheduled blog visibility.

Run on the VPS (same env as app.py):

    python3 fix_blog_schedule.py           # report only
    python3 fix_blog_schedule.py --fix    # ensure publish_date is set; keep published=True
    python3 fix_blog_schedule.py --unpublish-future  # set published=False until date (hard hide)

Why this exists:
  Public routes use _blog_is_public() which requires:
    published == True  AND  (no publish_date OR publish_date <= today)

  If posts appeared all at once with future dates, usual causes:
  1. Looking at /admin/blog (shows everything, including future)
  2. VPS app.py is older and ignores publish_date
  3. publish_date missing on saved rows (only date was set)
"""
import argparse
import datetime as dt
import sys

import persistence

TODAY = dt.datetime.now().strftime("%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Copy date -> publish_date when missing")
    ap.add_argument(
        "--unpublish-future",
        action="store_true",
        help="Set published=False for posts with publish_date > today (hard schedule)",
    )
    args = ap.parse_args()

    posts = persistence.load_blogs()
    print(f"Today (server): {TODAY}")
    print(f"Total posts: {len(posts)}\n")

    future = []
    missing_pd = []
    public_now = []

    for p in posts:
        title = (p.get("title") or "")[:60]
        pub = bool(p.get("published"))
        pd = (p.get("publish_date") or "").strip()
        date = (p.get("date") or "").strip()
        effective = pd or date

        # Mirror app._blog_is_public
        is_public = False
        if pub:
            if not pd:
                is_public = True
            else:
                is_public = pd <= TODAY

        status = "PUBLIC" if is_public else ("FUTURE" if pub and pd > TODAY else "HIDDEN")
        print(f"[{status}] published={pub} publish_date={pd or '-'} date={date or '-'} | {title}")

        if pub and pd and pd > TODAY:
            future.append(p)
        if pub and not pd and date and date > TODAY:
            missing_pd.append(p)
        if is_public:
            public_now.append(p)

    print(f"\n--- Summary ---")
    print(f"Would be public on site now: {len(public_now)}")
    print(f"Future scheduled (published + publish_date > today): {len(future)}")
    print(f"Published but only future date/ (no publish_date): {len(missing_pd)}")

    if not args.fix and not args.unpublish_future:
        print("\nNo changes made. Re-run with --fix and/or --unpublish-future if needed.")
        if missing_pd:
            print("TIP: these posts look 'future' by date but are PUBLIC because publish_date is empty.")
            print("     Run: python3 fix_blog_schedule.py --fix")
        return

    changed = 0
    for p in posts:
        pd = (p.get("publish_date") or "").strip()
        date = (p.get("date") or "").strip()

        if args.fix and not pd and date:
            p["publish_date"] = date
            changed += 1
            print(f"FIX publish_date <- date for: {(p.get('title') or '')[:50]}")

        pd = (p.get("publish_date") or "").strip()
        if args.unpublish_future and p.get("published") and pd and pd > TODAY:
            p["published"] = False
            changed += 1
            print(f"UNPUBLISH until {pd}: {(p.get('title') or '')[:50]}")

    if changed:
        persistence.save_blogs(posts)
        print(f"\nSaved. Updated {changed} post(s). Restart app if it caches blogs in memory.")
    else:
        print("\nNothing to change.")


if __name__ == "__main__":
    main()
