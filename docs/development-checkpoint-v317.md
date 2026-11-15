# VALUE HUNTER AI v317 — TDnet Japanese filings

Safie (4375) and Nissan (7201) now have two annual periods, parent equity, income, and fiscal-year-end outstanding shares verified from their TDnet PDFs. The shared parser checks issuer code, dated rows, reported yen millions and treasury-share subtraction. Negative values are preserved. Growth is blank when prior operating income is a loss. The three-market page now has detailed annual data for three Japanese and three US issuers.

JPX and the selected SEC originals succeeded from the development environment. GitHub Actions received 403 specifically at the SEC ticker-directory URL in v316 (run 43688218534). CI therefore has distinct Japan live replay and saved SEC filing regression jobs; a green fixture test does not assert a fresh SEC retrieval. Run the verifier without arguments in an environment with access to both data sources. v316 HTTP and directly openable browser ZIPs passed.
