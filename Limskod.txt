import asyncio
from datetime import datetime
import discord
from discord.ext import commands

# --- НАСТРОЙКИ БОТА ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # Сюда вставь токен твоего бота в кавычках
YOUR_DISCORD_ID = 813289862580928544
CATEGORY_TIER_ID = 1564151394242400286
LOG_CHANNEL_ID = 1564287632735862844

# --- 3 РОЛИ ДОСТУПА ---
ACCESS_ROLE_1_ID = 1562179700460363936
ACCESS_ROLE_2_ID = 1529899557654106232
ACCESS_ROLE_3_ID = 1564144768588587079

intents = discord.Intents.default()
intents.message_content = intents.members = intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)


class TierRejectModal(discord.ui.Modal, title="Отказ в выдаче Tier"):
    reason = discord.ui.TextInput(label="Причина отказа:", style=discord.TextStyle.long, required=True)

    def __init__(self, applicant: discord.Member = None):
        super().__init__()
        self.applicant = applicant

    async def on_submit(self, inter):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild

        # Защита: если объект игрока потерялся, пробуем найти его по владельцу канала
        if not self.applicant:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_create, limit=5):
                if entry.target and entry.target.id == inter.channel.id:
                    self.applicant = entry.user
                    break

        # Если лог пустой, ищем по упоминаниям в первом сообщении канала
        if not self.applicant and inter.channel.topic:
            try:
                uid = int(inter.channel.topic)
                self.applicant = guild.get_member(uid)
            except:
                pass

        # Финальная заглушка на случай, если тип совсем вышел с сервера
        app_mention = self.applicant.mention if self.applicant else "@Участник (покинул сервер)"
        app_name = self.applicant.name if self.applicant else "Неизвестно"
        app_avatar = self.applicant.display_avatar.url if self.applicant else None

        await inter.channel.send(embed=discord.Embed(
            title="❌ Заявка на Tier отклонена",
            description=f"**Игрок:** {app_mention}\n**Проверил:** {inter.user.mention}\n**Причина:** {self.reason.value}",
            color=0xFF0000
        ))

        log_ch = guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_emb = discord.Embed(
                title="📝 Лог Действий: Отказ в Tier",
                description=f"**Администратор:** {inter.user.mention}\n**Игрок:** {app_mention} ({app_name})\n**Причина:** {self.reason.value}",
                color=0xFF0000
            )
            if app_avatar: log_emb.set_thumbnail(url=app_avatar)
            await log_ch.send(embed=log_emb)

        if self.applicant:
            try:
                await self.applicant.send(embed=discord.Embed(
                    title="❌ Ваша заявка на Tier была отклонена",
                    description=f"На сервере **HATRED** вам отказали в Tier.\n**Причина:** {self.reason.value}",
                    color=0xFF0000
                ))
            except:
                pass

        await inter.channel.send("🛑 *Канал автоматически удалится через 10 секунд...*")
        await asyncio.sleep(10)
        await inter.channel.delete()


