@bot.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) != "📌":
        return

    guild = bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # už je připnutá
    if message.pinned:
        return

    for reaction in message.reactions:
        if str(reaction.emoji) == "📌":
            if reaction.count >= 1:
                await message.pin(reason="5× 📌 reakce")
                break

