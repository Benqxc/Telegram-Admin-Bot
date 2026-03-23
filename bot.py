import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BAD_WORDS = ['мат1', 'мат2', 'плохое_слово']
WARNINGS_FILE = 'warnings.json'
AUTO_ROLES_FILE = 'auto_roles.json'
TICKETS_FILE = 'tickets.json'
TICKET_CONFIG_FILE = 'ticket_config.json'

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


def load_tickets():
    """Загружает данные о тикетах"""
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_tickets(tickets):
    """Сохраняет данные о тикетах"""
    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tickets, f, ensure_ascii=False, indent=4)


def load_ticket_config():
    """Загружает конфигурацию тикетов"""
    if os.path.exists(TICKET_CONFIG_FILE):
        with open(TICKET_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_ticket_config(config):
    """Сохраняет конфигурацию тикетов"""
    with open(TICKET_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


# ==================== Система тикетов ====================

class TicketCreateButton(Button):
    """Кнопка для создания тикета"""
    def __init__(self):
        super().__init__(
            label="Открыть тикет",
            style=discord.ButtonStyle.green,
            emoji="🎫"
        )
    
    async def callback(self, interaction: discord.Interaction):
        tickets = load_tickets()
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        
        # Проверка на существующий открытый тикет
        if guild_id in tickets:
            for ticket_id, ticket_data in tickets[guild_id].items():
                if ticket_data['user_id'] == user_id and ticket_data['status'] == 'open':
                    channel = interaction.guild.get_channel(int(ticket_data['channel_id']))
                    if channel:
                        await interaction.response.send_message(
                            f'❌ У вас уже есть открытый тикет: {channel.mention}',
                            ephemeral=True
                        )
                        return
        
        # Получение конфигурации
        config = load_ticket_config()
        guild_config = config.get(guild_id, {})
        category_id = guild_config.get('category_id')
        support_role_id = guild_config.get('support_role_id')
        
        category = None
        if category_id:
            category = interaction.guild.get_channel(int(category_id))
        
        # Создание канала тикета
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        if support_role_id:
            support_role = interaction.guild.get_role(int(support_role_id))
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        try:
            ticket_number = len(tickets.get(guild_id, {})) + 1
            channel = await interaction.guild.create_text_channel(
                name=f'тикет-{ticket_number:04d}',
                category=category,
                overwrites=overwrites
            )
            
            # Сохранение данных тикета
            if guild_id not in tickets:
                tickets[guild_id] = {}
            
            ticket_id = str(channel.id)
            tickets[guild_id][ticket_id] = {
                'channel_id': channel.id,
                'user_id': user_id,
                'user_name': str(interaction.user),
                'created_at': datetime.datetime.now().isoformat(),
                'status': 'open',
                'claimed_by': None,
                'claimed_at': None,
                'closed_by': None,
                'closed_at': None,
                'close_reason': None,
                'number': ticket_number
            }
            save_tickets(tickets)
            
            # Создание embed для тикета
            embed = discord.Embed(
                title=f'🎫 Тикет #{ticket_number:04d}',
                description=f'Добро пожаловать, {interaction.user.mention}!\n\nОпишите вашу проблему, и наша команда поддержки скоро вам поможет.',
                color=discord.Color.blue()
            )
            embed.add_field(name='Статус', value='🟢 Открыт', inline=True)
            embed.add_field(name='Создан', value=f'<t:{int(datetime.datetime.now().timestamp())}:R>', inline=True)
            embed.set_footer(text='Powered by Nobame')
            
            # Создание кнопок управления тикетом
            view = TicketControlView()
            await channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                f'✅ Тикет создан: {channel.mention}',
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                '❌ У бота нет прав для создания каналов.',
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'❌ Ошибка при создании тикета: {e}',
                ephemeral=True
            )


class TicketPanelView(View):
    """View для панели тикетов"""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCreateButton())


