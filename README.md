# ICDTA Metadata Explorer

A small website that aggregates ICDTA paper metadata from Springer chapter pages and makes it searchable.

## Features
- Collects metadata for ICDTA proceedings (2021-2025 by default)
- Stores normalized data in `data/papers.json`
- Web UI with search, year/volume filters, and pagination
- Simple JSON API endpoint (`/api/papers`)

## Quick start
1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Fetch metadata:
   ```bash
   python scripts/fetch_icdta_metadata.py
   ```
3. Run the website:
   ```bash
   python app.py
   ```
4. Open http://127.0.0.1:5000

## Deploy to Vercel
1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```
2. Login:
   ```bash
   vercel login
   ```
3. From this project folder, deploy:
   ```bash
   vercel
   ```
4. For production deployment:
   ```bash
   vercel --prod
   ```

This repo already includes:
- `api/index.py` as the Vercel Python entrypoint
- `vercel.json` to route all paths to the Flask app

## Deploy to GitHub Pages (No Backend)
This project also includes a static build under `docs/` that runs fully on GitHub Pages.

### Files used by GitHub Pages
- `docs/index.html`
- `docs/assets/style.css`
- `docs/assets/app.js`
- `docs/data/papers.json`

### Keep docs metadata up-to-date
When you run:
```bash
python scripts/fetch_icdta_metadata.py
```
it now updates both:
- `data/papers.json` (Flask app)
- `docs/data/papers.json` (GitHub Pages app)

### Publish steps
1. Create a GitHub repository and add it as remote:
   ```bash
   git init
   git add .
   git commit -m "Initial ICDTA metadata site"
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. In GitHub repo settings:
   - `Settings` -> `Pages`
   - Source: `Deploy from a branch`
   - Branch: `main` and folder `/docs`
3. Your site will be available at:
   - `https://<your-username>.github.io/<your-repo>/`

## Output schema
Each paper entry in `data/papers.json` includes fields such as:
- `title`
- `authors`
- `doi`
- `url`
- `abstract`
- `keywords`
- `date_published`
- `conference_name`
- `conference_year`
- `proceedings_volume`
- `source_volume_url`

## Notes
- Springer occasionally rate-limits; rerun the fetch script if needed.
- If Springer page structure changes, selectors in `scripts/fetch_icdta_metadata.py` may need updates.
