# BizzyBot [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A custom Discord bot developed for the **Brno University of Technology – Faculty of Business and Management (BUT FP)** Discord server.  
It provides verification, subject/faculty role management, review system, and utilities to make onboarding smooth & fun.  

## 🔗 Invite
**https://discord.gg/WAStjDSx8K**

---

## ✨ Features

* 🔐 **Email Verification**  
  Verify with your university email to gain access. Each email can only be used once.  

* 🎓 **Automatic Role Assignment**  
  After verification, users receive:
  - General **VUT** role
  - Faculty-specific role
  - Optionally subject roles  

* 📘 **Subject & Faculty Roles**  
  - `/predmet` command for adding/removing subjects  
  - Reaction menu for faculty selection  

* 📝 **Subject Reviews**  
  - `/hodnoceni pridat` – add review for a subject  
  - `/hodnoceni zobrazit` – view reviews with likes/dislikes  
  - `/hodnoceni upravit` & `/hodnoceni smazat` – manage your own reviews  

* ✅ **TODO Onboarding**  
  Right after verification and gaining the VUT role, bot sends a **TODO checklist** via DM to help students navigate the server.  

* 🤖 **Bot Info**  
  - `/bot info` shows latency, uptime, memory usage, and more.  

* 🛠️ **Owner-Only Utilities**  
  - `!writeasbot <text>` – bot sends a custom message  
  - `!writeasbot_longmessage` – send contents of `longmessage_for_bot.txt`  
  - `!whois <user_id>` – see user’s verification status  
  - `!strip <user_id>` – remove verification + roles  

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
│   ├── nastav_prava.py       # role/permissions helpers
│   └── reaction_ids.json     # tracked reaction messages
├── bot.py                    # Main entrypoint
└── longmessage_for_bot.txt   # Optional file for owner commands
```

---

## ⚙️ Requirements

* Python 3.11+
* SQLite (default DB)  
* `.env` file with configuration:

```env
DISCORD_TOKEN=your_token_here
GUILD_ID=123456789012345678
```

* SMTP settings in `utils/mailer.py` (for email verification)

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
| `/predmet ...`            | Manage your subjects                 |
| `/hodnoceni pridat`       | Add subject review                   |
| `/hodnoceni zobrazit`     | Show subject reviews                 |
| `/hodnoceni upravit`      | Edit your review                     |
| `/hodnoceni smazat`       | Delete review                        |
| `/bot info`               | Show bot stats (latency, RAM, etc.)  |
| `/todo_reset` *(owner)*   | Reset TODO DM cache                  |

### Prefix Commands (Owner-only)

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

For issues, suggestions or contributions:  
👉 [gr3i on GitHub](https://github.com/gr3i)  

---

## 📚 Inspiration

Based on [Rubbergod Bot (BUT FIT Discord)](https://github.com/vutfitdiscord/rubbergod/tree/main).  
Extended and customized for **BUT FP**.