class TierModerationView(discord.ui.View):
    def __init__(self, applicant: discord.Member = None):
        super().__init__(timeout=None)
        self.applicant = applicant
        self.moderator = None

    async def chk_and_lock(self, inter) -> bool:
        if not inter.user.guild_permissions.administrator:
            await inter.response.send_message("❌ Только Администратор сервера может проверять заявки!", ephemeral=True)
            return False
        if self.moderator and self.moderator.id != inter.user.id:
            await inter.response.send_message(f"❌ Эту заявку уже рассматривает {self.moderator.mention}!",
                                              ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Рассмотрение", style=discord.ButtonStyle.blurple, custom_id="t_review_b_new")
    async def b2(self, inter, b):
        if not await self.chk_and_lock(inter): return
        if self.moderator: return await inter.response.send_message("❌ Заявка уже на рассмотрении!", ephemeral=True)
        self.moderator = inter.user
        b.disabled = True
        b.style = discord.ButtonStyle.gray
        await inter.response.edit_message(view=self)
        await inter.channel.send(
            embed=discord.Embed(description=f"👀 Администратор {inter.user.mention} взял заявку на рассмотрение.",
                                color=0xF1C40F))

    async def assign_tier_role(self, inter, role_name):
        if not await self.chk_and_lock(inter): return
        if not self.moderator: return await inter.response.send_message("❌ Сначала нажмите кнопку «Рассмотрение»!",
                                                                        ephemeral=True)
        guild = inter.guild

        # Если при восстановлении View applicant равен None, пытаемся вытащить его из описания канала
        if not self.applicant and inter.channel.topic:
            try:
                self.applicant = guild.get_member(int(inter.channel.topic))
            except:
                pass

        if not self.applicant:
            return await inter.response.send_message("❌ Ошибка: Игрок не найден на сервере или покинул его.",
                                                     ephemeral=True)

        role = discord.utils.get(guild.roles, name=role_name)
        if not role: return await inter.response.send_message(f"❌ Ошибка: Роль `{role_name}` не найдена!",
                                                              ephemeral=True)
        try:
            for r_rem in [discord.utils.get(guild.roles, name=n) for n in ["Tier 1", "Tier 2", "Tier 3"]]:
                if r_rem and r_rem in self.applicant.roles: await self.applicant.remove_roles(r_rem)
            await self.applicant.add_roles(role)
            await inter.response.send_message(embed=discord.Embed(title="🥇 Одобрено: Роль выдана!",
                                                                  description=f"Пользователю {self.applicant.mention} присвоен статус **{role_name}**!",
                                                                  color=0x2ECC71))
            log_ch = guild.get_channel(LOG_CHANNEL_ID)
            if log_ch:
                await log_ch.send(embed=discord.Embed(title="📝 Лог: Выдача Tier",
                                                      description=f"**Модератор:** {inter.user.mention}\n**Игрок:** {self.applicant.mention}\n**Статус:** {role_name}",
                                                      color=0x2ECC71))
            try:
                await self.applicant.send(embed=discord.Embed(title="🎉 Поздравляем!",
                                                              description=f"Вам выдана роль **{role_name}** на сервере HATRED!",
                                                              color=0x2ECC71))
            except:
                pass
            self.stop()
            await inter.channel.send("🛑 *Канал автоматически удалится через 10 секунд...*")
            await asyncio.sleep(10)
            await inter.channel.delete()
        except discord.Forbidden:
            await inter.response.send_message(
                "❌ У бота нет прав! Поднимите его роль выше остальных ролей в настройках.", ephemeral=True)

    @discord.ui.button(label="Tier 1", style=discord.ButtonStyle.green, custom_id="t_t1_b_new")
    async def b3(self, inter, b):
        await self.assign_tier_role(inter, "Tier 1")

    @discord.ui.button(label="Tier 2", style=discord.ButtonStyle.green, custom_id="t_t2_b_new")
    async def b4(self, inter, b):
        await self.assign_tier_role(inter, "Tier 2")

    @discord.ui.button(label="Tier 3", style=discord.ButtonStyle.green, custom_id="t_t3_b_new")
    async def b5(self, inter, b):
        await self.assign_tier_role(inter, "Tier 3")

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.red, custom_id="t_reject_b_new")
    async def b6(self, inter, b):
        if not await self.chk_and_lock(inter): return
        if not self.moderator: return await inter.response.send_message("❌ Сначала нажмите кнопку «Рассмотрение»!",
                                                                        ephemeral=True)

        # Передаем актуального игрока в модалку отказа
        if not self.applicant and inter.channel.topic:
            try:
                self.applicant = inter.guild.get_member(int(inter.channel.topic))
            except:
                pass
        await inter.response.send_modal(TierRejectModal(self.applicant))


