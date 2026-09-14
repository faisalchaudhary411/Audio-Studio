# Legacy Render entry point — production now runs via deploy/voxcraft.service
# (systemd) on the VPS, not this file. Kept in sync so it isn't a trap if
# this project is ever redeployed from Procfile again: --timeout must
# exceed the slowest synchronous request (Modal clone jobs up to 600s,
# now also long redub jobs), same reasoning as voxcraft.service.
web: gunicorn app:app --workers 2 --threads 4 --preload --timeout 660 --graceful-timeout 30 --max-requests 200 --max-requests-jitter 50 --bind 0.0.0.0:$PORT