class TicketControlView(View):
    """View для управления тикетом"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Принять", style=discord.ButtonStyle.primary, emoji="✋")
    async def claim_button(self, interaction: discord.Interaction, button: Button):
        tickets = load_tickets()
        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_id not in tickets or channel_id not in tickets[guild_id]:
            await interaction.response.send_message('❌ Тикет не найден.', ephemeral=True)
            return
        
        ticket = tickets[guild_id][channel_id]
        
        if ticket['claimed_by']:
            await interaction.response.send_message(
                f'❌ Тикет уже принят пользователем <@{ticket["claimed_by"]}>',
                ephemeral=True
            )
            return
        
        # Принятие тикета
        ticket['claimed_by'] = interaction.user.id
        ticket['claimed_at'] = datetime.datetime.now().isoformat()
        save_tickets(tickets)
        
        embed = discord.Embed(
            title='✋ Тикет принят',
            description=f'{interaction.user.mention} принял этот тикет и скоро поможет вам.',
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message('✅ Вы приняли этот тикет.', ephemeral=True)
    
    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        modal = CloseTicketModal()
        await interaction.response.send_modal(modal)


class CloseTicketModal(Modal, title='Закрытие тикета'):
    """Модальное окно для закрытия тикета"""
    reason = TextInput(
        label='Причина закрытия',
        placeholder='Укажите причину закрытия тикета...',
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        tickets = load_tickets()
        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        
        if guild_id not in tickets or channel_id not in tickets[guild_id]:
            await interaction.response.send_message('❌ Тикет не найден.', ephemeral=True)
            return
        
        ticket = tickets[guild_id][channel_id]
        
        # Закрытие тикета
        ticket['status'] = 'closed'
        ticket['closed_by'] = interaction.user.id
        ticket['closed_at'] = datetime.datetime.now().isoformat()
        ticket['close_reason'] = self.reason.value
        save_tickets(tickets)
        
        # Создание лога
        embed = discord.Embed(
            title='🔒 Тикет закрыт',
            color=discord.Color.red()
        )
        embed.add_field(name='Закрыл', value=interaction.user.mention, inline=True)
        embed.add_field(name='Причина', value=self.reason.value, inline=False)
        
        if ticket['claimed_by']:
            embed.add_field(name='Принял', value=f"<@{ticket['claimed_by']}>", inline=True)
        
        embed.add_field(name='Создатель', value=f"<@{ticket['user_id']}>", inline=True)
        embed.add_field(
            name='Время работы',
            value=f"<t:{int(datetime.datetime.fromisoformat(ticket['created_at']).timestamp())}:R>",
            inline=True
        )
        embed.set_footer(text='Канал будет удален через 10 секунд')
        
        await interaction.response.send_message(embed=embed)
        
        # Удаление канала через 10 секунд
        await interaction.channel.send('⏱️ Канал будет удален через 10 секунд...')
        import asyncio
        await asyncio.sleep(10)
        
        try:
            await interaction.channel.delete()
        except:
            pass


# ==================== События ====================

@bot.event
async def on_ready():
    """Событие при запуске бота"""
    print(f'✅ Бот {bot.user} успешно подключился к Discord!')
    print(f'📊 Подключен к {len(bot.guilds)} серверам')
    
    # Регистрация persistent views для тикетов
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    print('✅ Persistent views для тикетов зарегистрированы')
    
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


# ==================== Команды тикетов ====================

@bot.tree.command(name="setup_tickets", description="Создать панель тикетов в канале")
@app_commands.describe(
    channel="Канал для размещения панели тикетов",
    category="Категория для создания тикет-каналов (необязательно)",
    support_role="Роль поддержки с доступом к тикетам (необязательно)"
)
async def setup_tickets(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    category: discord.CategoryChannel = None,
    support_role: discord.Role = None
):
    """Создает панель тикетов в указанном канале"""
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message('❌ У вас нет прав на управление каналами.', ephemeral=True)
        return
    
    # Сохранение конфигурации
    config = load_ticket_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {}
    
    if category:
        config[guild_id]['category_id'] = category.id
    
    if support_role:
        config[guild_id]['support_role_id'] = support_role.id
    
    save_ticket_config(config)
    
    # Создание embed для панели
    embed = discord.Embed(
        title='🎫 Tickets v2',
        description='**Откройте билет!**\nНажав на кнопку, вы откроете билет.',
        color=discord.Color.blue()
    )
    embed.set_footer(text='Powered by Nobame')
    
    # Отправка панели с кнопкой
    try:
        view = TicketPanelView()
        await channel.send(embed=embed, view=view)
        
        response_text = f'✅ Панель тикетов создана в {channel.mention}'
        if category:
            response_text += f'\n📁 Категория: {category.mention}'
        if support_role:
            response_text += f'\n👥 Роль поддержки: {support_role.mention}'
        
        await interaction.response.send_message(response_text, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(
            f'❌ У бота нет прав для отправки сообщений в {channel.mention}',
            ephemeral=True
        )


@bot.tree.command(name="ticket_config", description="Настроить систему тикетов")
@app_commands.describe(
    category="Категория для создания тикет-каналов",
    support_role="Роль поддержки с доступом к тикетам"
)
async def ticket_config(
    interaction: discord.Interaction,
    category: discord.CategoryChannel = None,
    support_role: discord.Role = None
):
    """Настраивает параметры системы тикетов"""
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message('❌ У вас нет прав на управление каналами.', ephemeral=True)
        return
    
    config = load_ticket_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {}
    
    changes = []
    
    if category:
        config[guild_id]['category_id'] = category.id
        changes.append(f'📁 Категория: {category.mention}')
    
    if support_role:
        config[guild_id]['support_role_id'] = support_role.id
        changes.append(f'👥 Роль поддержки: {support_role.mention}')
    
    if not changes:
        await interaction.response.send_message('❌ Укажите хотя бы один параметр для настройки.', ephemeral=True)
        return
    
    save_ticket_config(config)
    
    embed = discord.Embed(
        title='⚙️ Конфигурация тикетов обновлена',
        description='\n'.join(changes),
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="ticket_stats", description="Показать статистику тикетов")
async def ticket_stats(interaction: discord.Interaction):
    """Показывает статистику по тикетам сервера"""
    tickets = load_tickets()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in tickets or not tickets[guild_id]:
        await interaction.response.send_message('📊 На этом сервере еще не было создано тикетов.', ephemeral=True)
        return
    
    guild_tickets = tickets[guild_id]
    
    total = len(guild_tickets)
    open_tickets = sum(1 for t in guild_tickets.values() if t['status'] == 'open')
    closed_tickets = sum(1 for t in guild_tickets.values() if t['status'] == 'closed')
    claimed_tickets = sum(1 for t in guild_tickets.values() if t['claimed_by'] is not None)
    
    embed = discord.Embed(
        title='📊 Статистика тикетов',
        color=discord.Color.blue()
    )
    embed.add_field(name='Всего тикетов', value=str(total), inline=True)
    embed.add_field(name='🟢 Открыто', value=str(open_tickets), inline=True)
    embed.add_field(name='🔒 Закрыто', value=str(closed_tickets), inline=True)
    embed.add_field(name='✋ Принято', value=str(claimed_tickets), inline=True)
    
    # Список открытых тикетов
    if open_tickets > 0:
        open_list = []
        for ticket_id, ticket in guild_tickets.items():
            if ticket['status'] == 'open':
                channel = interaction.guild.get_channel(int(ticket['channel_id']))
канал импортиф:
 статус = '✋' если билет['заявлено_от'] еще '🟢'
 открытый_список.добавить(ф"{статус} {канал.упомянуть} - <@{билет['идентификатор_пользователя']}>")
        
        если открытый_список:
 вставлять.добавить_поле(
 имя='Открытые тикеты',
 значение='\н'.присоединиться(открытый_список[:10]),
 встроенный=Ложь
            )
    
    ждать взаимодействие.ответ.отправить_сообщение(встраивать=встраивать)


@bot.tree.команда(имя="ticket_close_all", описание="Закрыть все открытые тикеты (только для администраторов)")
асинхронный деф билет_закрыть_все(взаимодействие: раздор.Взаимодействие):
    """Закрывает все открытые тикеты на сервере"""
    если нет взаимодействие.пользователь.guild_разрешения.администратор:
        ждать взаимодействие.ответ.отправить_сообщение('❌ Эта команда доступна только администраторам.', эфемерный=Истинный)
        возвращаться
    
 билеты = load_tickets()
 guild_id = стр(взаимодействие.гильдия.идентификатор)
    
    если идентификатор_гильдии нет в билеты:
        ждать взаимодействие.ответ.отправить_сообщение('❌ На этом сервере нет тикетов.', эфемерный=Истинный)
        возвращаться
    
    ждать взаимодействие.ответ.отложить(эфемерный=Истинный)
    
 закрытое_количество = 0
    для ticket_id, билет в билеты[идентификатор_гильдии].предметы():
        если билет['статус'] == 'открыть':
 канал = взаимодействие.гильдия.получить_канал(инт(билет['идентификатор_канала']))
            если канал:
                пытаться:
                    ждать канал.удалить(причина='Массовое закрытие тикетов администратором')
 билет['статус'] = «закрыто»
 билет['закрыто_по'] = взаимодействие.пользователь.идентификатор
 билет['закрыто_в'] = дата и время.дата и время.сейчас().изоформат()
 билет['закрыть_причину'] = 'Массовое закрытие администратором'
 закрытое_количество += 1
                кроме:
                    проходить
    
    сохранить_билеты(билеты)
    
    ждать взаимодействие.следовать за.отправлять(f'✅ ЗакрытѾ тикѵтѾв: {закрытое_количество}', эфемерный=Истинный)


# ==================== Запуск бота ====================

если __имя__ == '__основной__':
    если ТОКЕН является Нет:
        печать('❌ Ошибка: токен не найден. Укажите DISCORD_TOKEN в переменных окружениях или файле .env')
    еще:
        пытаться:
 бот.бегать(ТОКЕН)
        кроме Исключение как е:
            печать(f'❌ Ошибка запуска боЂа: {e}')
