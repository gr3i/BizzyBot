 # BUT FP Discord Bot [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A custom Discord bot developed for the **Brno University of Technology – Faculty of Business and Management (BUT FP)** Discord server.

It handles user verification via email, assigns roles based on user input or email domain, and provides several moderation and management utilities for streamlined community onboarding.

## 🔗 Link 
**[https://discord.gg/vutfp](https://discord.gg/WAStjDSx8K)**

---

## 📌 Features

* 🔐 **Email Verification** 
  Users must verify their identity using a university email. Only **one user per email address** is allowed. 

* 🎓 **Automatic Role Assignment**
  Upon successful verification, users are granted:

  * A general `Verified` role.
  * A specific role based on their email domain (`VUT` for university emails, `Host` for others).

* 📘 **Subject and Faculty Role Selection**
  Users can select their **subjects** and **faculty affiliation** using reaction-based messages and slash commands.

* ✅ **TODO Onboarding** 
  Right after verification and gaining the VUT role, bot sends a **TODO checklist** via DM to help students navigate the server. 

* 🛠️ **Owner-Only Commands**
  Admins can manage the bot and users via several restricted commands:

  * Send announcements as the bot
  * View user verification status
  * Remove verification and assigned roles

---

## 📂 Project Structure

```
BizzyBot/
│
├── cogs/                     # Slash command groups (verify, botInfo, reviews, etc.)
├── db/                       # SQLAlchemy ORM models and session
│   ├── models.py
│   └── session.py
├── utils/
│   ├── subject_management.py # /predmet group
│   ├── vyber_oboru.py        # faculty role selection
│   ├── nastav_prava.py       # role/permissions script
│   └── reaction_ids.json     # tracked reaction messages
├── bot.py                    # Run a bot (main) 
└── longmessage_for_bot.txt   # Optional file used for long-form bot messages
```

---

## ⚙️ Requirements & Technologies

- Python **3.11+**
- [discord.py 2.x](https://discordpy.readthedocs.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- SQLite (default DB) – stored as `app.db`
- Docker + Docker Compose
- `.env` file with configuration:

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=123456789012345678
```

* SMTP credentials configured inside utils/mailer.py for sending emails.

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Bot

### Local
```bash
python bot.py
```

### Docker
```bash
docker compose up --build -d
```

---

## 📚 Commands Overview

### Slash Commands

| Command                   | Description                          |
| ------------------------- | ------------------------------------ |
| `/verify <email>`         | Start verification                   |
| `/verify_code <code>`     | Finish verification                  |
| `/obor`                   | Set your major                       |
| `/predmet ...`            | Manage your subjects                 |
| `/hodnoceni ...`          | Manage reviews                       |
| `/bot info`               | Show bot stats (latency, RAM, etc.)  |
| `/todo_reset` *(owner)*   | Reset TODO DM cache                  |

### Prefix Commands (Owner-only + MODs)

| Command                   | Description                                   |
| ------------------------- | --------------------------------------------- |
| `!writeasbot <text>`      | Bot sends message as itself                   |
| `!writeasbot_longmessage` | Send contents of `longmessage_for_bot.txt`    |
| `!whois <user_id>`        | Show user’s verification status + email       |
| `!strip <user_id>`        | Remove verification + all roles               |

---

## 🛡️ Security

* ✅ One email → one user (unique verification). 
* ✅ Owner-only commands restricted by **ID** or **privileged role**. 
* ✅ Reviews can only be deleted/edited by **author**, **mods**, or **owner**. 
* ✅ TODO DM is sent only once per session (to prevent spam). 

---

## 📩 Contact

For inquiries, suggestions, or bug reports, please contact the [gr3i](https://github.com/gr3i) on GitHub or open an issue on GitHub.

---

## 📚 IB

[Rubbergod Bot (BUT FIT Discord)](https://github.com/vutfitdiscord/rubbergod/tree/main). 

