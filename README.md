# BUT FP Discord Bot

A custom Discord bot developed for the **Brno University of Technology – Faculty of Business and Management (BUT FP)** Discord server.

It handles user verification via email, assigns roles based on user input or email domain, and provides several moderation and management utilities for streamlined community onboarding.

---

## 📌 Features

* 🔐 **Email Verification**
  Users must verify their identity using a university email. Only **one user per email address** is allowed.

* 🎓 **Automatic Role Assignment**
  Upon successful verification, users are granted:

  * A general `Verified` role.
  * A specific role based on their email domain (`VUT` for university emails, `Host` for others).

* 📘 **Subject and Faculty Role Selection**
  Users can select their **subjects** and **faculty affiliation** using reaction-based messages.

* 🛠️ **Owner-Only Commands**
  Admins can manage the bot and users via several restricted commands:

  * Send announcements as the bot
  * View user verification status
  * Remove verification and assigned roles

---

## 🧩 Project Structure

```
project/
│
├── cogs/                     # Modular command handlers (hello.py, verify.py, etc.)
├── db/
│   ├── db_setup.py           # DB schema and initialization
│   └── database.py           # Connection handling
├── utils/
│   ├── codes.py              # Verification code generator
│   ├── mailer.py             # Email-sending logic
│   ├── reaction_ids.json     # Stores tracked message IDs for reactions
│   └── subject_management.py # Slash command definitions for subjects
├── bot.py                    # Bot entry point
└── longmessage_for_bot.txt   # Optional file used for long-form bot messages
```

---

## 📦 Requirements

* Python
* SQLite 
* `.env` file in the root directory with your bot token:

  ```env
  DISCORD_TOKEN=your_token_here
  ```
* SMTP credentials configured inside `utils/mailer.py` for sending emails.

### Python Packages

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Bot

```bash
python bot.py
```

---

## ✅ Commands Overview

### Slash Commands

| Command               | Description               |
| --------------------- | ------------------------- |
| `/verify <email>`     | Starts email verification |
| `/verify_code <code>` | Verifies the entered code |
There are more commands on the Discord server.

### Text Commands (Owner-only)

| Command                    | Description                                     |
| -------------------------- | ----------------------------------------------- |
| `!writeasbot <text>`       | Bot sends a message as itself                   |
| `!writeasbot_longmessage`  | Sends the contents of `longmessage_for_bot.txt` |
| `!whois <user_id>`         | Displays verification info about a user         |
| `!strip <user_id>`         | Removes user's email and roles from database    |
| `!create_subject_messages` | Create subject selection messages               |
| `!vut_roles`               | Sends VUT faculty role selection message        |

---

## 🛡️ Security

* Only one user can verify using a specific email address.
* Commands like `strip`, `writeasbot`, and `whois` are restricted to the bot owner or a privileged role.

---

## 📩 Contact

For inquiries, suggestions, or bug reports, please contact the [gr3i on GitHub](https://github.com/gr3i) or open an issue on GitHub.

---

## 🧪 TODO / Ideas

* Add logging system (audit trail)
* Web interface for managing verified users
* Rate limiting to avoid abuse of verification

---

## 🏫 Developed for

**BUT FP – Brno University of Technology, Faculty of Business and Management**
Discord server community automation and verification system.
