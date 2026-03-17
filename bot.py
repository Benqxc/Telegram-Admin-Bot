import discord
from discord.ext import commands
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '!'
BAD_WORDS = ['мат1', 'мат2', 'плохое_слово']  # замени на свои
ROLE_NEWBIE = 'Neuling'
ROLE_MOD = 'Genius'
WARNINGS_FILE = 'warnings.json'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ========== РАБОТА С ПРЕДУПРЕЖДЕНИЯМИ ==========
def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_warnings(warnings):
    with open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(warnings, f, ensure_ascii=False, indent=4)

# ========== СОБЫТИЯ ==========
@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключился к Discord!')

@bot.event
async def on_member_join(member):
    guild = member.guild
    role = discord.utils.get(guild.roles, name=ROLE_NEWBIE)
    if role:
        try:
            await member.add_roles(role)
            print(f'Выдана роль {ROLE_NEWBIE} пользователю {member}')
        except Exception as e:
            print(f'Ошибка при выдаче роли: {e}')
    else:
        print(f'Роль "{ROLE_NEWBIE}" не найдена на сервере.')

    try:
        await member.send('Добро пожаловать на сервер! Ознакомься с правилами в канале #правила')
    except discord.Forbidden:
        print(f'Не удалось отправить ЛС пользователю {member} (закрыты личные сообщения).')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Фильтр мата
    if any(bad_word in message.content.lower() for bad_word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.send('Ваше сообщение было удалено, так как содержит недопустимые выражения.')
        except discord.Forbidden:
            print(f'Не удалось отправить ЛС нарушителю {message.author}.')
        except discord.NotFound:
            print('Сообщение уже удалено.')
        return

    await bot.process_commands(message)

# ========== КОМАНДЫ ==========

# 👉 Команда !say (отправляет переданный текст)
@bot.command(name='say')
async def say(ctx, *, message):
    """Отправляет текст, написанный после команды. Пример: !say Привет всем!"""
    await ctx.send(message)

@bot.command(name='clear')
async def clear(ctx, amount: int):
    if not any(role.name == ROLE_MOD for role in ctx.author.roles):
        await ctx.send('У вас нет прав модератора.', delete_after=5)
        return

    if amount <= 0:
        await ctx.send('Количество должно быть положительным числом.', delete_after=5)
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f'Удалено {len(deleted)-1} сообщений.', delete_after=5)
    except Exception as e:
        await ctx.send(f'Ошибка при очистке: {e}', delete_after=5)

@bot.command(name='warn')
async def warn(ctx, member: discord.Member, *, reason='Причина не указана'):
    if not any(role.name == ROLE_MOD for role in ctx.author.roles):
        await ctx.send('У вас нет прав модератора.', delete_after=5)
        return

    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append({
        'reason': reason,
        'date': datetime.datetime.now().isoformat(),
        'moderator': str(ctx.author)
    })

    save_warnings(warnings)

    await ctx.send(f'Пользователю {member.mention} выдано предупреждение. Причина: {reason}')

@bot.command(name='warnings')
async def warnings_list(ctx, member: discord.Member):
    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings or not warnings[user_id]:
        await ctx.send(f'У пользователя {member.mention} нет предупреждений.')
        return

    embed = discord.Embed(title=f'Предупреждения для {member}', color=discord.Color.orange())
    for i, warn_data in enumerate(warnings[user_id], 1):
        embed.add_field(
            name=f'#{i} | {warn_data["date"][:10]}',
            value=f'Причина: {warn_data["reason"]}\nМодератор: {warn_data["moderator"]}',
            inline=False
        )

    await ctx.send(embed=embed)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    if TOKEN is None:
        print('Ошибка: токен не найден. Укажите DISCORD_TOKEN в переменных окружения или файле .env')
    else:
        bot.run(TOKEN)
