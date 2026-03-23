import discord
from discord.ext import commands
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '/'
BAD_WORDS = ['мат1', 'мат2', 'плохое_слово']
ROLE_NEWBIE = 'Neuling'
WARNINGS_FILE = 'warnings.json'
AUTO_ROLES_FILE = 'auto_roles.json'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_warnings(warnings):
    with open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(warnings, f, ensure_ascii=False, indent=4)


def load_auto_roles():
    if os.path.exists(AUTO_ROLES_FILE):
        with open(AUTO_ROLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_auto_roles(roles):
    with open(AUTO_ROLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(roles, f, ensure_ascii=False, indent=4)


@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключился к Discord!')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

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


@bot.command(name='say')
async def say(ctx, *, message):
    """Отправляет текст, написанный после команды. Пример: /say Привет всем!"""
    await ctx.send(message)


@bot.command(name='clear')
async def clear(ctx, amount: int):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send('У вас нет прав администратора.', delete_after=5)
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
    if not ctx.author.guild_permissions.administrator:
        await ctx.send('У вас нет прав администратора.', delete_after=5)
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


@bot.command(name='autorole_add')
async def autorole_add(ctx, *, role_name: str):
    """Добавляет роль в список автовыдачи. Пример: /autorole_add Neuling"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send('У вас нет прав администратора.', delete_after=5)
        return
    
 роль = раздор.полезности.получать(ктх.гильдия.роли, имя=имя_роли)
    если нет роль:
        ждать ктх.отправлять(ф'Роль "{имя_роли}" не найдена на сервере.', удалить_после=5)
        возвращаться
    
 авто_роли = загрузка_авто_ролей()
    
    если имя_роли в авто_роли:
        ждать ктх.отправлять(ф'Роль "{имя_роли}" уже в списке автовыдачи.', удалить_после=5)
        возвращаться
    
 авто_роли.добавить(имя_роли)
    сохранить_авто_роли(авто_роли)
    ждать ктх.отправлять(f'✅ Роль "{имя_роли}" " добавлена в список автовыдачи.')


@бот.команда(имя='autorole_remove')
асинхронный деф autorole_remove(ктх, *, имя_роли: str):
    """Удаляет роль из списка автовыдачи. Пример: /autorole_remove Neuling"""
    если нет ктх.автор.guild_разрешения.администратор:
        ждать ктх.отправлять('У вас нет прав администратора.', удалить_после=5)
        возвращаться
    
 авто_роли = загрузка_авто_ролей()
    
    если имя_роли нет в авто_роли:
        ждать ктх.отправлять(ф'Роль "{имя_роли}" " не найдена в списке автовыдачи.', удалить_после=5)
        возвращаться
    
 авто_роли.удалять(имя_роли)
    сохранить_авто_роли(авто_роли)
    ждать ктх.отправлять(f'✅ Роль "{имя_роли}" удалена из списка автовыдачи.')


@бот.команда(имя='список_авторолей')
асинхронный деф список_авторизаций(ктх):
    """Показывает список ролей для автовыдачи. Пример: /autorole_list"""
 авто_роли = загрузка_авто_ролей()
    
    если нет авто_роли:
        ждать ктх.отправлять('Список автовыдачи ролей пуст.')
        возвращаться
    
 встраивать = раздор.Вставлять(
 заголовок='📋 Роли для автовыдачи',
 описание='\н'.присоединиться(ф'• {роль}' для роль в авто_роли),
 цвет=разногласие.Цвет.синий()
    )
    
    ждать ктх.отправлять(встраивать=встраивать)


если __имя__ == '__основной__':
    если ТОКЕН является Нет:
        печать('Ошибка: токен не найден. Укажите DISCORD_TOKEN в переменных окружениях или файле .env')
    еще:
 бот.бегать(ТОКЕН)
