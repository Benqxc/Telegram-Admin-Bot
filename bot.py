import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, Select
import os
import json
import datetime
import asyncio
import re
import random
import string
from collections import defaultdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Файлы данных
WARNINGS_FILE = 'warnings.json'
AUTO_ROLES_FILE = 'auto_roles.json'
TICKETS_FILE = 'tickets.json'
TICKET_CONFIG_FILE = 'ticket_config.json'
LEVELS_FILE = 'levels.json'
WORD_FILTER_FILE = 'word_filter.json'
CONFIG_FILE = 'config.json'
REMINDERS_FILE = 'reminders.json'
REACTION_ROLES_FILE = 'reaction_roles.json'
WELCOME_CONFIG_FILE = 'welcome_config.json'
GIVEAWAYS_FILE = 'giveaways.json'
CUSTOM_COMMANDS_FILE = 'custom_commands.json'
VERIFICATION_CONFIG_FILE = 'verification_config.json'
ANTISPAM_CONFIG_FILE = 'antispam_config.json'
LOGS_CONFIG_FILE = 'logs_config.json'

# Настройка intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True
intents.presences = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)

# Глобальные переменные для анти-спам
user_message_cache = defaultdict(list)
user_spam_warnings = defaultdict(int)


# ==================== Утилиты загрузки/сохранения ====================

def load_json(filename):
    """Универсальная функция загрузки JSON"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    """Универсальная функция сохранения JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_warnings():
    return load_json(WARNINGS_FILE)

def save_warnings(warnings):
    save_json(WARNINGS_FILE, warnings)

def load_auto_roles():
    data = load_json(AUTO_ROLES_FILE)
    return data if isinstance(data, list) else []

def save_auto_roles(roles):
    save_json(AUTO_ROLES_FILE, roles)

def load_tickets():
    return load_json(TICKETS_FILE)

def save_tickets(tickets):
    save_json(TICKETS_FILE, tickets)

def load_ticket_config():
    return load_json(TICKET_CONFIG_FILE)

def save_ticket_config(config):
    save_json(TICKET_CONFIG_FILE, config)

def load_levels():
    return load_json(LEVELS_FILE)

def save_levels(levels):
    save_json(LEVELS_FILE, levels)

def load_word_filter():
    return load_json(WORD_FILTER_FILE)

def save_word_filter(filters):
    save_json(WORD_FILTER_FILE, filters)

def load_config():
    return load_json(CONFIG_FILE)

def save_config(config):
    save_json(CONFIG_FILE, config)

def load_reminders():
    return load_json(REMINDERS_FILE)

def save_reminders(reminders):
    save_json(REMINDERS_FILE, reminders)

def load_reaction_roles():
    return load_json(REACTION_ROLES_FILE)

def save_reaction_roles(reaction_roles):
    save_json(REACTION_ROLES_FILE, reaction_roles)

def load_welcome_config():
    return load_json(WELCOME_CONFIG_FILE)

def save_welcome_config(config):
    save_json(WELCOME_CONFIG_FILE, config)

def load_giveaways():
    return load_json(GIVEAWAYS_FILE)

def save_giveaways(giveaways):
    save_json(GIVEAWAYS_FILE, giveaways)

def load_custom_commands():
    return load_json(CUSTOM_COMMANDS_FILE)

def save_custom_commands(commands):
    save_json(CUSTOM_COMMANDS_FILE, commands)

def load_verification_config():
    return load_json(VERIFICATION_CONFIG_FILE)

def save_verification_config(config):
    save_json(VERIFICATION_CONFIG_FILE, config)

def load_antispam_config():
    return load_json(ANTISPAM_CONFIG_FILE)

def save_antispam_config(config):
    save_json(ANTISPAM_CONFIG_FILE, config)

def load_logs_config():
    return load_json(LOGS_CONFIG_FILE)

def save_logs_config(config):
    save_json(LOGS_CONFIG_FILE, config)


# ==================== Вспомогательные функции ====================

def parse_time(time_str):
    """Парсит строку времени в секунды (например: 1h, 30m, 1d)"""
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    match = re.match(r'(\d+)([smhdw])', time_str.lower())
    if match:
        value, unit = match.groups()
        return int(value) * time_units[unit]
    return None

