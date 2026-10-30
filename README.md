# BUT FBM Discord Bot

[License: MIT](https://opensource.org/licenses/MIT)

A custom Discord bot developed for the **Brno University of Technology – Faculty of Business and Management (BUT FBM)** Discord server.

It handles user verification via email, assigns roles based on user input or email domain, and provides several moderation and management utilities for streamlined community onboarding.

## Link

**[https://discord.gg/TnDwKvSPHG](https://discord.gg/TnDwKvSPHG)**

---

## Features

### Email Verification

Users must verify their identity using a university email. Only one user per email address is allowed.

### Automatic Role Assignment

Upon successful verification, users are granted:

* A general `Verified` role
* A specific role based on their email domain (`VUT`/`FP`/`Doktorand`/`Vyucujici/Zamestnanec` for university emails, `Host` for others)
* When a user receives the `FP` role, they will also get their corresponding year role.

### TODO Onboarding

After verification and receiving their role, the bot sends users a TODO checklist via DM to help them navigate the server.

### Owner-Only Commands

Admins can manage the bot and users via restricted commands:

* Send announcements as the bot
* View user verification status
* Remove verification and assigned roles

---

## Project Structure

```
BizzyBot/
│
├── cogs/                     # Slash command groups (verify, botInfo, reviews, etc.)
├── db/                       # SQLAlchemy ORM models and session
│   ├── models.py
│   └── session.py
├── utils/
│   ├── mailer.py             # sends verification code on mail
│   └──  vyber_oboru.py       # faculty role selection
├── bot.py                    # Run a bot (main)
└── ...
```

---

## Requirements & Technologies

* Python 3.11+
* discord.py 2.x
* SQLAlchemy (ORM)
* SQLite (default DB) – stored as `app.db`
* Docker + Docker Compose
* `.env` file with configuration:

```
DISCORD_TOKEN=your_token_here
GUILD_ID=123456789012345678
```

SMTP credentials are configured inside `utils/mailer.py` for sending emails.

### Install dependencies

```
pip install -r requirements.txt
```

---

## Running the Bot

### Local

```
python bot.py
```

### Docker

```
docker compose up --build -d
```

---

## Commands Overview

### Slash Commands

| Command               | Description                         |
| --------------------- | ----------------------------------- |
| `/verify vut`         | Start verification as VUT user      |
| `/verify host`        | Start verification as host          |
| `/verify code <code>` | Finish verification                 |
| `/room`               | Find a room at the faculty          |
| `/obor`               | Set your major                      |
| `/hodnoceni ...`      | Manage reviews                      |
| `/bot info`           | Show bot stats (latency, RAM, etc.) |
| `/pozvanka`           | QR code with invite link            |

### Prefix Commands (Owner-only + MODs)

| Command                   | Description                                |
| ------------------------- | ------------------------------------------ |
| `!whois <user_id>`        | Show user’s verification status and email  |
| `!strip <user_id>`        | Remove verification and all roles          |

---

## Security

* One email → one user (unique verification)
* Owner-only commands restricted by ID or privileged role
* Reviews can only be deleted or edited by author, moderators, or owner
* TODO DM is sent only once per session to prevent spam

---

## Contact

For inquiries, suggestions, or bug reports, please contact [gr3i](https://github.com/gr3i) on GitHub or open an issue on GitHub.

---

## IB

[Rubbergod Bot (BUT FIT Discord)](https://github.com/vutfitdiscord/rubbergod/tree/main)
