# Machine Economy Lab — Research Paper Repository

## Project Overview

This repo contains the prototype code and research paper for the **Machine Economy Lab** at HTW Berlin.  
Supervisor: Prof. Dr. Alexandra Mikityuk.  
Research Question: How can GPS-triggered autonomous drone delivery with on-chain Solana payment settlement enable trustless machine-to-machine transactions?

**Prototype built:**
- Raspberry Pi + Waveshare SIM7600X HAT (GPS via ttyUSB2)
- Pixhawk flight controller (MAVLink via /dev/serial0)
- Anchor smart contract on Solana Devnet — GPS geofence triggers escrow release
- Indoor PoC proven; outdoor test completed

## Repository Structure

```
progress/
├── rpi/                    ← RPi Python code (main.py, pixhawk_bridge.py, solana_client.py, config.py)
├── anchor/                 ← Solana Anchor smart contract (lib.rs)
├── paper/
│   └── Machine_Economy_Lab_Research_Paper.html  ← THE PAPER (open in browser → Ctrl+P for PDF)
├── CLAUDE.md               ← This file (auto-loaded by Claude Code)
├── README.md               ← Human overview
└── .gitlab-ci.yml          ← GitLab Pages (auto-publishes paper as website)
```

## Paper — HTML Structure

The paper is a single HTML file. Every chapter follows this pattern:

```html
<h2 id="chapter-N">N. Chapter Title</h2>
<p>Opening paragraph...</p>
<h3>N.1 Subsection Title</h3>
<p>Content...</p>
```

New chapters are inserted **before** the line `<h2>References</h2>`.  
Existing chapter IDs: `chapter-1` (Introduction), `chapter-7` (Prototype Development).

## Chapter Assignments

| # | Title | Author | Status |
|---|---|---|---|
| 1 | Introduction | Kevin | ✓ Done |
| 2 | Literature Review | TBD | Not started |
| 3 | Theoretical Framework | TBD | Not started |
| 4 | Research Methodology | TBD | Not started |
| 5 | System Requirements | TBD | Not started |
| 6 | System Architecture | Kevin | ✓ Done |
| 7 | Prototype Development | Kevin | ✓ Done |
| 8 | Payment Mechanisms | TBD | Not started |
| 9 | Experimental Design | TBD | Not started |
| 10 | Experimental Results | TBD | Not started |
| 11 | Comparative Evaluation | TBD | Not started |
| 12 | Security Analysis | TBD | Not started |
| 13 | Reliability and Robustness | TBD | Not started |
| 14 | Legal, Ethical and Societal Implications | TBD | Not started |
| 15 | Business and Economic Analysis | TBD | Not started |
| 16 | Discussion | TBD | Not started |
| 17 | Future Work | TBD | Not started |
| 18 | Conclusion | TBD | Not started |

## How to Contribute a Chapter (for Yash, Xinyan, and others)

**Step 1 — Tell Claude what you want to write:**

> "I want to write Chapter 4 — Research Methodology. Here is my content: [your text or outline]"

Claude will:
1. Read the current paper from `paper/Machine_Economy_Lab_Research_Paper.html`
2. Find the correct insertion point (before `<h2>References</h2>`, in chapter-number order)
3. Format your content into the HTML chapter structure
4. Commit with your name: `git commit -m "Add Chapter 4 — Research Methodology (Yashdeep Singh)"`
5. Push to GitLab

**Step 2 — Push to GitLab (requires PAT setup — one time per machine):**

```bash
# Set the remote URL with your PAT (replace YOUR_PAT with your token)
git remote set-url gitlab https://oauth2:YOUR_PAT@gitlab.com/robopay-group/robopay-research-group.git

# Push
git push gitlab main

# After pushing, remove PAT from URL (security)
git remote set-url gitlab https://gitlab.com/robopay-group/robopay-research-group.git
```

Get your PAT at: **gitlab.com → Profile → Access Tokens → Add new token**  
Scopes needed: `read_repository`, `write_repository`  
Never commit the PAT value into any file — always pass it only in the remote URL temporarily.

## Key Technical Facts (for writing chapters accurately)

- **GPS geofence (on-chain, lib.rs):** `lat_diff <= 2000 && lon_diff <= 3000` in degE7 encoding = ±22m lat × ±20m lon at 52°N
- **GPS geofence (client-side, pixhawk_bridge.py):** Haversine formula, `ARRIVAL_RADIUS_M = 13.0m`
- **GPS source:** Waveshare SIM7600X HAT via AT+CGPSINFO on /dev/ttyUSB2, ~0.5 Hz sampling
- **Payment:** Anchor escrow, full amount to seller on `confirm_delivery`; split-payment (delivery fee + product price) is planned for production but not yet implemented
- **MCC** = Mesh Companion Container (Staex product) — NOT "Machine Connectivity Cloud"
- **Solana network:** Devnet (not Mainnet)
- **Outdoor test:** completed; Step 4a = geofence trigger (GPS arrives within radius), Step 4b = TX confirmation (~4s later on Solana)
- **Smart contract language:** Rust (Anchor framework), deployed to Devnet
- **Three-node trust model:** Drone operator (RPi), delivery node (letterbox RPi), Solana blockchain — each independent, no single point of trust

## GitLab Pages

The paper is auto-published as a website via `.gitlab-ci.yml`.  
After every push to `main`, GitLab builds and publishes the HTML at:  
`https://robopay-group.gitlab.io/robopay-research-group/`

Open in any browser — or use Ctrl+P (Chrome/Edge) → "Save as PDF" to export.