def format_time(seconds):
    """Форматирует секунды в читаемый формат"""
    units = [('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for name, count in units:
        value = seconds // count
        if value:
            result.append(f'{int(value)}{name}')
            seconds -= value * count
    return ' '.join(result) or '0s'

def calculate_level(xp):
    """Вычисляет уровень по опыту"""
    return int((xp / 100) ** 0.5)

def xp_for_level(level):
    """Вычисляет необходимый опыт для уровня"""
    return (level ** 2) * 100

async def send_log(guild, log_type, embed):
    """Отправляет лог в настроенный канал"""
    logs_config = load_logs_config()
    guild_id = str(guild.id)
    
    if guild_id in logs_config and log_type in logs_config[guild_id]:
        channel_id = logs_config[guild_id][log_type]
        channel = guild.get_channel(int(channel_id))
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass

def format_welcome_message(message, member, guild):
    """Форматирует приветственное сообщение с переменными"""
    return message.replace('{user}', member.mention)\
                  .replace('{username}', member.name)\
                  .replace('{server}', guild.name)\
                  .replace('{member_count}', str(guild.member_count))


# ==================== Подтверждения для опасных действий ====================

class ConfirmView(View):
    """View для подтверждения опасных действий"""
    def __init__(self, timeout=30):
        super().__init__(timeout=timeout)
        self.value = None
    
    @discord.ui.button(label="Да", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
    
    @discord.ui.button(label="Нет", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


# ==================== Пагинация ====================

class PaginationView(View):
    """View для пагинации длинных списков"""
    def __init__(self, embeds, timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message = None
    
    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()
        self.stop()


# ==================== Система верификации ====================

class VerificationView(View):
    """View для верификации новых участников"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Верифицироваться", style=discord.ButtonStyle.green, emoji="✅", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        config = load_verification_config()
        guild_id = str(interaction.guild.id)
        
        if guild_id not in config:
            await interaction.response.send_message('❌ Система верификации не настроена.', ephemeral=True)
            return
        
        verified_role_id = config[guild_id].get('verified_role_id')
        if not verified_role_id:
            await interaction.response.send_message('❌ Роль верифицированных не настроена.', ephemeral=True)
            return
        
        verified_role = interaction.guild.get_role(int(verified_role_id))
        if not verified_role:
            await interaction.response.send_message('❌ Роль верифицированных не найдена.', ephemeral=True)
            return
        
        if verified_role in interaction.user.roles:
            await interaction.response.send_message('✅ Вы уже верифицированы!', ephemeral=True)
            return
        
        try:
            await interaction.user.add_roles(verified_role)
            await interaction.response.send_message('✅ Вы успешно верифицированы!', ephemeral=True)
            
            # Лог
            embed = discord.Embed(
                title='✅ Новая верификация',
                description=f'{interaction.user.mention} прошел верификацию',
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            await send_log(interaction.guild, 'member_log', embed)
        except:
            await interaction.response.send_message('❌ Ошибка при выдаче роли.', ephemeral=True)


# ==================== Reaction Roles ====================

class ReactionRoleView(View):
    """View для Reaction Roles"""
    def __init__(self, message_id, roles_data):
        super().__init__(timeout=None)
        self.message_id = message_id
        
        for emoji, role_id in roles_data.items():
            button = Button(emoji=emoji, custom_id=f"rr_{message_id}_{role_id}", style=discord.ButtonStyle.secondary)
            button.callback = self.create_callback(role_id)
            self.add_item(button)
    
    def create_callback(self, role_id):
        async def callback(interaction: discord.Interaction):
            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message('❌ Роль не найдена.', ephemeral=True)
                return
            
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f'✅ Роль {role.mention} снята.', ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f'✅ Роль {role.mention} выдана.', ephemeral=True)
        
        return callback


# ==================== Улучшенная система тикетов ====================

async def create_ticket_transcript(channel):
    """Создает транскрипт тикета"""
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        content = message.content or '[Вложение/Embed]'
        messages.append(f'[{timestamp}] {message.author}: {content}')
    
    transcript = '\n'.join(messages)
    filename = f'transcript-{channel.name}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f'Транскрипт тикета: {channel.name}\n')
        f.write(f'Создан: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write('=' * 50 + '\n\n')
        f.write(transcript)
    
    return filename


class TicketCategorySelect(Select):
    """Выбор категории тикета"""
    def __init__(self):
        options = [
            discord.SelectOption(label="Техническая поддержка", emoji="🔧", value="tech"),
            discord.SelectOption(label="Жалоба", emoji="⚠️", value="report"),
            discord.SelectOption(label="Вопрос", emoji="❓", value="question"),
            discord.SelectOption(label="Другое", emoji="📝", value="other")
        ]
        super().__init__(placeholder="Выберите категорию тикета", options=options, custom_id="ticket_category_select")
    
    async def callback(self, interaction: discord.Interaction):
        category_names = {
            "tech": "Техподдержка",
            "report": "Жалоба",
            "question": "Вопрос",
            "other": "Другое"
        }
        
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
                'category': self.values[0],
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
                title=f'🎫 Тикет #{ticket_number:04d} - {category_names[self.values[0]]}',
                description=f'Добро пожаловать, {interaction.user.mention}!\n\nОпишите вашу проблему, и наша команда поддержки скоро вам поможет.',
                color=discord.Color.blue()
            )
            embed.add_field(name='Статус', value='🟢 Открыт', inline=True)
            embed.add_field(name='Категория', value=category_names[self.values[0]], inline=True)
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


class TicketCreateButton(Button):
    """Кнопка для создания тикета"""
    def __init__(self):
        super().__init__(
            label="Открыть тикет",
            style=discord.ButtonStyle.green,
            emoji="🎫",
            custom_id="ticket_create_button"
        )
    
    async def callback(self, interaction: discord.Interaction):
        view = View(timeout=60)
        view.add_item(TicketCategorySelect())
        await interaction.response.send_message(
            '📋 Выберите категорию вашего тикета:',
            view=view,
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
    
    @discord.ui.button(label="Принять", style=discord.ButtonStyle.primary, emoji="✋", custom_id="ticket_claim_button")
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
    
    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_button")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        modal = CloseTicketModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Добавить участника", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_user_button")
    async def add_user_button(self, interaction: discord.Interaction, button: Button):
        modal = AddUserModal()
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
        
        # Создание транскрипта
        await interaction.response.send_message('📝 Создание транскрипта...', ephemeral=True)
        
        try:
            transcript_file = await create_ticket_transcript(interaction.channel)
            
            # Отправка транскрипта создателю тикета
            user = interaction.guild.get_member(int(ticket['user_id']))
            if user:
                try:
                    with open(transcript_file, 'rb') as f:
                        file = discord.File(f, filename=transcript_file)
                        await user.send(
                            f'📋 Транскрипт вашего тикета #{ticket["number"]:04d}',
                            file=file
                        )
                except:
                    pass
            
            # Удаление файла транскрипта
            if os.path.exists(transcript_file):
                os.remove(transcript_file)
        except:
            pass
        
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
        
        await interaction.channel.send(embed=embed)
        
        # Удаление канала через 10 секунд
        await interaction.channel.send('⏱️ Канал будет удален через 10 секунд...')
        await asyncio.sleep(10)
        
        try:
            await interaction.channel.delete()
        except:
            pass


class AddUserModal(Modal, title='Добавить участника'):
    """Модальное окно для добавления участника в тикет"""
    user_id = TextInput(
        label='ID пользователя',
        placeholder='Введите ID пользователя...',
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message('❌ Пользователь не найден.', ephemeral=True)
                return
            
            await interaction.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True
            )
            
            await interaction.response.send_message(
                f'✅ {member.mention} добавлен в тикет.',
                ephemeral=False
            )
        except ValueError:
            await interaction.response.send_message('❌ Неверный ID пользователя.', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


# ==================== Фоновые задачи ====================

@tasks.loop(seconds=30)
async def check_reminders():
    """Проверка напоминаний"""
    reminders = load_reminders()
    current_time = datetime.datetime.now()
    
    to_remove = []
    
    for reminder_id, reminder_data in reminders.items():
        remind_time = datetime.datetime.fromisoformat(reminder_data['time'])
        if current_time >= remind_time:
            guild = bot.get_guild(int(reminder_data['guild_id']))
            if guild:
                channel = guild.get_channel(int(reminder_data['channel_id']))
                user = guild.get_member(int(reminder_data['user_id']))
                if channel and user:
                    try:
                        await channel.send(f'⏰ {user.mention}, напоминание: {reminder_data["message"]}')
                    except:
                        pass
            to_remove.append(reminder_id)
    
    for reminder_id in to_remove:
        del reminders[reminder_id]
    
    if to_remove:
        save_reminders(reminders)


@tasks.loop(seconds=60)
async def check_giveaways():
    """Проверка розыгрышей"""
    giveaways = load_giveaways()
    current_time = datetime.datetime.now()
    
    for giveaway_id, giveaway_data in list(giveaways.items()):
        if giveaway_data['status'] == 'active':
            end_time = datetime.datetime.fromisoformat(giveaway_data['end_time'])
            if current_time >= end_time:
                guild = bot.get_guild(int(giveaway_data['guild_id']))
                if guild:
                    channel = guild.get_channel(int(giveaway_data['channel_id']))
                    if channel:
                        try:
                            message = await channel.fetch_message(int(giveaway_id))
                            
                            # Получение участников
                            participants = giveaway_data.get('participants', [])
                            
                            if participants:
                                winners_count = giveaway_data.get('winners', 1)
                                winners = random.sample(participants, min(winners_count, len(participants)))
                                
                                winner_mentions = ', '.join([f'<@{w}>' for w in winners])
                                
                                embed = discord.Embed(
                                    title='🎉 Розыгрыш завершен!',
                                    description=f'**Приз:** {giveaway_data["prize"]}\n**Победители:** {winner_mentions}',
                                    color=discord.Color.gold()
                                )
                                
                                await channel.send(embed=embed)
                                await message.edit(content='🎉 **РОЗЫГРЫШ ЗАВЕРШЕН**', embed=embed, view=None)
                            else:
                                await channel.send('❌ Нет участников розыгрыша.')
                            
                            giveaways[giveaway_id]['status'] = 'ended'
                            save_giveaways(giveaways)
                        except:
                            pass


# ==================== События ====================

@bot.event
async def on_ready():
    """Событие при запуске бота"""
    print(f'✅ Бот {bot.user} успешно подключился к Discord!')
    print(f'📊 Подключен к {len(bot.guilds)} серверам')
    
    # Регистрация persistent views
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(VerificationView())
    print('✅ Persistent views зарегистрированы')
    
    # Запуск фоновых задач
    if not check_reminders.is_running():
        check_reminders.start()
    if not check_giveaways.is_running():
        check_giveaways.start()
    print('✅ Фоновые задачи запущены')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} slash-команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации команд: {e}')


@bot.event
async def on_member_join(member):
    """Обработка входа нового участника"""
    guild_id = str(member.guild.id)
    
    # Автовыдача ролей
    auto_roles = load_auto_roles()
    if auto_roles:
        for role_name in auto_roles:
            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                try:
                    await member.add_roles(role)
                except:
                    pass
    
    # Приветственное сообщение
    welcome_config = load_welcome_config()
    if guild_id in welcome_config and 'welcome_channel' in welcome_config[guild_id]:
        channel_id = welcome_config[guild_id]['welcome_channel']
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            message = welcome_config[guild_id].get('welcome_message', 'Добро пожаловать, {user}!')
            formatted_message = format_welcome_message(message, member, member.guild)
            try:
                await channel.send(formatted_message)
            except:
                pass
    
    # Лог
    embed = discord.Embed(
        title='📥 Новый участник',
        description=f'{member.mention} присоединился к серверу',
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name='Аккаунт создан', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_log(member.guild, 'member_log', embed)


@bot.event
async def on_member_remove(member):
    """Обработка выхода участника"""
    guild_id = str(member.guild.id)
    
    # Прощальное сообщение
    welcome_config = load_welcome_config()
    if guild_id in welcome_config and 'goodbye_channel' in welcome_config[guild_id]:
        channel_id = welcome_config[guild_id]['goodbye_channel']
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            message = welcome_config[guild_id].get('goodbye_message', 'Прощай, {username}!')
            formatted_message = format_welcome_message(message, member, member.guild)
            try:
                await channel.send(formatted_message)
            except:
                pass
    
    # Лог
    embed = discord.Embed(
        title='📤 Участник покинул сервер',
        description=f'{member.mention} ({member.name})',
        color=discord.Color.red(),
        timestamp=datetime.datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_log(member.guild, 'member_log', embed)


@bot.event
async def on_message(message):
    """Обработка сообщений"""
    if message.author.bot:
        return
    
    guild_id = str(message.guild.id) if message.guild else None
    
    if guild_id:
        # Фильтр слов
        word_filter = load_word_filter()
        if guild_id in word_filter and word_filter[guild_id].get('enabled', False):
            bad_words = word_filter[guild_id].get('words', [])
            if any(bad_word.lower() in message.content.lower() for bad_word in bad_words):
                try:
                    await message.delete()
                    await message.author.send('⚠️ Ваше сообщение было удалено, так как содержит недопустимые выражения.')
                except:
                    pass
                return
        
        # Анти-спам
        antispam_config = load_antispam_config()
        if guild_id in antispam_config and antispam_config[guild_id].get('enabled', False):
            user_id = str(message.author.id)
            current_time = datetime.datetime.now()
            
            # Добавление сообщения в кэш
            user_message_cache[user_id].append({
                'content': message.content,
                'time': current_time
            })
            
            # Очистка старых сообщений (старше 10 секунд)
            user_message_cache[user_id] = [
                msg for msg in user_message_cache[user_id]
                if (current_time - msg['time']).total_seconds() < 10
            ]
            
            # Проверка на спам
            if len(user_message_cache[user_id]) >= 5:
                user_spam_warnings[user_id] += 1
                
                try:
                    await message.channel.purge(limit=5, check=lambda m: m.author == message.author)
                    
                    if user_spam_warnings[user_id] >= 3:
                        # Таймаут на 10 минут
                        try:
                            await message.author.timeout(datetime.timedelta(minutes=10), reason='Спам')
                            await message.channel.send(f'🔇 {message.author.mention} получил таймаут за спам.')
                            user_spam_warnings[user_id] = 0
                        except:
                            pass
                    else:
                        await message.channel.send(f'⚠️ {message.author.mention}, не спамьте! Предупреждение {user_spam_warnings[user_id]}/3')
                except:
                    pass
                
                user_message_cache[user_id].clear()
                return
        
        # Система уровней
        levels = load_levels()
        user_id = str(message.author.id)
        
        if guild_id not in levels:
            levels[guild_id] = {}
        
        if user_id not in levels[guild_id]:
            levels[guild_id][user_id] = {'xp': 0, 'level': 0, 'messages': 0}
        
        # Добавление XP (5-15 за сообщение)
        xp_gain = random.randint(5, 15)
        levels[guild_id][user_id]['xp'] += xp_gain
        levels[guild_id][user_id]['messages'] += 1
        
        # Проверка повышения уровня
        old_level = levels[guild_id][user_id]['level']
        new_level = calculate_level(levels[guild_id][user_id]['xp'])
        
        if new_level > old_level:
            levels[guild_id][user_id]['level'] = new_level
            try:
                await message.channel.send(
                    f'🎉 {message.author.mention} достиг уровня **{new_level}**!'
                )
            except:
                pass
        
        save_levels(levels)
        
        # Кастомные команды
        custom_commands = load_custom_commands()
        if guild_id in custom_commands:
            for cmd_name, cmd_response in custom_commands[guild_id].items():
                if message.content.lower() == f'!{cmd_name.lower()}':
                    await message.channel.send(cmd_response)
                    return
    
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    """Обработка добавления реакций для Reaction Roles"""
    if payload.member.bot:
        return
    
    reaction_roles = load_reaction_roles()
    guild_id = str(payload.guild_id)
    message_id = str(payload.message_id)
    
    if guild_id in reaction_roles and message_id in reaction_roles[guild_id]:
        emoji_str = str(payload.emoji)
        if emoji_str in reaction_roles[guild_id][message_id]:
            role_id = reaction_roles[guild_id][message_id][emoji_str]
            guild = bot.get_guild(payload.guild_id)
            if guild:
                role = guild.get_role(int(role_id))
                if role:
                    try:
                        await payload.member.add_roles(role)
                    except:
                        pass


@bot.event
async def on_raw_reaction_remove(payload):
    """Обработка удаления реакций для Reaction Roles"""
    reaction_roles = load_reaction_roles()
    guild_id = str(payload.guild_id)
    message_id = str(payload.message_id)
    
    if guild_id in reaction_roles and message_id in reaction_roles[guild_id]:
        emoji_str = str(payload.emoji)
        if emoji_str in reaction_roles[guild_id][message_id]:
            role_id = reaction_roles[guild_id][message_id][emoji_str]
            guild = bot.get_guild(payload.guild_id)
            if guild:
                role = guild.get_role(int(role_id))
                member = guild.get_member(payload.user_id)
                if role and member:
                    try:
                        await member.remove_roles(role)
                    except:
                        pass


# ==================== Slash-команды: Модерация ====================

@bot.tree.command(name="timeout", description="Выдать таймаут пользователю")
@app_commands.describe(
    member="Пользователь для таймаута",
    duration="Длительность (например: 10m, 1h, 1d)",
    reason="Причина таймаута"
)
async def timeout_cmd(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Причина не указана"):
    """Выдает таймаут пользователю"""
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message('❌ У вас нет прав модератора.', ephemeral=True)
        return
    
    seconds = parse_time(duration)
    if not seconds or seconds > 2419200:
        await interaction.response.send_message('❌ Неверная длительность. Используйте формат: 10m, 1h, 1d (максимум 28d)', ephemeral=True)
        return
    
    try:
        await member.timeout(datetime.timedelta(seconds=seconds), reason=reason)
        
        embed = discord.Embed(
            title='🔇 Таймаут выдан',
            color=discord.Color.orange()
        )
        embed.add_field(name='Пользователь', value=member.mention, inline=True)
        embed.add_field(name='Длительность', value=format_time(seconds), inline=True)
        embed.add_field(name='Причина', value=reason, inline=False)
        embed.add_field(name='Модератор', value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        await send_log(interaction.guild, 'mod_log', embed)
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для выдачи таймаута этому пользователю.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="untimeout", description="Снять таймаут с пользователя")
@app_commands.describe(member="Пользователь для снятия таймаута")
async def untimeout_cmd(interaction: discord.Interaction, member: discord.Member):
    """Снимает таймаут с пользователя"""
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message('❌ У вас нет прав модератора.', ephemeral=True)
        return
    
    try:
        await member.timeout(None)
        await interaction.response.send_message(f'✅ Таймаут снят с {member.mention}')
        
        embed = discord.Embed(
            title='🔊 Таймаут снят',
            description=f'Модератор {interaction.user.mention} снял таймаут с {member.mention}',
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        await send_log(interaction.guild, 'mod_log', embed)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


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
    
    view = ConfirmView()
    await interaction.response.send_message(
        f'⚠️ Вы уверены, что хотите заблокировать {member.mention}?\nПричина: {reason}',
        view=view,
        ephemeral=True
    )
    
    await view.wait()
    
    if view.value:
        try:
            await member.ban(reason=reason)
            await interaction.followup.send(f'✅ Пользователь {member.mention} заблокирован. Причина: {reason}', ephemeral=True)
            
            embed = discord.Embed(
                title='🔨 Пользователь заблокирован',
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name='Пользователь', value=f'{member.mention} ({member.name})', inline=True)
            embed.add_field(name='Модератор', value=interaction.user.mention, inline=True)
            embed.add_field(name='Причина', value=reason, inline=False)
            await send_log(interaction.guild, 'mod_log', embed)
        except discord.Forbidden:
            await interaction.followup.send('❌ У бота нет прав для блокировки этого пользователя.', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Ошибка: {e}', ephemeral=True)
    else:
        await interaction.followup.send('❌ Блокировка отменена.', ephemeral=True)


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
    
    view = ConfirmView()
    await interaction.response.send_message(
        f'⚠️ Вы уверены, что хотите исключить {member.mention}?\nПричина: {reason}',
        view=view,
        ephemeral=True
    )
    
    await view.wait()
    
    if view.value:
        try:
            await member.kick(reason=reason)
            await interaction.followup.send(f'✅ Пользователь {member.mention} исключен. Причина: {reason}', ephemeral=True)
            
            embed = discord.Embed(
                title='👢 Пользователь исключен',
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name='Пользователь', value=f'{member.mention} ({member.name})', inline=True)
            embed.add_field(name='Модератор', value=interaction.user.mention, inline=True)
            embed.add_field(name='Причина', value=reason, inline=False)
            await send_log(interaction.guild, 'mod_log', embed)
        except discord.Forbidden:
            await interaction.followup.send('❌ У бота нет прав для исключения этого пользователя.', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Ошибка: {e}', ephemeral=True)
    else:
        await interaction.followup.send('❌ Исключение отменено.', ephemeral=True)


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
        
        embed = discord.Embed(
            title='🗑️ Сообщения удалены',
            description=f'Модератор {interaction.user.mention} удалил {len(deleted)} сообщений в {interaction.channel.mention}',
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        await send_log(interaction.guild, 'mod_log', embed)
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
        'moderator_id': interaction.user.id,
        'guild_id': interaction.guild.id
    })

    save_warnings(warnings)
    
    warn_count = len(warnings[user_id])
    
    embed = discord.Embed(
        title='⚠️ Предупреждение',
        description=f'Пользователю {member.mention} выдано предупреждение',
        color=discord.Color.orange()
    )
    embed.add_field(name='Причина', value=reason, inline=False)
    embed.add_field(name='Модератор', value=interaction.user.mention, inline=True)
    embed.add_field(name='Всего предупреждений', value=str(warn_count), inline=True)
    
    await interaction.response.send_message(embed=embed)
    
    # Авто-действия при достижении порога
    if warn_count >= 5:
        try:
            await member.ban(reason=f'Достигнуто {warn_count} предупреждений')
            await interaction.channel.send(f'🔨 {member.mention} автоматически заблокирован за {warn_count} предупреждений.')
        except:
            pass
    elif warn_count >= 3:
        try:
            await member.timeout(datetime.timedelta(hours=1), reason=f'Достигнуто {warn_count} предупреждений')
            await interaction.channel.send(f'🔇 {member.mention} получил таймаут на 1 час за {warn_count} предупреждения.')
        except:
            pass
    
    await send_log(interaction.guild, 'mod_log', embed)


@bot.tree.command(name="unwarn", description="Снять предупреждение с пользователя")
@app_commands.describe(
    member="Пользователь",
    warning_number="Номер предупреждения для снятия"
)
async def unwarn(interaction: discord.Interaction, member: discord.Member, warning_number: int):
    """Снимает предупреждение с пользователя"""
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message('❌ У вас нет прав модератора.', ephemeral=True)
        return

    warnings = load_warnings()
    user_id = str(member.id)

    if user_id not in warnings or not warnings[user_id]:
        await interaction.response.send_message(f'❌ У пользователя {member.mention} нет предупреждений.', ephemeral=True)
        return
    
    if warning_number < 1 or warning_number > len(warnings[user_id]):
        await interaction.response.send_message(f'❌ Неверный номер предупреждения. Доступно: 1-{len(warnings[user_id])}', ephemeral=True)
        return
    
    removed_warn = warnings[user_id].pop(warning_number - 1)
    save_warnings(warnings)
    
    await interaction.response.send_message(
        f'✅ Предупреждение #{warning_number} снято с {member.mention}\nПричина была: {removed_warn["reason"]}'
    )


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


# ==================== Команды управления ролями ====================

@bot.tree.command(name="role_add", description="Выдать роль пользователю")
@app_commands.describe(
    member="Пользователь",
    role="Роль для выдачи"
)
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Выдает роль пользователю"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    if role in member.roles:
        await interaction.response.send_message(f'❌ У {member.mention} уже есть роль {role.mention}', ephemeral=True)
        return
    
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f'✅ Роль {role.mention} выдана {member.mention}')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для выдачи этой роли.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="role_remove", description="Снять роль с пользователя")
@app_commands.describe(
    member="Пользователь",
    role="Роль для снятия"
)
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Снимает роль с пользователя"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    if role not in member.roles:
        await interaction.response.send_message(f'❌ У {member.mention} нет роли {role.mention}', ephemeral=True)
        return
    
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f'✅ Роль {role.mention} снята с {member.mention}')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для снятия этой роли.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="role_info", description="Информация о роли")
@app_commands.describe(role="Роль для просмотра")
async def role_info(interaction: discord.Interaction, role: discord.Role):
    """Показывает информацию о роли"""
    embed = discord.Embed(
        title=f'Информация о роли: {role.name}',
        color=role.color
    )
    embed.add_field(name='ID', value=str(role.id), inline=True)
    embed.add_field(name='Цвет', value=str(role.color), inline=True)
    embed.add_field(name='Участников', value=str(len(role.members)), inline=True)
    embed.add_field(name='Позиция', value=str(role.position), inline=True)
    embed.add_field(name='Упоминаемая', value='Да' if role.mentionable else 'Нет', inline=True)
    embed.add_field(name='Отображается отдельно', value='Да' if role.hoist else 'Нет', inline=True)
    embed.add_field(name='Создана', value=f'<t:{int(role.created_at.timestamp())}:R>', inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="role_create", description="Создать новую роль")
@app_commands.describe(
    name="Название роли",
    color="Цвет в HEX формате (например: #FF0000)"
)
async def role_create(interaction: discord.Interaction, name: str, color: str = None):
    """Создает новую роль"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    try:
        role_color = discord.Color.default()
        if color:
            try:
                role_color = discord.Color(int(color.replace('#', ''), 16))
            except:
                await interaction.response.send_message('❌ Неверный формат цвета. Используйте HEX (например: #FF0000)', ephemeral=True)
                return
        
        role = await interaction.guild.create_role(name=name, color=role_color)
        await interaction.response.send_message(f'✅ Роль {role.mention} создана!')
    except discord.Forbidden:
        await interaction.response.send_message('❌ У бота нет прав для создания ролей.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


# ==================== Информационные команды ====================

@bot.tree.command(name="serverinfo", description="Информация о сервере")
async def serverinfo(interaction: discord.Interaction):
    """Показывает информацию о сервере"""
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f'📊 Информация о сервере: {guild.name}',
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name='ID', value=str(guild.id), inline=True)
    embed.add_field(name='Владелец', value=guild.owner.mention if guild.owner else 'Неизвестно', inline=True)
    embed.add_field(name='Создан', value=f'<t:{int(guild.created_at.timestamp())}:R>', inline=True)
    embed.add_field(name='Участников', value=str(guild.member_count), inline=True)
    embed.add_field(name='Ролей', value=str(len(guild.roles)), inline=True)
    embed.add_field(name='Каналов', value=str(len(guild.channels)), inline=True)
    embed.add_field(name='Эмодзи', value=str(len(guild.emojis)), inline=True)
    embed.add_field(name='Уровень буста', value=f'Уровень {guild.premium_tier}', inline=True)
    embed.add_field(name='Бустов', value=str(guild.premium_subscription_count or 0), inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userinfo", description="Информация о пользователе")
@app_commands.describe(member="Пользователь для просмотра")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    """Показывает информацию о пользователе"""
    member = member or interaction.user
    
    embed = discord.Embed(
        title=f'👤 Информация о пользователе: {member.name}',
        color=member.color,
        timestamp=datetime.datetime.now()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    embed.add_field(name='ID', value=str(member.id), inline=True)
    embed.add_field(name='Никнейм', value=member.display_name, inline=True)
    embed.add_field(name='Бот', value='Да' if member.bot else 'Нет', inline=True)
    embed.add_field(name='Аккаунт создан', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=True)
    embed.add_field(name='Присоединился', value=f'<t:{int(member.joined_at.timestamp())}:R>', inline=True)
    embed.add_field(name='Ролей', value=str(len(member.roles) - 1), inline=True)
    
    # Роли
    if len(member.roles) > 1:
        roles = [role.mention for role in sorted(member.roles[1:], key=lambda r: r.position, reverse=True)]
        roles_text = ', '.join(roles[:10])
        if len(member.roles) > 11:
            roles_text += f' и еще {len(member.roles) - 11}'
        embed.add_field(name='Роли', value=roles_text, inline=False)
    
    # Уровень
    levels = load_levels()
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    if guild_id in levels and user_id in levels[guild_id]:
        user_data = levels[guild_id][user_id]
        embed.add_field(name='Уровень', value=str(user_data['level']), inline=True)
        embed.add_field(name='XP', value=str(user_data['xp']), inline=True)
        embed.add_field(name='Сообщений', value=str(user_data['messages']), inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Показать аватар пользователя")
@app_commands.describe(member="Пользователь")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    """Показывает аватар пользователя"""
    member = member or interaction.user
    
    embed = discord.Embed(
        title=f'Аватар пользователя {member.name}',
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)


# ==================== Команды авторолей ====================

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


# ==================== Команды фильтра слов ====================

@bot.tree.command(name="filter_add", description="Добавить слово в фильтр")
@app_commands.describe(word="Слово для добавления в фильтр")
async def filter_add(interaction: discord.Interaction, word: str):
    """Добавляет слово в фильтр"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return
    
    word_filter = load_word_filter()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in word_filter:
        word_filter[guild_id] = {'enabled': True, 'words': []}
    
    if word.lower() in [w.lower() for w in word_filter[guild_id]['words']]:
        await interaction.response.send_message(f'❌ Слово "{word}" уже в фильтре.', ephemeral=True)
        return
    
    word_filter[guild_id]['words'].append(word)
    save_word_filter(word_filter)
    
    await interaction.response.send_message(f'✅ Слово "{word}" добавлено в фильтр.')


@bot.tree.command(name="filter_remove", description="Удалить слово из фильтра")
@app_commands.describe(word="Слово для удаления из фильтра")
async def filter_remove(interaction: discord.Interaction, word: str):
    """Удаляет слово из фильтра"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return
    
    word_filter = load_word_filter()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in word_filter or word not in word_filter[guild_id]['words']:
        await interaction.response.send_message(f'❌ Слово "{word}" не найдено в фильтре.', ephemeral=True)
        return
    
    word_filter[guild_id]['words'].remove(word)
    save_word_filter(word_filter)
    
    await interaction.response.send_message(f'✅ Слово "{word}" удалено из фильтра.')


@bot.tree.command(name="filter_list", description="Показать список фильтруемых слов")
async def filter_list(interaction: discord.Interaction):
    """Показывает список фильтруемых слов"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return
    
    word_filter = load_word_filter()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in word_filter or not word_filter[guild_id]['words']:
        await interaction.response.send_message('📋 Фильтр слов пуст.', ephemeral=True)
        return
    
    embed = discord.Embed(
        title='📋 Фильтр слов',
        description='\n'.join(f'• ||{word}||' for word in word_filter[guild_id]['words']),
        color=discord.Color.red()
    )
    embed.set_footer(text=f'Статус: {"Включен" if word_filter[guild_id].get("enabled", False) else "Выключен"}')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="filter_toggle", description="Включить/выключить фильтр слов")
async def filter_toggle(interaction: discord.Interaction):
    """Включает или выключает фильтр слов"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return
    
    word_filter = load_word_filter()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in word_filter:
        word_filter[guild_id] = {'enabled': True, 'words': []}
    
    word_filter[guild_id]['enabled'] = not word_filter[guild_id].get('enabled', False)
    save_word_filter(word_filter)
    
    status = 'включен' if word_filter[guild_id]['enabled'] else 'выключен'
    await interaction.response.send_message(f'✅ Фильтр слов {status}.')


# ==================== Команды приветствий ====================

@bot.tree.command(name="welcome_setup", description="Настроить приветственные сообщения")
@app_commands.describe(
    channel="Канал для приветствий",
    message="Сообщение приветствия (используйте {user}, {username}, {server}, {member_count})"
)
async def welcome_setup(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    """Настраивает приветственные сообщения"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_config:
        welcome_config[guild_id] = {}
    
    welcome_config[guild_id]['welcome_channel'] = channel.id
    welcome_config[guild_id]['welcome_message'] = message
    save_welcome_config(welcome_config)
    
    await interaction.response.send_message(
        f'✅ Приветствия настроены!\n**Канал:** {channel.mention}\n**Сообщение:** {message}'
    )


@bot.tree.command(name="goodbye_setup", description="Настроить прощальные сообщения")
@app_commands.describe(
    channel="Канал для прощаний",
    message="Сообщение прощания (используйте {user}, {username}, {server}, {member_count})"
)
async def goodbye_setup(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    """Настраивает прощальные сообщения"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    welcome_config = load_welcome_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_config:
        welcome_config[guild_id] = {}
    
    welcome_config[guild_id]['goodbye_channel'] = channel.id
    welcome_config[guild_id]['goodbye_message'] = message
    save_welcome_config(welcome_config)
    
    await interaction.response.send_message(
        f'✅ Прощания настроены!\n**Канал:** {channel.mention}\n**Сообщение:** {message}'
    )


# ==================== Команды логирования ====================

@bot.tree.command(name="log_setup", description="Настроить канал логирования")
@app_commands.describe(
    log_type="Тип логов (mod_log, member_log, message_log)",
    channel="Канал для логов"
)
async def log_setup(interaction: discord.Interaction, log_type: str, channel: discord.TextChannel):
    """Настраивает канал логирования"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    valid_types = ['mod_log', 'member_log', 'message_log']
    if log_type not in valid_types:
        await interaction.response.send_message(
            f'❌ Неверный тип логов. Доступные: {", ".join(valid_types)}',
            ephemeral=True
        )
        return
    
    logs_config = load_logs_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in logs_config:
        logs_config[guild_id] = {}
    
    logs_config[guild_id][log_type] = channel.id
    save_logs_config(logs_config)
    
    await interaction.response.send_message(
        f'✅ Логи типа **{log_type}** будут отправляться в {channel.mention}'
    )


# ==================== Команды опросов ====================

@bot.tree.command(name="poll", description="Создать опрос")
@app_commands.describe(
    question="Вопрос опроса",
    option1="Вариант 1",
    option2="Вариант 2",
    option3="Вариант 3 (необязательно)",
    option4="Вариант 4 (необязательно)",
    option5="Вариант 5 (необязательно)"
)
async def poll(
    interaction: discord.Interaction,
    question: str,
    option1: str,
    option2: str,
    option3: str = None,
    option4: str = None,
    option5: str = None
):
    """Создает опрос с автоматическими реакциями"""
    options = [option1, option2]
    if option3:
        options.append(option3)
    if option4:
        options.append(option4)
    if option5:
        options.append(option5)
    
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    
    embed = discord.Embed(
        title=f'📊 {question}',
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    for i, option in enumerate(options):
        embed.add_field(name=f'{emojis[i]} {option}', value='\u200b', inline=False)
    
    embed.set_footer(text=f'Опрос создан {interaction.user.name}')
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    for i in range(len(options)):
        await message.add_reaction(emojis[i])


# ==================== Команды напоминаний ====================

@bot.tree.command(name="remind", description="Создать напоминание")
@app_commands.describe(
    time="Время (например: 10m, 1h, 1d)",
    message="Текст напоминания"
)
async def remind(interaction: discord.Interaction, time: str, message: str):
    """Создает напоминание"""
    seconds = parse_time(time)
    if not seconds:
        await interaction.response.send_message(
            '❌ Неверный формат времени. Используйте: 10m, 1h, 1d',
            ephemeral=True
        )
        return
    
    reminders = load_reminders()
    reminder_id = str(int(datetime.datetime.now().timestamp() * 1000))
    
    remind_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    
    reminders[reminder_id] = {
        'user_id': interaction.user.id,
        'guild_id': interaction.guild.id,
        'channel_id': interaction.channel.id,
        'message': message,
        'time': remind_time.isoformat()
    }
    
    save_reminders(reminders)
    
    await interaction.response.send_message(
        f'✅ Напоминание установлено на <t:{int(remind_time.timestamp())}:R>\n**Сообщение:** {message}'
    )


# ==================== Команды Reaction Roles ====================

@bot.tree.command(name="reactionrole_setup", description="Настроить Reaction Roles")
@app_commands.describe(
    message_id="ID сообщения",
    emoji="Эмодзи",
    role="Роль для выдачи"
)
async def reactionrole_setup(interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
    """Настраивает Reaction Roles"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message('❌ У вас нет прав на управление ролями.', ephemeral=True)
        return
    
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message('❌ Сообщение не найдено.', ephemeral=True)
        return
    
    reaction_roles = load_reaction_roles()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in reaction_roles:
        reaction_roles[guild_id] = {}
    
    if message_id not in reaction_roles[guild_id]:
        reaction_roles[guild_id][message_id] = {}
    
    reaction_roles[guild_id][message_id][emoji] = role.id
    save_reaction_roles(reaction_roles)
    
    try:
        await message.add_reaction(emoji)
    except:
        pass
    
    await interaction.response.send_message(
        f'✅ Reaction Role настроен!\n**Эмодзи:** {emoji}\n**Роль:** {role.mention}'
    )


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
    
    config = load_ticket_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {}
    
    if category:
        config[guild_id]['category_id'] = category.id
    
    if support_role:
        config[guild_id]['support_role_id'] = support_role.id
    
    save_ticket_config(config)
    
    embed = discord.Embed(
        title='🎫 Tickets v2',
        description='**Откройте билет!**\nНажав на кнопку, вы откроете билет.',
        color=discord.Color.blue()
    )
    embed.set_footer(text='Powered by Nobame')
    
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
    
    if open_tickets > 0:
        open_list = []
        for ticket_id, ticket in guild_tickets.items():
            if ticket['status'] == 'open':
                channel = interaction.guild.get_channel(int(ticket['channel_id']))
                if channel:
                    status = '✋' if ticket['claimed_by'] else '🟢'
                    open_list.append(f"{status} {channel.mention} - <@{ticket['user_id']}>")
        
        if open_list:
            embed.add_field(
                name='Открытые тикеты',
                value='\n'.join(open_list[:10]),
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ticket_close_all", description="Закрыть все открытые тикеты (только для администраторов)")
async def ticket_close_all(interaction: discord.Interaction):
    """Закрывает все открытые тикеты на сервере"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Эта команда доступна только администраторам.', ephemeral=True)
        return
    
    tickets = load_tickets()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in tickets:
        await interaction.response.send_message('❌ На этом сервере нет тикетов.', ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    closed_count = 0
    for ticket_id, ticket in tickets[guild_id].items():
        if ticket['status'] == 'open':
            channel = interaction.guild.get_channel(int(ticket['channel_id']))
            if channel:
                try:
                    await channel.delete(reason='Массовое закрытие тикетов администратором')
                    ticket['status'] = 'closed'
                    ticket['closed_by'] = interaction.user.id
                    ticket['closed_at'] = datetime.datetime.now().isoformat()
                    ticket['close_reason'] = 'Массовое закрытие администратором'
                    closed_count += 1
                except:
                    pass
    
    save_tickets(tickets)
    
    await interaction.followup.send(f'✅ Закрыто тикетов: {closed_count}', ephemeral=True)


# ==================== Команды кастомных команд ====================

@bot.tree.command(name="customcmd_add", description="Добавить кастомную команду")
@app_commands.describe(
    name="Название команды (без !)",
    response="Ответ команды"
)
async def customcmd_add(interaction: discord.Interaction, name: str, response: str):
    """Добавляет кастомную команду"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    custom_commands = load_custom_commands()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in custom_commands:
        custom_commands[guild_id] = {}
    
    if name.lower() in custom_commands[guild_id]:
        await interaction.response.send_message(f'❌ Команда `!{name}` уже существует.', ephemeral=True)
        return
    
    custom_commands[guild_id][name.lower()] = response
    save_custom_commands(custom_commands)
    
    await interaction.response.send_message(f'✅ Кастомная команда `!{name}` создана!')


@bot.tree.command(name="customcmd_remove", description="Удалить кастомную команду")
@app_commands.describe(name="Название команды для удаления")
async def customcmd_remove(interaction: discord.Interaction, name: str):
    """Удаляет кастомную команду"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    custom_commands = load_custom_commands()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in custom_commands or name.lower() not in custom_commands[guild_id]:
        await interaction.response.send_message(f'❌ Команда `!{name}` не найдена.', ephemeral=True)
        return
    
    del custom_commands[guild_id][name.lower()]
    save_custom_commands(custom_commands)
    
    await interaction.response.send_message(f'✅ Кастомная команда `!{name}` удалена.')


@bot.tree.command(name="customcmd_list", description="Показать список кастомных команд")
async def customcmd_list(interaction: discord.Interaction):
    """Показывает список кастомных команд"""
    custom_commands = load_custom_commands()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in custom_commands or not custom_commands[guild_id]:
        await interaction.response.send_message('📋 Нет кастомных команд.', ephemeral=True)
        return
    
    embed = discord.Embed(
        title='📋 Кастомные команды',
        description='\n'.join(f'• `!{cmd}`' for cmd in custom_commands[guild_id].keys()),
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed)


# ==================== Команды розыгрышей ====================

class GiveawayView(View):
    """View для участия в розыгрыше"""
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(label="Участвовать", style=discord.ButtonStyle.green, emoji="🎉", custom_id="giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        giveaways = load_giveaways()
        
        if self.giveaway_id not in giveaways:
            await interaction.response.send_message('❌ Розыгрыш не найден.', ephemeral=True)
            return
        
        giveaway = giveaways[self.giveaway_id]
        
        if giveaway['status'] != 'active':
            await interaction.response.send_message('❌ Розыгрыш завершен.', ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        if 'participants' not in giveaway:
            giveaway['participants'] = []
        
        if user_id in giveaway['participants']:
            await interaction.response.send_message('❌ Вы уже участвуете в этом розыгрыше!', ephemeral=True)
            return
        
        giveaway['participants'].append(user_id)
        save_giveaways(giveaways)
        
        await interaction.response.send_message('✅ Вы участвуете в розыгрыше!', ephemeral=True)


@bot.tree.command(name="giveaway_start", description="Начать розыгрыш")
@app_commands.describe(
    duration="Длительность (например: 1h, 1d)",
    winners="Количество победителей",
    prize="Приз"
)
async def giveaway_start(interaction: discord.Interaction, duration: str, winners: int, prize: str):
    """Начинает розыгрыш"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    seconds = parse_time(duration)
    if not seconds:
        await interaction.response.send_message('❌ Неверный формат времени. Используйте: 1h, 1d', ephemeral=True)
        return
    
    if winners < 1:
        await interaction.response.send_message('❌ Количество победителей должно быть больше 0.', ephemeral=True)
        return
    
    end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    
    embed = discord.Embed(
        title='🎉 РОЗЫГРЫШ!',
        description=f'**Приз:** {prize}\n**Победителей:** {winners}\n**Завершится:** <t:{int(end_time.timestamp())}:R>',
        color=discord.Color.gold()
    )
    embed.set_footer(text=f'Организатор: {interaction.user.name}')
    
    view = GiveawayView('temp')
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    giveaways = load_giveaways()
    giveaway_id = str(message.id)
    
    giveaways[giveaway_id] = {
        'guild_id': interaction.guild.id,
        'channel_id': interaction.channel.id,
        'message_id': message.id,
        'prize': prize,
        'winners': winners,
        'end_time': end_time.isoformat(),
        'status': 'active',
        'participants': [],
        'host_id': interaction.user.id
    }
    
    save_giveaways(giveaways)


@bot.tree.command(name="giveaway_end", description="Завершить розыгрыш досрочно")
@app_commands.describe(message_id="ID сообщения розыгрыша")
async def giveaway_end(interaction: discord.Interaction, message_id: str):
    """Завершает розыгрыш досрочно"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    giveaways = load_giveaways()
    
    if message_id not in giveaways:
        await interaction.response.send_message('❌ Розыгрыш не найден.', ephemeral=True)
        return
    
    giveaway = giveaways[message_id]
    
    if giveaway['status'] != 'active':
        await interaction.response.send_message('❌ Розыгрыш уже завершен.', ephemeral=True)
        return
    
    try:
        channel = interaction.guild.get_channel(int(giveaway['channel_id']))
        message = await channel.fetch_message(int(message_id))
        
        participants = giveaway.get('participants', [])
        
        if participants:
            winners_count = giveaway.get('winners', 1)
            winners = random.sample(participants, min(winners_count, len(participants)))
            
            winner_mentions = ', '.join([f'<@{w}>' for w in winners])
            
            embed = discord.Embed(
                title='🎉 Розыгрыш завершен!',
                description=f'**Приз:** {giveaway["prize"]}\n**Победители:** {winner_mentions}',
                color=discord.Color.gold()
            )
            
            await channel.send(embed=embed)
            await message.edit(content='🎉 **РОЗЫГРЫШ ЗАВЕРШЕН**', embed=embed, view=None)
        else:
            await channel.send('❌ Нет участников розыгрыша.')
        
        giveaway['status'] = 'ended'
        save_giveaways(giveaways)
        
        await interaction.response.send_message('✅ Розыгрыш завершен!', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Ошибка: {e}', ephemeral=True)


@bot.tree.command(name="giveaway_reroll", description="Перевыбрать победителя розыгрыша")
@app_commands.describe(message_id="ID сообщения розыгрыша")
async def giveaway_reroll(interaction: discord.Interaction, message_id: str):
    """Перевыбирает победителя розыгрыша"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    giveaways = load_giveaways()
    
    if message_id not in giveaways:
        await interaction.response.send_message('❌ Розыгрыш не найден.', ephemeral=True)
        return
    
    giveaway = giveaways[message_id]
    participants = giveaway.get('participants', [])
    
    if not participants:
        await interaction.response.send_message('❌ Нет участников для перевыбора.', ephemeral=True)
        return
    
    winner = random.choice(participants)
    
    embed = discord.Embed(
        title='🎉 Новый победитель!',
        description=f'**Приз:** {giveaway["prize"]}\n**Победитель:** <@{winner}>',
        color=discord.Color.gold()
    )
    
    await interaction.response.send_message(embed=embed)


# ==================== Команды уровней ====================

@bot.tree.command(name="level", description="Показать свой уровень или уровень пользователя")
@app_commands.describe(member="Пользователь (необязательно)")
async def level(interaction: discord.Interaction, member: discord.Member = None):
    """Показывает уровень пользователя"""
    member = member or interaction.user
    
    levels = load_levels()
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    
    if guild_id not in levels or user_id not in levels[guild_id]:
        await interaction.response.send_message(f'❌ У {member.mention} еще нет уровня.', ephemeral=True)
        return
    
    user_data = levels[guild_id][user_id]
    current_level = user_data['level']
    current_xp = user_data['xp']
    next_level_xp = xp_for_level(current_level + 1)
    progress = current_xp - xp_for_level(current_level)
    needed = next_level_xp - xp_for_level(current_level)
    
    embed = discord.Embed(
        title=f'📊 Уровень {member.display_name}',
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='Уровень', value=str(current_level), inline=True)
    embed.add_field(name='XP', value=f'{current_xp}/{next_level_xp}', inline=True)
    embed.add_field(name='Сообщений', value=str(user_data['messages']), inline=True)
    embed.add_field(name='Прогресс', value=f'{progress}/{needed} XP до следующего уровня', inline=False)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="Показать таблицу лидеров")
async def leaderboard(interaction: discord.Interaction):
    """Показывает таблицу лидеров по уровням"""
    levels = load_levels()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in levels or not levels[guild_id]:
        await interaction.response.send_message('📊 Еще нет данных для таблицы лидеров.', ephemeral=True)
        return
    
    # Сортировка по XP
    sorted_users = sorted(
        levels[guild_id].items(),
        key=lambda x: x[1]['xp'],
        reverse=True
    )[:10]
    
    embed = discord.Embed(
        title='🏆 Таблица лидеров',
        color=discord.Color.gold()
    )
    
    medals = ['🥇', '🥈', '🥉']
    
    for i, (user_id, data) in enumerate(sorted_users, 1):
        member = interaction.guild.get_member(int(user_id))
        if member:
            medal = medals[i-1] if i <= 3 else f'`#{i}`'
            embed.add_field(
                name=f'{medal} {member.display_name}',
                value=f'Уровень {data["level"]} • {data["xp"]} XP • {data["messages"]} сообщений',
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setlevel", description="Установить уровень пользователю")
@app_commands.describe(
    member="Пользователь",
    level="Уровень"
)
async def setlevel(interaction: discord.Interaction, member: discord.Member, level: int):
    """Устанавливает уровень пользователю"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Эта команда доступна только администраторам.', ephemeral=True)
        return
    
    if level < 0:
        await interaction.response.send_message('❌ Уровень не может быть отрицательным.', ephemeral=True)
        return
    
    levels = load_levels()
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)
    
    if guild_id not in levels:
        levels[guild_id] = {}
    
    if user_id not in levels[guild_id]:
        levels[guild_id][user_id] = {'xp': 0, 'level': 0, 'messages': 0}
    
    levels[guild_id][user_id]['level'] = level
    levels[guild_id][user_id]['xp'] = xp_for_level(level)
    save_levels(levels)
    
    await interaction.response.send_message(f'✅ Уровень {member.mention} установлен на **{level}**')


# ==================== Команды настройки систем ====================

@bot.tree.command(name="verification_setup", description="Настроить систему верификации")
@app_commands.describe(
    channel="Канал с кнопкой верификации",
    verified_role="Роль для верифицированных пользователей"
)
async def verification_setup(interaction: discord.Interaction, channel: discord.TextChannel, verified_role: discord.Role):
    """Настраивает систему верификации"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    config = load_verification_config()
    guild_id = str(interaction.guild.id)
    
    config[guild_id] = {
        'verified_role_id': verified_role.id
    }
    save_verification_config(config)
    
    embed = discord.Embed(
        title='✅ Верификация',
        description='Нажмите на кнопку ниже, чтобы получить доступ к серверу.',
        color=discord.Color.green()
    )
    
    view = VerificationView()
    await channel.send(embed=embed, view=view)
    
    await interaction.response.send_message(
        f'✅ Система верификации настроена!\n**Канал:** {channel.mention}\n**Роль:** {verified_role.mention}',
        ephemeral=True
    )


@bot.tree.command(name="antispam_toggle", description="Включить/выключить анти-спам")
async def antispam_toggle(interaction: discord.Interaction):
    """Включает или выключает анти-спам"""
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message('❌ У вас нет прав на управление сервером.', ephemeral=True)
        return
    
    config = load_antispam_config()
    guild_id = str(interaction.guild.id)
    
    if guild_id not in config:
        config[guild_id] = {'enabled': True}
    else:
        config[guild_id]['enabled'] = not config[guild_id].get('enabled', False)
    
    save_antispam_config(config)
    
    status = 'включен' if config[guild_id]['enabled'] else 'выключен'
    await interaction.response.send_message(f'✅ Анти-спам {status}.')


# ==================== Утилиты ====================

@bot.tree.command(name="say", description="Отправить текст от имени бота")
@app_commands.describe(message="Текст для отправки")
async def say(interaction: discord.Interaction, message: str):
    """Отправляет сообщение от имени бота"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message('❌ У вас нет прав на управление сообщениями.', ephemeral=True)
        return
    
    await interaction.response.send_message('✅ Сообщение отправлено.', ephemeral=True)
    await interaction.channel.send(message)


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


@bot.tree.command(name="me", description="Выделяет текст курсивом")
@app_commands.describe(text="Текст для выделения")
async def me(interaction: discord.Interaction, text: str):
    """Отправляет текст курсивом"""
    await interaction.response.send_message(f'*{text}*')


@bot.tree.command(name="shrug", description="Добавляет ¯\\_(ツ)_/¯ к вашему сообщению")
@app_commands.describe(text="Текст сообщения (необязательно)")
async def shrug(interaction: discord.Interaction, text: str = ""):
    """Отправляет сообщение с шрагом"""
    shrug_emoji = r"¯\_(ツ)_/¯"
    message = f"{text} {shrug_emoji}" if text else shrug_emoji
    await interaction.response.send_message(message)


@bot.tree.command(name="gif", description="Искать анимированные картинки в интернете")
@app_commands.describe(query="Поисковый запрос")
async def gif(interaction: discord.Interaction, query: str):
    """Отправляет GIF по запросу (через Tenor API)"""
    await interaction.response.send_message(f'🔍 Поиск GIF: {query}\n(Для полной функциональности требуется Tenor API ключ)')


# ==================== Команда помощи ====================

@bot.tree.command(name="help", description="Показать список команд")
async def help_command(interaction: discord.Interaction):
    """Показывает список всех команд бота"""
    
    embeds = []
    
    # Модерация
    embed1 = discord.Embed(
        title='📋 Команды бота - Модерация',
        color=discord.Color.blue()
    )
    embed1.add_field(
        name='Модерация',
        value=(
            '`/timeout` - Выдать таймаут\n'
            '`/untimeout` - Снять таймаут\n'
            '`/ban` - Заблокировать пользователя\n'
            '`/kick` - Выгнать пользователя\n'
            '`/warn` - Выдать предупреждение\n'
            '`/unwarn` - Снять предупреждение\n'
            '`/warnings` - Показать предупреждения\n'
            '`/clear` - Очистить сообщения\n'
            '`/nick` - Изменить никнейм'
        ),
        inline=False
    )
    embeds.append(embed1)
    
    # Роли и информация
    embed2 = discord.Embed(
        title='📋 Команды бота - Роли и Информация',
        color=discord.Color.green()
    )
    embed2.add_field(
        name='Управление ролями',
        value=(
            '`/role_add` - Выдать роль\n'
            '`/role_remove` - Снять роль\n'
            '`/role_info` - Информация о роли\n'
            '`/role_create` - Создать роль\n'
            '`/autorole_add` - Добавить автороль\n'
            '`/autorole_remove` - Удалить автороль\n'
            '`/autorole_list` - Список авторолей'
        ),
        inline=False
    )
    embed2.add_field(
        name='Информация',
        value=(
            '`/serverinfo` - Информация о сервере\n'
            '`/userinfo` - Информация о пользователе\n'
            '`/avatar` - Аватар пользователя'
        ),
        inline=False
    )
    embeds.append(embed2)
    
    # Системы
    embed3 = discord.Embed(
        title='📋 Команды бота - Системы',
        color=discord.Color.purple()
    )
    embed3.add_field(
        name='Тикеты',
        value=(
            '`/setup_tickets` - Создать панель тикетов\n'
            '`/ticket_config` - Настроить тикеты\n'
            '`/ticket_stats` - Статистика тикетов\n'
            '`/ticket_close_all` - Закрыть все тикеты'
        ),
        inline=False
    )
    embed3.add_field(
        name='Фильтр слов',
        value=(
            '`/filter_add` - Добавить слово\n'
            '`/filter_remove` - Удалить слово\n'
            '`/filter_list` - Список слов\n'
            '`/filter_toggle` - Вкл/выкл фильтр'
        ),
        inline=False
    )
    embeds.append(embed3)
    
    # Уровни и розыгрыши
    embed4 = discord.Embed(
        title='📋 Команды бота - Уровни и Розыгрыши',
        color=discord.Color.gold()
    )
    embed4.add_field(
        name='Уровни',
        value=(
            '`/level` - Показать уровень\n'
            '`/leaderboard` - Таблица лидеров\n'
            '`/setlevel` - Установить уровень'
        ),
        inline=False
    )
    embed4.add_field(
        name='Розыгрыши',
        value=(
            '`/giveaway_start` - Начать розыгрыш\n'
            '`/giveaway_end` - Завершить розыгрыш\n'
            '`/giveaway_reroll` - Перевыбрать победителя'
        ),
        inline=False
    )
    embeds.append(embed4)
    
    # Настройки и утилиты
    embed5 = discord.Embed(
        title='📋 Команды бота - Настройки и Утилиты',
        color=discord.Color.orange()
    )
    embed5.add_field(
        name='Настройки',
        value=(
            '`/welcome_setup` - Настроить приветствия\n'
            '`/goodbye_setup` - Настроить прощания\n'
            '`/log_setup` - Настроить логи\n'
            '`/verification_setup` - Настроить верификацию\n'
            '`/antispam_toggle` - Вкл/выкл анти-спам\n'
            '`/reactionrole_setup` - Настроить Reaction Roles'
        ),
        inline=False
    )
    embed5.add_field(
        name='Утилиты',
        value=(
            '`/poll` - Создать опрос\n'
            '`/remind` - Создать напоминание\n'
            '`/customcmd_add` - Добавить команду\n'
            '`/customcmd_remove` - Удалить команду\n'
            '`/customcmd_list` - Список команд\n'
            '`/say` - Сообщение от бота\n'
            '`/msg` - Отправить ЛС\n'
            '`/me` - Курсив\n'
            '`/shrug` - ¯\\_(ツ)_/¯\n'
            '`/gif` - Поиск GIF'
        ),
        inline=False
    )
    embeds.append(embed5)
    
    view = PaginationView(embeds)
    await interaction.response.send_message(embed=embeds[0], view=view)


# ==================== Запуск бота ====================

if __name__ == '__main__':
    if TOKEN is None:
        print('❌ Ошибка: токен не найден. Укажите DISCORD_TOKEN в переменных окружения или файле .env')
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f'❌ Ошибка запуска бота: {e}')
