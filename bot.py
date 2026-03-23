import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BAD_WORDS = ['мат1', 'мат2', 'плохое_слово']
WARNINGS_FILE = 'warnings.json'
AUTO_ROLES_FILE = 'auto_roles.json'

# Настройка intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)


# ==================== Утилиты ====================

def load_warnings():
    """Загружает предупреждения из файла"""
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_warnings(warnings):
    """Сохраняет предупреждения в файл"""
    with open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(warnings, f, ensure_ascii=False, indent=4)


def load_auto_roles():
    """Загружает список автоматических ролей"""
    if os.path.exists(AUTO_ROLES_FILE):
        with open(AUTO_ROLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_auto_roles(roles):
    """Сохраняет список автоматических ролей"""
    with open(AUTO_ROLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(roles, f, ensure_ascii=False, indent=4)


# ==================== События ====================

@bot.event
async def on_ready():
    """Событие при запуске бота"""
    print(f'✅ Бот {bot.user} успешно подключился к Discord!')
    print(f'📊 Подключен к {len(bot.guilds)} серверам')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} slash-команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации команд: {e}')


@bot.event
async def on_member_join(member):
    """Автоматическая выдача ролей новым участникам"""
    auto_roles = load_auto_roles()
    
    if not auto_roles:
        return
    
    for role_name in auto_roles:
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            try:
                await member.add_roles(role)
                print(f'✅ Роль "{role_name}" выдана пользователю {member.name}')
            except discord.Forbidden:
                print(f'❌ Нет прав для выдачи роли "{role_name}"')
            except Exception as e:
                print(f'❌ Ошибка при выдаче роли: {e}')


@bot.event
async def on_message(message):
    """Фильтрация нецензурных слов"""
    if message.author.bot:
        return

    # Проверка на плохие слова
    if any(bad_word in message.content.lower() for bad_word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.send('⚠️ Ваше сообщение было удалено, так как содержит недопустимые выражения.')
        except discord.Forbidden:
            print(f'❌ Не удалось отправить ЛС пользователю {message.author}')
        except discord.NotFound:
            pass
        return

    await bot.process_commands(message)


# ==================== Slash-команды ====================

@bot.tree.command(name="ban", description="Заблокировать пользователя")
@app_commands.describe(
    member="Пользователь для блокировки",
    reason="Причина блокировки"
)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Причина не указана"):
    """Блокирует пользователя на сервере"""
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message('❌ У вас нет прав на блокировку пользователей.', ephemeral=True)
        return
    
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f'✅ Пользователь {member.mention} заблокирован. Причина: {reason}')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для блокировки этого пользователя.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="kick", description="Выгнать пользователя")
@app_commands.describe(
    member="Пользователь для исключения",
    reason="Причина исключения"
)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Причина не указана"):
    """Выгоняет пользователя с сервера"""
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message('❌ У вас нет прав на исключение пользователей.', ephemeral=True)
        return
    
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f'✅ Пользователь {member.mention} исключен. Причина: {reason}')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для исключения этого пользователя.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="gif", description="Искать анимированные картинки в интернете")
@app_commands.describe(query="Поисковый запрос")
async def gif(interaction: discord.Interaction, query: str):
    """Отправляет GIF по запросу (через Tenor API)"""
    await interaction.response.send_message(f'🔍 Поиск GIF: {query}\n(Для полной функциональности требуется Tenor API ключ)')


@bot.tree.command(name="me", description="Выделяет текст курсивом")
@app_commands.describe(text="Текст для выделения")
async def me(interaction: discord.Interaction, text: str):
    """Отправляет текст курсивом"""
    await interaction.response.send_message(f'*{text}*')


@bot.tree.command(name="msg", description="Написать пользователю")
@app_commands.describe(
    member="Пользователь для отправки сообщения",
    message="Текст сообщения"
)
async def msg(interaction: discord.Interaction, member: discord.Member, message: str):
    """Отправляет личное сообщение пользователю"""
    try:
        await member.send(f'📨 Сообщение от {interaction.user.mention}:\n{message}')
        await interaction.response.send_message(f'✅ Сообщение отправлено пользователю {member.mention}', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f'❌ Не удалось отправить сообщение {member.mention}. Возможно, у пользователя закрыты ЛС.', ephemeral=True)


@bot.tree.command(name="nick", description="Изменить никнейм на этом сервере")
@app_commands.describe(
    member="Пользователь для изменения никнейма",
    nickname="Новый никнейм"
)
async def nick(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Изменяет никнейм пользователя на сервере"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message('❌ У вас нет прав на изменение никнеймов.', ephemeral=True)
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        await interaction.response.send_message(f'✅ Никнейм {member.mention} изменен с "{old_nick}" на "{nickname}"')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для изменения никнейма этого пользователя.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="shrug", description="Добавляет ¯\\_(ツ)_/¯ к вашему сообщению")
@app_commands.describe(text="Текст сообщения (необязательно)")
async def shrug(interaction: discord.Interaction, text: str = ""):
    """Отправляет сообщение с шрагом"""
    shrug_emoji = r"¯\_(ツ)_/¯"
    message = f"{text} {shrug_emoji}" if text else shrug_emoji
    await interaction.response.send_message(message)


