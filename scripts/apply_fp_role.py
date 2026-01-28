import os
import json
import asyncio

import discord


CANDIDATES_PATH = os.getenv("FP_CANDIDATES_IN", "fp_candidates.json")
FP_ROLE_ID = int(os.getenv("FP_ROLE_ID", "1466036385017233636"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# If set to "1", script will not add roles, only print what it would do
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN env var")
    if not GUILD_ID:
        raise RuntimeError("Missing GUILD_ID env var")

    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    user_ids = [int(x["discord_user_id"]) for x in candidates if "discord_user_id" in x]

    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True  # required for fetch_member

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[apply_fp] logged in as {client.user}")

        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        role = guild.get_role(FP_ROLE_ID)

        if role is None:
            print("[apply_fp] FP role not found (check FP_ROLE_ID)")
            await client.close()
            return

        added = 0
        already = 0
        missing = 0
        failed = 0

        for uid in user_ids:
            try:
                member = guild.get_member(uid)
                if member is None:
                    member = await guild.fetch_member(uid)

                if role in member.roles:
                    already += 1
                else:
                    if DRY_RUN:
                        print(f"[apply_fp] DRY_RUN would add role to {uid}")
                    else:
                        await member.add_roles(
                            role,
                            reason="Auto-assign FP role based on VUT API (FP + B/N)"
                        )
                        added += 1

            except discord.NotFound:
                missing += 1
            except discord.Forbidden:
                failed += 1
                print(f"[apply_fp] forbidden for user={uid} (bot role/permissions?)")
            except Exception as e:
                failed += 1
                print(f"[apply_fp] error for user={uid}: {e}")

            # small delay for rate limits
            await asyncio.sleep(0.4)

        print(f"[apply_fp] done | added={added} already={already} missing={missing} failed={failed}")
        await client.close()

    await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

