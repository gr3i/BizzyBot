import discord
from discord.ext import commands
import json

class RoleAndChannelCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # MOD tym role IDs; zde muzu pridavat dalsi IDs role pro opravneni
        self.extra_roles_ids = [
            1358898283782602932,  # MOD role
            1359508102222975087,
            1370841996977246218,
            1370842282084925541,
            1370842977479692338,
            1370843216898953307
        ]

    @commands.command(name="createSubjects_script")
    @commands.has_permissions(manage_roles=True, manage_channels=True)
    async def vytvor_predmety_soubor(self, ctx):
        """
        Vytvoří role a místnosti na základě seznamu v souboru subjects.txt a uloží Role ID do souboru.
        """
        created_items = []

        try:
            with open("utils/subjects.txt", "r", encoding="utf-8") as f:
                subject_names = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            await ctx.send("Soubor subjects.txt nebyl nalezen.")
            return
        
        for name in subject_names:
            role = discord.utils.get(ctx.guild.roles, name=name)
            if not role:
                role = await ctx.guild.create_role(name=name)
                await ctx.send(f"Vytvořena role '{name}' s ID {role.id}.")
            else:
                await ctx.send(f"Role '{name}' už existuje s ID {role.id}.")
            
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                role: discord.PermissionOverwrite(view_channel=True)
            }

            
            for role_id in self.extra_roles_ids:
                extra_role = ctx.guild.get_role(role_id)
                if extra_role:
                    overwrites[extra_role] = discord.PermissionOverwrite(view_channel=True)

            channel_name = name.lower().replace(" ", "-")
            channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
            if not channel:
                channel = await ctx.guild.create_text_channel(name=channel_name, overwrites=overwrites)
                await ctx.send(f"Vytvořen kanál '{channel.name}' s ID {channel.id}.")
            else:
                await ctx.send(f"Kanál '{channel.name}' už existuje s ID {channel.id}.")
            
            created_items.append({"name": name, "role_id": role.id})
        
        with open("utils/created_roles.json", "w", encoding="utf-8") as f:
            json.dump(created_items, f, ensure_ascii=False, indent=4)
        await ctx.send("Role ID byla uložena do souboru created_roles.json.")

async def setup(bot):
    await bot.add_cog(RoleAndChannelCreator(bot))