class TierModal(discord.ui.Modal, title="Заявка на Tier"):
    t1 = discord.ui.TextInput(label="1. Откаты с арены Спешик | Сайга 10+мин", style=discord.TextStyle.long,
                              required=True)
    t2 = discord.ui.TextInput(label="2. Откаты с MCL | ВЗЗ | ВЗМ | КАПТ | и т.д", style=discord.TextStyle.long,
                              required=True)
    t3 = discord.ui.TextInput (label="3. Сыллка на ЛК", style=discord.TextStyle.long,
                              required=True)

    async def on_submit(self, inter):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        cat = discord.utils.get(guild.categories, id=int(CATEGORY_TIER_ID))
        if not cat: return await inter.followup.send("❌ Ошибка: Категория не найдена.", ephemeral=True)

        r1, r2, r3 = guild.get_role(int(ACCESS_ROLE_1_ID)), guild.get_role(int(ACCESS_ROLE_2_ID)), guild.get_role(
            int(ACCESS_ROLE_3_ID))
        try:
            ow = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}

            # Принудительно убираем роли создателя тикета, чтобы они не наследовались
            for member_role in inter.user.roles:
                if member_role != guild.default_role:
                    ow[member_role] = discord.PermissionOverwrite(read_messages=False, send_messages=False)

            ow[inter.user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            ow[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            if r1: ow[r1] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if r2: ow[r2] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if r3: ow[r3] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            # Записываем ID игрока в Описание Канала (topic), чтобы бот никогда его не потерял!
            ch = await guild.create_text_channel(name=f"тир-{inter.user.name}", category=cat, overwrites=ow,
                                                 topic=str(inter.user.id))
        except discord.Forbidden:
            return await inter.followup.send("❌ Ошибка: У бота нет прав Администратора на создание каналов!",
                                             ephemeral=True)

        emb = discord.Embed(title=f"🥇 Заявка на Tier от {inter.user.display_name}", color=0x111111)
        emb.add_field(name="1. Арена:", value=self.t1.value, inline=False)
        emb.add_field(name="2. Откаты MCL/КАПТ:", value=self.t2.value, inline=False)
        emb.add_field(name="3. Лк", value=self.t3.value, inline=False)

        await ch.send(content=f"{inter.user.mention}", embed=emb, view=TierModerationView(inter.user))
        await inter.followup.send(f"✅ Канал Tier успешно создан: {ch.mention}", ephemeral=True)


class TierView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать на Tier", style=discord.ButtonStyle.gray, custom_id="apply_btn_t")
    async def b(self, inter, btn):
        cat = discord.utils.get(inter.guild.categories, id=int(CATEGORY_TIER_ID))
        if cat:
            for ch in cat.text_channels:
                if ch.name == f"тир-{inter.user.name}".lower(): return await inter.response.send_message(
                    f"❌ Канал уже открыт: {ch.mention}", ephemeral=True)
        await inter.response.send_modal(TierModal())


@bot.event
async def on_ready():
    bot.add_view(TierView())
    bot.add_view(TierModerationView(None))
    print(f'Бот {bot.user.name} успешно запущен!')


@bot.command()
async def тир(ctx):
    if ctx.author.id != YOUR_DISCORD_ID: return

    description_text = (
        "### ⠀⠀⠀⠀⠀⠀🔹 **ПОЛУЧЕНИЕ TIER | HATRED**🔹 \n"
        "### ⠀⠀⠀⠀ ⠀⠀⠀⠀⠀⠀⠀ **🔹⭣ВАЖНО⭣🔹**\n"
        "### 🔹⭣**Ознакомьтесь с правилами подачи заявки**⭣🔹\n"
        "### ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[🔹Правила подачи🔹](https://discord.com)"
    )

    embed = discord.Embed(description=description_text, color=0x000000)
    embed.set_footer(text="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀By Diego")

    await ctx.send(embed=embed, view=TierView())
    try:
        await ctx.message.delete()
    except:
        pass


        bot.run(os.getenv('DISCORD_TOKEN'))
