# job-radar

[![CI](https://github.com/daria-sobko-dev/job-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/daria-sobko-dev/job-radar/actions/workflows/ci.yml)

A small automation that checks job boards every morning, scores new vacancies against my profile and sends the best matches to Telegram. It runs on a GitHub Actions schedule, so there is no server to maintain.

```
 GitHub Actions (cron, daily)
          │
          ▼
 ┌─────────────────┐   DOU RSS feeds
 │  collect()      │◄─ Greenhouse Job Board API
 │                 │◄─ Lever Postings API
 └────────┬────────┘
          │ keep jobs published in the last 26h, de-duplicate by URL,
          │ drop jobs seen before (data/seen.json)
          ▼
 ┌─────────────────┐
 │  score()        │  hard filters: role in title, no senior/lead, allowed location
 │                 │  score: weighted skills + title bonus + text penalties
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Telegram bot   │  one digest grouped by profile, split under the 4096-character limit
 └────────┬────────┘
          ▼
 commit data/seen.json back to the repo, so each job is reported once
```

## Example message

```
Job Radar · 2026-11-10
2 match(es) out of 37 new vacancies

14 · Junior DevOps Engineer
Acme Cloud · Київ, віддалено
Skills: aws, terraform, linux, docker, ci/cd, github actions, python, bash
Notes: junior +3

9 · DevOps Engineer - Credit Cards
DKB Code Factory · Valencia, Spain
Skills: aws, terraform, kubernetes, helm, prometheus, grafana, postgresql
```

## Design choices

- **Configuration over code.** Sources, filters and skill weights live in `config.yaml`. Changing what counts as a good match never needs a code change.
- **Several directions at once.** `profiles` holds one block per direction (here DevOps / Cloud and Web / PHP / Frontend). Shared rules such as red flags and locations live once in `filters`. A vacancy is reported once, under the profile where it scores best.
- **Idempotent runs.** Every processed job is recorded in `data/seen.json`, so re-running the workflow does not resend old vacancies. The file is pruned after 90 days.
- **Failure isolation.** A broken feed is logged and listed at the bottom of the digest; the other sources still run. The workflow fails only if every source fails.
- **Secrets stay in GitHub.** The bot token and chat id are repository secrets, never in the code or the logs. Error messages never print the Telegram URL, because it contains the token.
- **Public APIs only.** DOU RSS, the Greenhouse Job Board API and the Lever Postings API are public and need no keys. Sites without a public API (LinkedIn, Workday) are out of scope.

## Setup

1. **Create a bot.** In Telegram, talk to `@BotFather`, send `/newbot`, and copy the token.
2. **Get your chat id.** Send any message to your new bot, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `message.chat.id`.
3. **Add repository secrets** in *Settings → Secrets and variables → Actions*:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. **Edit `config.yaml`**: feeds, companies, skills and filters.
5. **Run it once by hand**: *Actions → Daily digest → Run workflow*. Tick *dry run* first to see the digest in the log, then run it for real.

After that it runs every day at 06:17 UTC.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m jobradar --dry-run --explain   # print the digest and why each job passed or failed
pytest                                   # tests use fixtures, no network
ruff check . && ruff format --check .
```

To send a real message from your machine:

```bash
export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python -m jobradar --ignore-state
```

## Build the profile from a resume

The `skills` block in `config.yaml` can be generated from a resume instead of written by hand:

```bash
python -m jobradar.resume ~/Documents/resume.pdf                          # preview, devops profile
python -m jobradar.resume ~/Documents/resume.pdf --profile web --write    # update the web profile
```

The tool extracts the text (PDF, TXT or Markdown), looks for skills from the profile's vocabulary in `jobradar/vocabulary.py` (infrastructure for `devops`, web technologies for `web`) and counts mentions. Skills mentioned three or more times get weight 2, the rest weight 1. Only the block between `# BEGIN skills <profile>` and `# END skills <profile>` is replaced, so every other setting and comment stays as it is. Aliases are matched too: a `kubernetes` skill also matches `k8s` in a vacancy.

The resume itself is not committed: it contains personal contact details.

## Configuration

| Key | Meaning |
|---|---|
| `sources.dou` | DOU RSS feed URLs. Set filters on jobs.dou.ua and copy the RSS link. |
| `sources.greenhouse` | `board` is the part after `job-boards.greenhouse.io/`. |
| `sources.lever` | `company` is the part after `jobs.lever.co/`. |
| `filters.red_flags` | A vacancy mentioning any of these anywhere is skipped (e.g. iGaming, unpaid). |
| `filters.allowed_locations` | Title or location must contain one of these. |
| `filters.location_bonus` | Extra points for locations such as Spain or "work from abroad". |
| `filters.penalties` | Points removed for phrases in the text. |
| `profiles.<name>.label` | Section heading in the digest. |
| `profiles.<name>.title_keywords` | The title must contain one of these. |
| `profiles.<name>.exclude_title` | Titles with any of these are skipped. |
| `profiles.<name>.skills` | Skill → weight, matched anywhere in the vacancy (aliases included). |
| `profiles.<name>.title_bonus` | Extra points for words in the title. |
| `profiles.<name>.min_score` | Minimum score to be included. |
| `max_age_hours` | Only jobs published in the last N hours (jobs without a date are kept). |
| `digest.max_items` | Top N matches per profile per day. |
| `digest.send_when_empty` | Send a short message even when nothing matched. |

## Project layout

```
jobradar/
  sources/        dou.py, greenhouse.py, lever.py  (fetch + pure parse functions)
  scoring.py      filters and scoring
  resume.py       generate the skills block from a resume
  vocabulary.py   known skills and their aliases
  state.py        seen-jobs store with pruning and atomic writes
  telegram.py     message formatting, escaping, splitting, sending
  main.py         CLI and orchestration
tests/            pytest with recorded fixtures, no network
.github/workflows ci.yml (lint + tests), digest.yml (daily schedule)
```

## Notes

- GitHub may pause scheduled workflows in repositories with no activity for 60 days. The daily state commit usually keeps the repository active; if the schedule is paused, re-enable it in the Actions tab.
- Scheduled runs can start a few minutes late when GitHub is busy.
