import time
import textwrap
import discord
from discord.ext import commands

# ID kanalu kde ma bot reagovat
TARGET_CHANNEL_ID = 1358876461825523863

# klicova slova na ktera bot reaguje
# POZN.: "/" jsem odstranil, aby se to nespoustelo na URL apod.
KEYWORDS = {"problém", "problem", "pomoc", "nejde", "nefunguje", "verify",
            "ver", "věř", "kod", "kód", "mail", "doš", "dos"}

# casova prodleva mezi odpovedmi aby bot nespamoval
COOLDOWN_SECONDS = 5 * 60 * 60  # 5 hodin

# na koho nereagovat
IGNORED_ROLE_IDS = {
    1358898283782602932, 1359508102222975087, 1370841996977246218,
    1370842282084925541, 1370842977479692338, 1370843216898953307
}  # napr. role MOD
IGNORED_USER_IDS = {685958402442133515}  # konkretni uzivatel

content = textwrap.dedent("""
### Nejčastější problém?
**Nenapsal*a jsi lomítko! `/` Tam teprve vložíš údaje...**
Link na cringe staré video, jak napsat lomítko: https://discord.com/channels/1357455204391321712/1407119813146443778/1434342560951963779 

Zda ti to furt nejde, tak to zkusíme ještě jednou.
Postup je fakt jednoduchý.

### ✅ Jak se ověřit
1. Napiš lomítko **`/`** a najdi `/verify vut`.
2. Tam zadej svoje VUT ID (To je to 6-místné číslo, např.654321) nebo VUT login (např.xlogin00).
3. Otevři Outlook → najdi e-mail s kódem (často ve **spamu**).
4. Napiš znovu lomítko **`/`** a najdi `/verify code`, kde zadáš kód z mailu.
5. Po tomto získáš přístup na server.

---

## ℹ️ Stále se ti nedaří verifikovat na server a máš VUT mail?
* Pokud máš školní e-mail ve formátu podobný **123456@vut.cz** nebo **xlogin00@vutbr.cz**, tak ho zadej do příkazu `/verify host`  – dostaneš roli *Host*.
* Pro roli *VUT* budeš muset kontaktovat někoho z mods.

Teprve když nic z tohoto nepomůže, napiš někomu z Mods.
""").strip()


class KeywordHelper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # per-uzivatel cooldown casy (timestamp z time.monotonic)
        self._last_by_user: dict[int, float] = {}

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
            if any(role.id in IGNORED_ROLE_IDS for role in getattr(message.author, "roles", [])):
                return

            # kontrola ze zprava je v cilovem kanale nebo jeho rodici (napr. thread)
            parent_id = getattr(message.channel, "parent_id", None)
            if message.channel.id != TARGET_CHANNEL_ID and parent_id != TARGET_CHANNEL_ID:
                return

            # kontrola zda text obsahuje nejake klicove slovo
            text = (message.content or "").lower()
            triggered = (
                any(k in text for k in KEYWORDS)
                or "/verify" in text
                or "/verify_code" in text
            )
            if not triggered:
                return

            # cooldown proti spamu (per-uzivatel)
            now = time.monotonic()
            last = self._last_by_user.get(message.author.id, 0.0)
            if now - last < COOLDOWN_SECONDS:
                return
            self._last_by_user[message.author.id] = now

            await message.reply(content, mention_author=True)

        except discord.Forbidden:
            # bot nema prava posilat zpravy v kanalu
            pass
        except Exception as e:
            # zachyti jinou chybu a vypise ji do konzole
            print(f"on_message error: {e}")


# registrace cogu do bota
async def setup(bot: commands.Bot):
    await bot.add_cog(KeywordHelper(bot))

