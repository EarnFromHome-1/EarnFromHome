# TimeCash

A clean Flask implementation of the TimeCash project described in the supplied notebook pages.

## Included from the notebook

- Mobile-first Home / Earn / Withdraw / Admin navigation
- 30,000 UGX registration payment flow
- Payment screenshot upload + admin confirmation
- Registration details: first name, last name, email, password, terms acceptance
- User dashboard with profile, balance and notifications
- Four earning routes: Tasks, Refer & Earn, Games, Lucky Draw
- Task proof upload and pending rewards
- Referral links and 5,000 UGX referral reward setting
- Lucky Draw with ticket collection, 16-hour collection window and 8-hour cooldown
- Daily spin wheel and extra-spin purchase setting
- Tier 2 war games and Tier 3 board games from the notebook
- Voice-chat-enabled labels for multiplayer games (voice transport is intentionally left as a provider integration point)
- Owner dashboard with users, ledgers, budgets, withdrawals and feature hooks
- Configurable Airtel payment number and SMTP email delivery

## Important

This repository uses **manual payment verification** as a safe starting point. It does not pretend that a screenshot proves a mobile-money payment automatically. Connect a legitimate payment provider/API before accepting real money automatically.

The lucky-draw and paid-game features are implemented as project scaffolding and should only be enabled after checking the laws, platform rules, age restrictions, KYC/AML obligations, payment-provider rules and licensing requirements that apply to the launch country.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

## Admin

Set `ADMIN_PASSCODE` in `.env`. The owner dashboard is at `/admin`.

## GitHub

Create a new repository, copy these files into it, commit, and push. Never commit `.env`, the database, uploaded payment screenshots, or real SMTP credentials.
