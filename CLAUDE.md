# Machine Economy Lab — Research Paper Repository

> **Source of truth for the paper outline:** the Google Doc
> (https://docs.google.com/document/d/1wvbvqWtbmJVxRuOWr4nrCI1FpnJ7VJlhOxUPSsQWCwc/edit)
> is the authoritative outline/assignment document. The chapter table below
> is a summary only — if it ever disagrees with the Google Doc, the Google
> Doc wins. The published paper itself lives in `paper/` (single HTML file);
> edit the HTML only for content already written, and update this table to
> match.
>
> **Before pushing chapter edits, run the consistency check:**
> `python3 scripts/check_paper_refs.py paper/Machine_Economy_Lab_Research_Paper.html`
> (verifies every body citation [n] has a References entry and no duplicate
> figure captions).

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
Existing chapter IDs: `chapter-1` (Introduction), `chapter-2` (Theoretical Foundations), `chapter-6` (System Architecture), `chapter-7` (Prototype Development).

## Chapter Assignments

| # | Title | Author | Subsections |
|---|---|---|---|
| 1 | Introduction | Kevin | 1.1 Background · 1.2 Problem Statement · 1.3 Research Gap · 1.7 Hypotheses · 1.8 Scope · 1.9 Contributions · 1.10 Methodology · 1.11 Structure |
| 2 | Theoretical Foundations | **Xinyan** | 2.1 Machine Economy · 2.2 AI Agents and Autonomous Systems · 2.3 Blockchain Technology, Smart Contracts and Escrow · 2.4 Machine Identity · 2.5 M2M Communication · 2.6 Autonomous Payment Systems · 2.7 Solana as Settlement Layer · 2.8 x402 Protocol vs GPS-Based Localization · 2.9 Security Foundations |
| 3 | Literature Review | **Yash** | 3.0 Purpose, Method and Structure · 3.1 Machine Economy Research · 3.2 Autonomous Robotics · 3.3 AI Agent Economy · 3.4 Blockchain-Based Payments · 3.5 Autonomous Delivery Systems · 3.6 Internet of Drones · 3.7 Digital Identity for AI Agents · 3.8 Machine Trust · 3.9 Existing Payment Architectures · 3.10 Comparative Analysis · 3.11 Identified Research Gap |
| 4 | Research Methodology | **Xinyan** | 4.1 Philosophy · 4.2 Design · 4.3 Mixed-Method · 4.4 Lit. Review · 4.5 Prototype Dev · 4.6 Experimental Design · 4.7 Expert Interviews · 4.8 Questionnaire · 4.9 Data Collection · 4.10 Data Analysis · 4.11 Ethics · 4.12 Threats to Validity |
| 5 | System Requirements | **Xinyan** | 5.1 Functional · 5.2 Non-Functional · 5.3 User · 5.4 Machine · 5.5 Security · 5.6 Regulatory |
| 6 | System Architecture | Kevin | 6.1 Overall · 6.2 Hardware · 6.3 Software · 6.4 Blockchain & Payment & Data Flow |
| 7 | Prototype Development | Kevin (partial) | 7.1–7.8 (existing) · 7.9–7.13 TBD |
| 8 | Payment Mechanisms | TBD | 8.1 Traditional · 8.2 GPS-Triggered · 8.3 AI Agent · 8.4 x402 · 8.5 Escrow · 8.6 Event-Driven · 8.7 Comparative |
| 9 | Experimental Design | TBD | 9.1 Environment · 9.2 Indoor · 9.3 Outdoor · 9.4 Scenarios · 9.5 Success Criteria · 9.6–9.10 Metrics & Testing |
| 10 | Experimental Results | TBD | 10.1 TX Performance · 10.2 GPS Accuracy · 10.3–10.9 Comm/Blockchain/Payment/Energy/Latency/Failure/Stats |
| 11 | Comparative Evaluation | TBD | 11.1 GPS vs x402 · 11.2 Autonomous vs Human · 11.3 Blockchain vs Traditional · 11.4 Solana vs Alternatives · 11.5 Related Work · 11.6 Cost |
| 12 | Security Analysis | **Yash** | 12.1 Threat Model · 12.2 GPS Spoofing · 12.3 Wallet · 12.4 Key Protection · 12.5 Smart Contract · 12.6–12.10 Network/Replay/Sybil/AI/Mitigation |
| 13 | Reliability and Robustness | TBD | 13.1 Fault Tolerance · 13.2 Recovery · 13.3 Redundancy · 13.4 Scalability · 13.5 Availability · 13.6 Maintainability |
| 14 | Legal, Ethical & Societal | **Yash** | 14.1 Legal Personhood · 14.2 Liability · 14.3 Human Oversight · 14.4 Privacy · 14.5 Regulatory · 14.6 Ethics · 14.7 Employment · 14.8 Acceptance |
| 15 | Business & Economic Analysis | **Yash** | 15.1 Market · 15.2 Business Models · 15.3 Cost-Benefit · 15.4 SWOT · 15.5 Barriers · 15.6 Industry · 15.7 Economic Impact · 15.8 Future Market |
| 16 | Discussion | TBD | 16.1 Results · 16.2 Research Contributions · 16.3 Scientific · 16.4 Technical · 16.5 Practical · 16.6 Limitations · 16.7 Lessons |
| 17 | Future Work | TBD | 17.1 Autonomous Drone · 17.2 AI-Agent · 17.3 Multi-Agent · 17.4 Cross-Chain · 17.5 Marketplaces · 17.6 Machine Identity · 17.7 Large-Scale |
| 18 | Conclusion | TBD | 18.1 Summary · 18.2 Answers to RQ · 18.3 Contributions · 18.4 Closing |

*Detailed breakdown & GitLab work items: https://docs.google.com/document/d/1wvbvqWtbmJVxRuOWr4nrCI1FpnJ7VJlhOxUPSsQWCwc/edit*

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
