# VALUE HUNTER AI — v249 downloadable dashboard preview

This folder is the complete static dashboard generated from the repository `docs/` directory. It is **not** a deployed GitHub Pages site, a source of current licensed SGX quotes, or investment advice. Rankings are intentionally disabled until all official validation conditions pass.

## Mac / Windows local preview

1. Open the GitHub Actions run that generated the artifact and download `value-hunter-dashboard-preview-v249` from **Artifacts** (GitHub sign-in may be required).
2. Extract the downloaded archive. Inside is `value-hunter-dashboard-preview-v249.zip`; extract that ZIP too. You should then see a `docs` directory with `index.html`, JavaScript, CSS, and `data/`.
3. Open Terminal / PowerShell in the directory **containing** the `docs` folder.
4. Run:

   ```sh
   python3 -m http.server 8000
   ```

   On Windows, if `python3` is unavailable, try `py -m http.server 8000`.
5. Open **http://localhost:8000/docs/** in Chrome.

Do not double-click `docs/index.html` directly: the dashboard fetches local JSON files, and browsers often block file:// JSON requests. A local HTTP server is only used on your computer; it does not make the dashboard a publicly hosted website.

The downloaded snapshot contains data as of the original repository build. It does not obtain current SGX prices by itself. Do not treat historical reference shares or issuer-only financial data as a current ranking.

## To publish using GitHub Pages

Repository owner: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Then open Actions → **VALUE HUNTER dashboard publish v46** → **Run workflow**. Check that the `pages` job itself finishes **success**, not merely the `validate` or `dashboard-preview` jobs. A green overall Actions run with a skipped `pages` job does not mean the website is published.

## Technical record

Preview is built in `.github/workflows/value-hunter-pages.yml` by the `dashboard-preview` job after `validate` passes. Artifact retention is 30 days. The primary `docs/data/latest.json` feed remains fail-closed, with investment ranking eligibility false.
