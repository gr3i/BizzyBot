import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from db.db_setup import setup_database
from db.db_setup import create_connection
from utils.subject_management import predmet

"""i have converted this into a class"""


class DiscordBot:
    def __init__(self):
        load_dotenv()
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        setup_database()
        
        self.REACTION_IDS_FILE = "utils/reaction_ids.json"
        
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.reactions = True
        intents.members = True
        intents.message_content = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.reaction_message_ids = []
        
        self.vut_roles_list = [
            ("FP - 1BC", 1359529613428134081),
            ("FP - 2BC", 1359529670109827304),
            ("FP - 3+BC", 1359529713453891627),
            ("FP - 1MGR", 1359529781582102618),
            ("FP - 2+MGR", 1359529858325287012),
            ("FP", 1358915656782844094),
            ("FEKT", 1359530289444946081),
            ("FIT", 1359530329463062678),
            ("FSI", 1359530359045230725),
            ("FA", 1359530388183191582),
            ("FAST", 1359530415970586629),
            ("FCH", 1359597408434126989),
            ("FAVU", 1389930978079801395),
            ("ÚSI", 1389931262525050930),
        ]
        
        self.load_reaction_ids()
        self.setup_events()
        self.setup_commands()
    
    def load_reaction_ids(self):
        if os.path.exists(self.REACTION_IDS_FILE):
            with open(self.REACTION_IDS_FILE, "r") as f:
                self.reaction_message_ids = json.load(f)
                print(f"📌 Načteno {len(self.reaction_message_ids)} zpráv s reakcemi.")
        else:
            print("📌 Soubor s ID zpráv nenalezen.")
    
    def is_owner(self, ctx):
        allowed_ids = [685958402442133515]
        allowed_role_ids = [1358898283782602932]
        
        if ctx.author.id in allowed_ids:
            return True
        
        if any(role.id in allowed_role_ids for role in ctx.author.roles):
            return True
        
        return False
    
    def funkce_vrati_false(self, ctx):
        return False
    
    def setup_events(self):
        @self.bot.event
        async def on_ready():
            print(f"✅ Bot je přihlášen jako {self.bot.user} (ID: {self.bot.user.id})")
            
            for extension in ["cogs.hello","cogs.botInfo", "cogs.verify", "cogs.role", "cogs.reviews", "utils.vyber_oboru", "utils.nastav_prava"]:
                try: 
                    await self.bot.load_extension(extension)
                    print(f"✅ Cog '{extension}' načten.")
                except Exception as e:
                    print(f"❌ Chyba při načítání '{extension}': {e}")
            
            self.bot.tree.add_command(predmet)
            await self.bot.tree.sync()
            print("✅ Slash příkazy synchronizovány.")
        
        @self.bot.event
        async def on_raw_reaction_add(payload):
            if payload.message_id not in self.reaction_message_ids:
                return

            guild = self.bot.get_guild(payload.guild_id)
            if guild is None:
                return

            member = guild.get_member(payload.user_id)
            if member is None or member.bot:
                return

            emoji = str(payload.emoji)

            message = None
            for channel in guild.text_channels:
                try:
                    msg = await channel.fetch_message(payload.message_id)
                    if msg:
                        message = msg
                        break
                except (discord.NotFound, discord.Forbidden):
                    continue

            if message is None:
                return

            if emoji in ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳"]:
                index = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳"].index(emoji)
                list_source = self.vut_roles_list
            else:
                return

            if index < len(list_source):
                role_id = list_source[index][1]
                role = guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    print(f"✅ Přidána role {role.name} uživateli {member.name}")

                    try:
                        await member.send(f"✅ Byla ti přidělena role: {role.name}")
                    except discord.Forbidden:
                        print(f"❗ Nelze poslat DM uživateli {member.name}")
        
        @self.bot.event
        async def on_raw_reaction_remove(payload):
            if payload.message_id not in self.reaction_message_ids:
                return

            guild = self.bot.get_guild(payload.guild_id)
            if guild is None:
                return

            member = guild.get_member(payload.user_id)
            if member is None:
                return

            emoji = str(payload.emoji)

            message = None
            for channel in guild.text_channels:
                try:
                    msg = await channel.fetch_message(payload.message_id)
                    if msg:
                        message = msg
                        break
                except (discord.NotFound, discord.Forbidden):
                    continue

            if message is None:
                return

            if emoji in ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳"]:
                index = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳"].index(emoji)
                list_source = self.vut_roles_list
            else:
                return

            if index < len(list_source):
                role_id = list_source[index][1]
                role = guild.get_role(role_id)
                if role:
                    await member.remove_roles(role)
                    print(f"❌ Odebrána role {role.name} uživateli {member.name}")

                    try:
                        await member.send(f"❌ Byla ti odebrána role: {role.name}")
                    except discord.Forbidden:
                        print(f"❗ Nelze poslat DM uživateli {member.name}")
    
    def setup_commands(self):
        @self.bot.command()
        @commands.check(self.funkce_vrati_false)
        async def vut_roles(ctx):
            emojis = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]
            message_lines = [f"{emojis[i]} {text}" for i, (text, _) in enumerate(self.vut_roles_list)]
            msg = await ctx.send("\n".join(message_lines))
            self.reaction_message_ids.append(msg.id)
            for emoji in emojis[:len(self.vut_roles_list)]:
                await msg.add_reaction(emoji)

            try:
                with open(self.REACTION_IDS_FILE, "w") as f:
                    json.dump(self.reaction_message_ids, f)
                print("💾 VUT role zpráva uložena.")
            except Exception as e:
                print(f"❌ Chyba při ukládání ID zpráv: {e}")

        @vut_roles.error
        async def vut_roles_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("Tento příkaz může použít pouze vlastník bota.")

        @self.bot.command()
        @commands.check(self.is_owner)
        async def writeasbot(ctx, *, text: str):
            await ctx.send(text)

        @writeasbot.error
        async def writeasbot_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("Na tento prikaz nemas opravneni.")

        @self.bot.command()
        @commands.check(self.is_owner)
        async def writeasbot_longmessage(ctx):
            try:
                with open("longmessage_for_bot.txt", "r", encoding="utf-8") as file:
                    content = file.read()
                
                if not content:
                    await ctx.send("Soubor 'bot_write.txt' je prázdný.")
                else:
                    await ctx.send(content)
            
            except FileNotFoundError:
                await ctx.send("Soubor 'bot_write.txt' nebyl nalezen.")
            except Exception as e:
                await ctx.send(f"Došlo k chybě při čtení souboru: {e}")

        @writeasbot_longmessage.error
        async def writeasbot_longmessage_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("Tento příkaz může použít pouze vlastník bota.")

        @self.bot.command()
        @commands.check(self.is_owner)
        async def whois(ctx, user_id: int):
            member = ctx.guild.get_member(user_id)

            if member is None:
                await ctx.send(f"Uživatel s ID {user_id} není na tomto serveru.")
                return

            conn = create_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT mail, verified FROM verifications WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()

            if row is None:
                verification_status = "Ověření nebylo zahájeno."
                user_email = "Neznámý"
            else:
                mail, verified = row
                if verified:
                    verification_status = "Ověřeno"
                else:
                    verification_status = "Neověřeno"
                user_email = mail

            conn.close()

            embed = discord.Embed(title=f"Informace o uživatelském účtu {member.name}", color=discord.Color.blue())
            embed.add_field(name="Uživatelské jméno", value=member.name, inline=True)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Ověření", value=verification_status, inline=True)
            embed.add_field(name="E-mail", value=user_email, inline=True)

            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)

            await ctx.send(embed=embed)

        @whois.error
        async def whois_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("Tento příkaz může použít pouze vlastník bota.")

        @self.bot.command()
        @commands.check(self.is_owner)
        async def strip(ctx, user_id: int):
            conn = create_connection()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM verifications WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()

            if row is None:
                await ctx.send(f"Uživatel s ID {user_id} nemá uložený žádný ověřovací záznam.")
            else:
                cursor.execute('''
                DELETE FROM verifications WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                await ctx.send(f"Ověření uživatele s ID {user_id} bylo odstraněno.")

            conn.close()

            member = ctx.guild.get_member(user_id)
            if member is None:
                await ctx.send("Uživatel není na tomto serveru nebo není online.")
                return

            roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Odebrání rolí po zrušení ověření.")
                    await ctx.send(f"✅ Uživateli {member.mention} byly odebrány všechny role.")
                except discord.Forbidden:
                    await ctx.send("❌ Nemám oprávnění odebrat některé role.")
            else:
                await ctx.send("Uživatel nemá žádné role k odebrání.")

        @strip.error
        async def strip_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("Tento příkaz může použít pouze vlastník bota.")
    
    def run(self):
        self.bot.run(self.TOKEN)

if __name__ == "__main__":
    bot = DiscordBot()
    bot.run()

