# 🏫 Discord BOT developed for BUT FP

BUT FP – Brno University of Technology, Faculty of Business and Management
Discord server community automation and verification system.

A custom Discord bot developed for the Brno University of Technology – Faculty of Business and Management (BUT FP) server.  
It handles user verification via email, role assignment via reactions, and provides several moderation and utility commands tailored for university use.

---

## 📌 Features

- 🔐 **Email Verification**  
  Users must verify their email to access the full server. Only one email can be used per user.

- 🎓 **Automatic Role Assignment**  
  Upon verification, users are granted:
  - A general `Verified` role.
  - A specific role based on their email domain (e.g. `VUT` or `Host`).

- 📘 **Subject and Faculty Role Selection**  
  Users can select their subjects (e.g. Mikroekonomie, Účetnictví) and faculty (e.g. FIT, FSI) by reacting to messages with specific emojis.

- 🛠️ **Owner-Only Commands**  
  Includes commands for:
  - Sending messages as the bot.
  - Manually stripping verification.
  - Querying user verification status.

---

## 🧩 Structure
BizzyBot/
│
├── cogs/ # Modular Discord bot components (e.g. hello.py, role.py, verify.py)
├── db/
│ ├── db_setup.py # Database initialization
│ └── database.py # DB connection
├── utils/
│ ├── codes.py # Verification code generator
│ ├── mailer.py # Email sending utility
│ ├── reaction_ids.json # Stores message IDs used for reaction-based role assignment
│ └── subject_management.py
├── bot.py # Entry point for the bot
└── longmessage_for_bot.txt # Optional file used for long-form bot messages

---

## 📦 Requirements

- Python 3.10+
- SQLite
- `.env` file containing:
DISCORD_TOKEN=your_token_here

- SMTP credentials configured inside `utils/mailer.py` for sending emails.

### Python Packages

Install dependencies with:

```bash
pip install -r requirements.txt

## 🚀 Running the Bot
python bot.py

✅ Commands Overview
Slash Commands
| Command               | Description               |
| --------------------- | ------------------------- |
| `/verify <email>`     | Starts email verification |
| `/verify_code <code>` | Verifies the entered code |

Text Commands (Owner-only)
| Command                    | Description                                     |
| -------------------------- | ----------------------------------------------- |
| `!writeasbot <text>`       | Bot sends a message as itself                   |
| `!writeasbot_longmessage`  | Sends the contents of `longmessage_for_bot.txt` |
| `!whois <user_id>`         | Displays verification info about a user         |
| `!strip <user_id>`         | Removes user's email and roles from database    |
| `!create_subject_messages` | Sends subject selection messages                |
| `!vut_roles`               | Sends VUT faculty role selection message        |

🛡️ Security
- Only one user can verify using a specific email address.
- Commands like strip, writeasbot, and whois are restricted to the bot owner or authorized role.

📫 Contact
For inquiries, suggestions, or bug reports, please contact the gr3i (dat sem odkaz na me) or open an issue on GitHub.
