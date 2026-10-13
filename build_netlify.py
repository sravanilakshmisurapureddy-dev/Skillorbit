"""
build_netlify.py - Prepares the Netlify Functions deployment bundle.
Copies all Flask app source files into netlify/functions/ so the
serverless handler can import them at runtime.
"""
import os
import shutil

FUNC_DIR = os.path.join("netlify", "functions")

# Directories and files to copy into the functions directory
DIRS_TO_COPY = ["modules", "pages", "templates", "data"]
FILES_TO_COPY = ["app.py", "database.py", "campus2career.db"]

for d in DIRS_TO_COPY:
    dest = os.path.join(FUNC_DIR, d)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    if os.path.exists(d):
        shutil.copytree(d, dest)
        print(f"Copied {d}/ -> {dest}/")

for f in FILES_TO_COPY:
    dest = os.path.join(FUNC_DIR, f)
    if os.path.exists(f):
        shutil.copy2(f, dest)
        print(f"Copied {f} -> {dest}")

# Copy static directory into publish dir (already there, but ensure it exists)
if not os.path.exists("static"):
    os.makedirs("static")

print("Build complete. Netlify Functions bundle ready.")
