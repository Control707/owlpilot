# OwlPilot 🦉

**A personal academic co-pilot for D2L Brightspace.** OwlPilot reads your courses from D2L (read-only), then gives you:

- a calendar of every due date,
- a mistake log built from graded work below 80%,
- per-course grade overviews,
- review guides that cite your actual course data.

It runs entirely on your own computer. The page is hosted by **[It](https://github.com/Aaryan-Kapoor/it)**, which also stores everything in a local database. A small Python worker handles every button click in the background.

> Built for Kennesaw State University's D2L (`kennesaw.view.usg.edu`). Other schools on D2L Brightspace can use it by setting one environment variable (see [Using another school's D2L](#using-another-schools-d2l)).

---

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Step by step](#step-by-step)
- [Pairing your browser (the "Connect this browser" screen)](#pairing-your-browser)
- [Daily use](#daily-use)
- [What each screen does](#what-each-screen-does)
- [Review guides](#review-guides)
- [Commands reference](#commands-reference)
- [Troubleshooting](#troubleshooting)
- [Privacy and safety](#privacy-and-safety)
- [Project layout](#project-layout)
- [Development and tests](#development-and-tests)
- [License](#license)

---

## How it works

```
 Your browser ──(paired)──▶ It (localhost:4700) ◀──▶ It's local database
                                   ▲
                       button clicks│ & page state
                                   ▼
                       OwlPilot worker (Python)
                         ├─ D2L: you sign in once; reads via D2L's own API (GET only)
                         └─ Review guides: written by Claude Code from cited course data
```

1. **It** shows the OwlPilot page and stores its data. It only answers on this computer.
2. When you click a button, the page sends an *action* to It. The **worker** picks it up within about 2 seconds, validates it, does the work, and saves the result back. The page then updates by itself.
3. For **D2L**, a browser window opens and you sign in yourself, including SSO and Duo. Your login session is saved in `data/d2l/session.json` on your computer, and OwlPilot uses it only to *read* your courses.

## Requirements

| What | Version / notes |
|---|---|
| macOS or Linux | Windows: run inside WSL. It supports Windows natively, but the scripts here are shell scripts. |
| Python | 3.11 or newer (`python3 --version`) |
| curl | Preinstalled on macOS and most Linux distributions |
| Internet | Needed for setup (It downloads a ~60 MB backend the first time) and for D2L |
| Optional: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Needed for one-click review guides. Install it and sign in once by running `claude`. |

You do **not** need Node.js, Docker, or a database.

## Quick start

```sh
git clone https://github.com/Control707/owlpilot.git
cd owlpilot
./scripts/setup.sh          # one time: installs It, Python packages and a browser, all inside this folder
./scripts/start.sh          # starts OwlPilot; keep this terminal open
```

Then, in a **second terminal**, from the `owlpilot` folder:

```sh
IT_HOME="$PWD/.tools/it" .tools/it/bin/it site
```

That opens a link that **pairs your browser** with It. Then open **http://localhost:4700/p/owlpilot** and go to **Settings → Sign in to D2L**.

## Step by step

### 1. Clone the repository

```sh
git clone https://github.com/Control707/owlpilot.git
cd owlpilot
```

Run every command below from this `owlpilot` folder.

### 2. Run setup (one time)

```sh
./scripts/setup.sh
```

This script:

- Downloads and installs **It v0.1.45** into `.tools/it/`. It does **not** change your shell profile or `PATH`, and it does not install a login service.
- Runs `it setup --none --no-service`. This sets It up on your computer without connecting any agent add-ons or adding a background service.
- Turns off It's usage reporting and update checks.
- Creates a Python virtual environment in `.venv/` and installs `pypdf` and `playwright`.
- Installs a Chromium browser for the D2L sign-in window.

If you get "permission denied", run `chmod +x scripts/*.sh` and try again.

### 3. Start OwlPilot

```sh
./scripts/start.sh
```

Keep this terminal open. It starts **It** and the **OwlPilot worker**, and the first time it also publishes the page. Press **Ctrl-C** to stop both.

### 4. Pair your browser

See [Pairing your browser](#pairing-your-browser) below. You do this once per browser.

### 5. Open OwlPilot and connect D2L

1. Open **http://localhost:4700/p/owlpilot**.
2. Go to **Settings** and click **Sign in to D2L**.
3. A browser window opens on your D2L. Sign in as you normally would. The window closes by itself once OwlPilot can read your courses, usually within a few seconds of finishing Duo.
4. Your courses, due dates, grades and announcements appear. Look for **"D2L synced"** in the sidebar.

From then on, OwlPilot re-syncs automatically, every 6 hours by default; you can change this in Settings. You can also click **Sync D2L** at any time.

## Pairing your browser

The first time you open `http://localhost:4700/p/owlpilot` in a browser, you'll see It's **"Connect this browser"** screen. This is expected. It only shows pages in browsers that you have paired, so that other apps or websites can't read your data.

To pair, open a **second terminal** in the `owlpilot` folder and run:

```sh
IT_HOME="$PWD/.tools/it" .tools/it/bin/it site
```

This opens a pairing link in your default browser. To pair a **different** browser, print the link without opening it, then paste it into that browser:

```sh
IT_HOME="$PWD/.tools/it" .tools/it/bin/it site --no-open
```

It prints something like:

```json
{ "url": "http://localhost:4700/pair#abcdefghijklmnopqrst" }
```

Open that URL in the browser you want to pair, then reload `http://localhost:4700/p/owlpilot`. Alternatively, type the 20-letter code after `#` into the box on the "Connect this browser" screen.

**Why not just `it site`, as the screen says?** OwlPilot installs It *inside the project*, so the `it` command is not on your `PATH`. Always run it as `.tools/it/bin/it`, with `IT_HOME="$PWD/.tools/it"` in front so it uses this project's It. Pairing links are single-use and expire quickly; if one fails, generate a new one.

## Daily use

```sh
cd owlpilot
./scripts/start.sh
```

Then open http://localhost:4700/p/owlpilot. Your browser stays paired between restarts, and all your data is kept.

- **Assistant online / offline** (top bar): shows whether the worker is running. If it says offline, `start.sh` isn't running.
- If your D2L sign-in expires, the D2L card says so. Click **Sign in to D2L** again.
- Stop everything with **Ctrl-C** in the `start.sh` terminal.

## What each screen does

| Screen | What you see / can do |
|---|---|
| **Overview** | Your next deadline, the count due in the next 7 days, course tiles with grade averages, recent announcements and assistant activity |
| **Courses** | Every D2L course, with tabs for **Coming up** (due dates), **Announcements**, **Grades** (released scores and feedback), **Topics** (module outline) and **Materials** (add your own notes or PDFs) |
| **Calendar** | A week view of every assignment and quiz deadline, with previous and next week |
| **Assistant activity** | A history of every sync, guide and edit, including failures and the reason |
| **Approvals** | Items OwlPilot extracted from files *you* uploaded, waiting for you to confirm or reject. D2L data is used directly. |
| **Mistake log** | Graded items below 80% are added automatically after each sync. Add a note on what went wrong, hide an entry, or log a mistake yourself. |
| **Review guides** | One guide per course: focus topics, advice from your mistakes, ungraded practice questions, a checklist and evidence gaps. Each claim has a **source** link to the D2L data it came from. |
| **Grades & progress** | Released-grade averages per course, with every graded item. This is *not* your official GPA, because instructors weight categories differently. |
| **Rules & boundaries** | What OwlPilot does and never does |
| **Settings** | D2L connection and **Sync now**, the auto-sync interval, and who writes review guides |

## Review guides

Click **Generate review guide** on the Review guides screen. The worker:

1. Collects that course's synced D2L data and your mistake-log entries, including your notes.
2. Asks **Claude Code** (`claude -p`, with all tools disabled) to write a guide that cites only that evidence.
3. Checks every citation against the real course data, then saves the guide. This usually takes under a minute.

If Claude Code isn't installed, signed in, or available (for example, if you've hit its usage limit), the guide shows **Failed** with the reason. Nothing is made up.

**To use a different AI agent instead**, go to Settings → **Review guides written by → My chat agent**. Clicks on Generate then wait in It. Open this folder in your agent (Claude Code, Codex, DeepSeek Harness, …) and say **"process OwlPilot"**. [AGENTS.md](AGENTS.md) tells the agent exactly what to do.

## Commands reference

Run all of these from the `owlpilot` folder.

| Task | Command |
|---|---|
| One-time setup | `./scripts/setup.sh` |
| Start OwlPilot | `./scripts/start.sh` |
| **Pair a browser** | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it site` |
| Print a pairing link (no browser) | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it site --no-open` |
| Is It running? | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it status` |
| See the page's stored data | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it state owlpilot` |
| Republish the page after editing `app/` | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it update owlpilot --dir app` |
| Run It alone | `IT_HOME="$PWD/.tools/it" .tools/it/bin/it serve` |
| Run the worker alone | `.venv/bin/python -m owlpilot.worker` |
| Process waiting clicks once, then exit | `.venv/bin/python -m owlpilot.worker --once` |
| Sign in to D2L from the terminal | `.venv/bin/python -m owlpilot.d2l login` |
| Run tests | `.venv/bin/python -m unittest discover -s tests` |

**Tip:** to type `it` instead of the full path in the current terminal, run:

```sh
export IT_HOME="$PWD/.tools/it"; export PATH="$IT_HOME/bin:$PATH"
```

## Troubleshooting

**"Connect this browser" screen.** Your browser isn't paired. See [Pairing your browser](#pairing-your-browser).

**`it: command not found`.** That's expected, because It is installed inside the project. Use `.tools/it/bin/it` with `IT_HOME="$PWD/.tools/it"` in front, or apply the PATH tip above.

**The page won't load at all (connection refused).** It isn't running. Start `./scripts/start.sh`.

**"Assistant offline" in the top bar.** The worker isn't running. Restart `./scripts/start.sh`. Check `data/worker.log` for errors.

**"It is already running" / "worker is already running elsewhere".** That's fine: an earlier copy is still running, and `start.sh` won't start a duplicate. To start fresh, stop the other copy (Ctrl-C in its terminal), or run `pkill -f owlpilot.worker`.

**D2L says "needs sign-in".** Your D2L session expired. Go to Settings → **Sign in to D2L**.

**The D2L sign-in window doesn't open.** Run `.venv/bin/python -m playwright install chromium`, then try again. To use your own browser instead, set `OWLPILOT_BROWSER` to its path, for example `export OWLPILOT_BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`.

**Review guide "Failed".** Read the reason shown on the page:

- *Could not run*: install Claude Code and run `claude` once to sign in.
- *Usage limit*: wait for the limit to reset, or switch Settings to **My chat agent**.

**A course or due date is missing.** OwlPilot shows courses that are active now, or that ended within the last 3 weeks, up to 8 courses. Items your instructor hid in D2L aren't visible to it. Click **Sync D2L** to refresh.

**Logs.** `data/worker.log` (worker) and `data/it.log` (It).

**Start completely over.** Stop `start.sh`, then delete `data/` and `.tools/it/`, and run `./scripts/setup.sh` again. This erases all OwlPilot data and the D2L sign-in.

## Using another school's D2L

Set the D2L address before starting:

```sh
export OWLPILOT_D2L_URL="https://your-school.brightspace.com"
./scripts/start.sh
```

Due-date times are shown in `America/New_York`. To change this, edit `TZ` in `owlpilot/d2l.py`.

## Privacy and safety

- **Everything stays on your computer.** It answers only on `localhost`, with network sharing off. Course data lives in It's database inside `.tools/it/` and in `data/`, and both are git-ignored.
- **D2L is read-only.** OwlPilot only makes GET requests: courses, assignments, quizzes, announcements, released grades and content outline. It never submits, posts, opens quizzes, or changes anything.
- **Your password is never seen.** You sign in to D2L yourself in a normal browser window. Only the resulting session cookie is saved, in `data/d2l/session.json` with owner-only permissions. **Never commit or share the `data/` folder.**
- **AI use.** When you generate a review guide, relevant excerpts of that course's data are sent to the AI provider behind Claude Code (or your chosen agent). Nothing is sent otherwise.
- **No graded work.** Guides are study aids with ungraded practice. OwlPilot will not write or submit assignments.

## Project layout

```
app/                 The OwlPilot page (vanilla HTML/CSS/JS) that It publishes
  index.html
  owlpilot.js        All screens; reads It state, sends actions with It.action
  style.css
owlpilot/            Python package
  core.py            Validates every action; builds revision-checked patches for It's state
  d2l.py             D2L sign-in and read-only sync; maps courses, due dates, grades and modules
  worker.py          Background loop: takes actions from It, runs them, writes results back
  __main__.py        CLI: python -m owlpilot initial|handle|context|complete
scripts/
  setup.sh           One-time install (It, Python environment, browser)
  start.sh           Starts It and the worker; publishes the page
tests/               Unit tests (python -m unittest)
fixtures/            Synthetic sample course notes for testing imports
AGENTS.md            Instructions for an AI agent operating OwlPilot ("process OwlPilot")
GLOSSARY.md          Domain vocabulary
owlpilot_academic_co_pilot.html   Original static design prototype (reference)
.scratch/owlpilot/   Design decisions, spec and build plan (Wayfinder map)
```

**Not in the repository** (created locally, git-ignored): `.tools/` (It install and database), `.venv/`, and `data/` (D2L session, snapshots, materials, logs).

## Development and tests

```sh
.venv/bin/python -m unittest discover -s tests     # 33 tests: validation, D2L mapping, guides
```

After editing anything in `app/`, republish the page. Open browsers reload automatically:

```sh
IT_HOME="$PWD/.tools/it" .tools/it/bin/it update owlpilot --dir app
```

After editing Python code, restart `./scripts/start.sh`.

How data flows: page actions → `owlpilot/worker.py` → `core.handle_action` or `d2l.apply_snapshot` validate them and compute a merge patch → `it patch owlpilot --if-revision N` saves it. A concurrent edit is detected and retried, never overwritten.

## License

OwlPilot's own code is released under the MIT License (see [LICENSE](LICENSE)).

**It** is a separate, source-available program by Aaryan Kapoor with its own [license](https://github.com/Aaryan-Kapoor/it/blob/master/docs/licensing.md). It is **not** included in this repository: `setup.sh` downloads it from its official releases. Personal, non-commercial use is permitted. Read its terms before using It for an organization or offering it as a service.