@bot.tree.command(name="say", description="Отправляет текст от имени бота")
@app_commands.describe(message="Текст для отправки")
async def say(interaction: discord.Interaction, message: str):
    """Отправляет сообщение от имени бота"""
    await interaction.response.send_message(message)


@bot.tree.command(name="clear", description="Очистить сообщения в канале")
@app_commands.describe(amount="Количество сообщений для удаления")
async def clear(interaction: discord.Interaction, amount: int):
    """Удаляет указанное количество сообщений"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return

    if amount <= 0 or amount > 100:
        await interaction.response.send_message('❌ Количество должно быть от 1 до 100.', ephemeral=True)
        return

    try:
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f'✅ Удалено {len(deleted)} сообщений.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ У бота нет прав на удаление сообщений.', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="warn", description="Выдать предупреждение пользователю")
@app_commands.describe(
    member="Пользователь для предупреждения",
    reason="Причина предупреждения"
)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "Причина не указана"):
    """Выдает предупреждение пользователю"""
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message('❌ У вас нет прав модератора.', ephemeral=True)
        return

    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append({
        'reason': reason,
        'date': datetime.datetime.now().isoformat(),
        'moderator': str(interaction.user),
        'moderator_id': interaction.user.id
    })

    save_warnings(warnings)
    
    embed = discord.Embed(
        title='⚠️ Предупреждение',
        description=f'Пользователю {member.mention} выдано предупреждение',
        color=discord.Color.orange()
    )
    embed.add_field(name='Причина', value=reason, inline=False)
    embed.add_field(name='Модератор', value=interaction.user.mention, inline=True)
    embed.add_field(name='Всего предупреждений', value=str(len(warnings[user_id])), inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warnings", description="Показать предупреждения пользователя")
@app_commands.describe(member="Пользователь для проверки")
async def warnings_list(interaction: discord.Interaction, member: discord.Member):
    """Показывает список предупреждений пользователя"""
    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings or not warnings[user_id]:
        await interaction.response.send_message(f'✅ У пользователя {member.mention} нет предупреждений.', ephemeral=True)
        return

    embed = discord.Embed(
        title=f'⚠️ Предупреждения пользователя {member.display_name}',
        color=discord.Color.orange()
    )
    
    for i, warn_data in enumerate(warnings[user_id], 1):
        date = warn_data['date'][:10]
        embed.add_field(
            name=f'#{i} | {date}',
            value=f"**Причина:** {warn_data['reason']}\n**Модератор:** {warn_data['moderator']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="autorole_add", description="Добавить роль в список автовыдачи")
@app_commands.describe(role="Роль для автоматической выдачи")
async def autorole_add(interaction: discord.Interaction, role: discord.Role):
    """Добавляет роль в список автоматической выдачи новым участникам"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    auto_roles = load_auto_roles()
    
    if role.name in auto_roles:
        await interaction.response.send_message(f'❌ Роль {role.mention} уже в списке автовыдачи.', ephemeral=True)
        return
    
    auto_roles.append(role.name)
    save_auto_roles(auto_roles)
    await interaction.response.send_message(f'✅ Роль {role.mention} добавлена в список автовыдачи.')


@bot.tree.command(name="autorole_remove", description="Удалить роль из списка автовыдачи")
@app_commands.describe(role="Роль для удаления из автовыдачи")
async def autorole_remove(interaction: discord.Interaction, role: discord.Role):
    """Удаляет роль из списка автоматической выдачи"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    auto_roles = load_auto_roles()
    
    if role.name not in auto_roles:
        await interaction.response.send_message(f'❌ Роль {role.mention} не найдена в списке автовыдачи.', ephemeral=True)
        return
    
    auto_roles.remove(role.name)
    save_auto_roles(auto_roles)
    await interaction.response.send_message(f'✅ Роль {role.mention} удалена из списка автовыдачи.')


@bot.tree.command(name="autorole_list", description="Показать список ролей для автовыдачи")
async def autorole_list(interaction: discord.Interaction):
    """Показывает список ролей для автоматической выдачи"""
    auto_roles = load_auto_roles()
    
    if not auto_roles:
        await interaction.response.send_message('📋 Список автовыдачи ролей пуст.', ephemeral=True)
        return
    
    embed = discord.Embed(
        title='📋 Роли для автоматической выдачи',
        description='\n'.join(f'• {role}' for role in auto_roles),
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)


# ==================== Запуск бота ====================

if __name__ == '__main__':
    if TOKEN is None:
        print('❌ Ошибка: токен не найден. Укажите DISCORD_TOKEN в переменных окружения или файле .env')
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f'❌ Ошибка запуска бота: {e}')
