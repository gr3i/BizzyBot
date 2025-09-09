import time
import textwrap
import discord
from discord.ext import commands

# ID kanalu kde ma bot reagovat
TARGET_CHANNEL_ID = 1358876461825523863

# klicova slova na ktera bot reaguje
KEYWORDS = {"problém", "problem", "pomoc", "nejde", "nefunguje", "verify",
            "/", "ver", "věř", "kod", "kód", "mail", "doš", "dos"}

# casova prodleva mezi odpovedmi aby bot nespamoval
COOLDOWN_SECONDS = 5 * 60 * 60 # 5 hodin

# na koho nereagovat
IGNORED_ROLE_IDS = {1358898283782602932, 1359508102222975087, 1370841996977246218, 1370842282084925541, 
                    1370842977479692338, 1370843216898953307}     # napr. role MOD
IGNORED_USER_IDS = {685958402442133515}      # konkretni uzivatel

content = textwrap.dedent("""
### Nejčastější problém?
**Nenapsal jsi lomítko! `/` Tam teprve vložíš mail!**

Zda ti to furt nejde, tak to zkusíme ještě jednou.
Postup je fakt jednoduchý.

### ✅ Jak se ověřit
1. Napiš lomítko **`/`** a najdi `/verify`
2. Tam zadej svůj školní e-mail (`123456@vutbr.cz`)
3. Otevři Outlook → najdi e-mail s kódem (často ve **spamu**)
4. Napiš znovu lomítko **`/`** a najdi `/verify_code`
5. Po tomto získáš přístup na server

---

## ℹ️ Jsi původně z FITu?
* Pokud máš školní e-mail ve formátu podobný **xlogin00@vutbr.cz**, použij ten – dostaneš roli *Host*.
* Pro roli *VUT* budeš muset kontaktovat někoho z mods.

Teprve když nic z tohoto nepomůže, napiš někomu z MOD týmu: MOD • Shadow MOD • Shadow SubMOD.
""").strip()


class KeywordHelper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_trigger_ts: float = 0.0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            # ignoruj zpravy od botu a soukrome zpravy
            if message.author.bot or not message.guild:
                return

            # ignoruj vyjmenovane UZIVATELE
            if message.author.id in IGNORED_USER_IDS:
                return

            # ignoruj zpravy od uzivatelu s vyjmenovanymi ROLEMI
            # (autor je Member -> ma .roles; DM uz jsme vyloucili)
            if any(role.id in IGNORED_ROLE_IDS for role in getattr(message.author, "roles", [])):
                return

            # kontrola ze zprava je v cilovem kanale nebo jeho rodici (napr. thread)
            parent_id = getattr(message.channel, "parent_id", None)
            if message.channel.id != TARGET_CHANNEL_ID and parent_id != TARGET_CHANNEL_ID:
                return

            # cooldown proti spamu
            now = time.time()
            if now - self._last_trigger_ts < COOLDOWN_SECONDS:
                return

            # kontrola zda text obsahuje nejake klicove slovo
            text = (message.content or "").lower()
            if any(k in text for k in KEYWORDS):
                await message.reply(content, mention_author=True)
                self._last_trigger_ts = now

        except discord.Forbidden:
            # bot nema prava posilat zpravy v kanalu
            pass
        except Exception as e:
            # zachyti jinou chybu a vypise ji do konzole
            print(f"on_message error: {e}")


# registrace cogu do bota
async def setup(bot: commands.Bot):
    await bot.add_cog(KeywordHelper(bot))

