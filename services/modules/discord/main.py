"""Módulo Discord — encaminha mensagens ao engine."""

import os

import discord

from shared.popse_common.engine_client import send_chat

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    print(f"Discord bot conectado: {client.user}")


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    user_id = f"discord:{message.author.id}"
    reply = await send_chat(message.content, user_id, "discord")
    await message.channel.send(reply)


def main() -> None:
    client.run(TOKEN)


if __name__ == "__main__":
    main()
