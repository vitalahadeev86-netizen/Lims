# --- ЧАСТЬ 1: МОДАЛЬНЫЕ ОКНА И ФОРМЫ ---
import asyncio
from datetime import datetime
import discord

# --- НАСТРОЙКИ ИЗ ВАШЕГО КОДА ---
YOUR_DISCORD_ID = 813289862580928544
LOG_CHANNEL_ID = 1564287632735862844
CATEGORY_ID = 1564151394242400286

ACCESS_ROLE_1_ID = 1562179700460363936
ACCESS_ROLE_2_ID = 1529899557654106232
ACCESS_ROLE_3_ID = 1564144768588587079


class DeclineReasonModal(discord.ui.Modal, title="Причина отклонения"):
    reason = discord.ui.TextInput(
        label="Укажите причину отказа",
        style=discord.TextStyle.long,
        required=True,
        max_length=400
    )

    def __init__(self, view, applicant):
        super().__init__()
        self.view = view
        self.applicant = applicant

    async def on_submit(self, inter: discord.Interaction):
        await inter.response.defer()
        dec_emb = discord.Embed(
            title="▫️ ЗАЯВКА ОТКЛОНЕНА",
            description=f"🤍 Проверка {self.applicant.mention} отклонена модератором {inter.user.mention}.\n🤍 **Причина:** {self.reason.value}",
            color=0x000000
        )
        await inter.followup.send(embed=dec_emb)

        decline_msg = (
            "### ⠀⠀⠀⠀⠀⠀⠀⠀🤍 **ВЕРИФИКАЦИЯ TIER | HATRED** 🤍\n\n"
            "🤍 **Ваша заявка на получение статуса Tier была отклонена 🤍**\n\n"
            f"◽ **Статус:** Отклонено\n"
            f"◽ **Проверил:** {inter.user.display_name}\n"
            f"◽ **Причина:** {self.reason.value}\n"
            f"◽ **Дата:** {datetime.now().strftime('%d.%m.%Y в %H:%M')}\n\n"
            "▫️ *Вы можете подать заявку заного.*"
        )
        await self.view.log_and_dm(inter, self.applicant, "▫️ ЛОГ: ОТКЛОНЕНИЕ ЗАЯВКИ",
                                   f"▫️ Отклонено (Причина: {self.reason.value})", decline_msg)


class TierModal(discord.ui.Modal, title="Заявка на Tier"):
    t1 = discord.ui.TextInput(
        label="1. Откаты с арены Спешик и Сайги", 
        placeholder="Спешик 5+мин | Сайга 5+мин | 6+ типов с начала гг",
        style=discord.TextStyle.long,
        required=True
    )
    t2 = discord.ui.TextInput(
        label="2. Откаты с MCL | ВЗЗ | ВЗМ | КАПТ | и т.д", 
        style=discord.TextStyle.long,
        required=True
    )
    t3 = discord.ui.TextInput(
        label="3. Ссылка на ЛК", 
        style=discord.TextStyle.long, 
        required=True
    )

    async def on_submit(self, inter):
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        cat = guild.get_channel(CATEGORY_ID) or inter.channel.category
        
        if cat:
            target_name = f"{inter.user.name}".lower()
            for ch in cat.text_channels:
                ch_name_lower = ch.name.lower()
                if ch_name_lower.startswith(f"тир-{target_name}") or ch_name_lower.startswith(f"рассмотрение-{target_name}"):
                    return await inter.followup.send(f"▫️ Канал уже открыт: {ch.mention}", ephemeral=True)

        r1, r2, r3 = guild.get_role(ACCESS_ROLE_1_ID), guild.get_role(ACCESS_ROLE_2_ID), guild.get_role(ACCESS_ROLE_3_ID)
        try:
            ow = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                inter.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            if r1: ow[r1] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if r2: ow[r2] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if r3: ow[r3] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            ch = await guild.create_text_channel(name=f"тир-{inter.user.name}", category=cat, overwrites=ow)
            emb = discord.Embed(title=f"🤍 Заявка на Tier от {inter.user.display_name}", color=0x000000)
            emb.add_field(name="▫️ 1. Откаты с арены Спешик 5+мин | Сайга 5+мин | 6+ типов с начала гг:", value=self.t1.value, inline=False)
            emb.add_field(name="▫️ 2. Откаты с MCL | ВЗЗ | ВЗМ | КАПТ | и т.д:", value=self.t2.value, inline=False)
            emb.add_field(name="▫️ 3. Лк:", value=self.t3.value, inline=False)
            emb.set_footer(text=f"ID: {inter.user.id} • Hatred")

            await ch.send(content=f"{inter.user.mention}", embed=emb)
            await ch.send(view=TierModerationView())
            await inter.followup.send(f"▫️ Канал Tier успешно создан: {ch.mention}", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"▫️ Ошибка: {e}", ephemeral=True)
# --- ЧАСТЬ 2: ПАНЕЛИ КНОПОК И ЛОГИКА ТИКЕТОВ ---

class TierModerationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def get_context(self, inter) -> tuple[discord.Member | None, int | None]:
        applicant = None
        async for message in inter.channel.history(limit=5, oldest_first=True):
            if message.mentions:
                applicant = message.mentions
                break
        handler_id = None
        ch_name = inter.channel.name
        if "id-" in ch_name:
            try: handler_id = int(ch_name.split("id-")[-1])
            except: pass
        return applicant, handler_id

    async def chk(self, inter, require_handler=True) -> discord.Member | None:
        user_role_ids = [role.id for role in inter.user.roles]
        allowed = [ACCESS_ROLE_1_ID, ACCESS_ROLE_2_ID, ACCESS_ROLE_3_ID]
        if not any(r_id in allowed for r_id in user_role_ids):
            await inter.response.send_message("▫️ У вас нет прав для управления панелью Tier.", ephemeral=True)
            return None
        applicant, handler_id = await self.get_context(inter)
        if not applicant:
            await inter.response.send_message("▫️ Ошибка: Не удалось определить автора заявки.", ephemeral=True)
            return None
        if require_handler and not handler_id:
            await inter.response.send_message("▫️ Сначала нажмите кнопку 'Рассмотрение'!", ephemeral=True)
            return None
        if handler_id and handler_id != inter.user.id:
            await inter.response.send_message(f"▫️ Эту заявку уже проверяет <@{handler_id}>!", ephemeral=True)
            return None
        return applicant

    async def log_and_dm(self, inter, applicant, log_title, res_text, pm_msg):
        log_ch = inter.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_emb = discord.Embed(title=log_title, color=0x000000)
            log_emb.add_field(name="🤍 Модератор:", value=inter.user.mention, inline=True)
            log_emb.add_field(name="🤍 Игрок:", value=applicant.mention, inline=True)
            log_emb.add_field(name="🤍 Решение:", value=res_text, inline=False)
            log_emb.set_footer(text=f"Дата: {datetime.now().strftime('%d.%m.%Y в %H:%M')} • Hatred")
            await log_ch.send(embed=log_emb)
        try: await applicant.send(content=pm_msg)
        except: pass

    @discord.ui.button(label="Рассмотрение", style=discord.ButtonStyle.secondary, custom_id="htrd_p:review")
    async def b_review(self, inter, b):
        applicant, handler_id = await self.get_context(inter)
        user_role_ids = [role.id for role in inter.user.roles]
        if not any(r_id in [ACCESS_ROLE_1_ID, ACCESS_ROLE_2_ID, ACCESS_ROLE_3_ID] for r_id in user_role_ids):
            return await inter.response.send_message("▫️ У вас нет прав.", ephemeral=True)
        if handler_id:
            return await inter.response.send_message("▫️ Заявка уже на рассмотрении!", ephemeral=True)
        await inter.channel.edit(name=f"рассмотрение-{inter.user.name}-id-{inter.user.id}")
        review_emb = discord.Embed(title="▫️ ЗАЯВКА НА РАССМОТРЕНИИ", description=f"🤍 Модератор {inter.user.mention} принял заявку.\n🤍 Другие модераторы заблокированы.", color=0x000000)
        await inter.response.send_message(embed=review_emb)

    async def give_tier(self, inter, name):
        applicant = await self.chk(inter)
        if not applicant: return
        role = discord.utils.get(inter.guild.roles, name=name)
        if not role: return await inter.followup.send(f"▫️ Роль `{name}` не найдена!", ephemeral=True)
        try:
            for r in ["Tier 1", "Tier 2", "Tier 3"]:
                old = discord.utils.get(inter.guild.roles, name=r)
                if old and old in applicant.roles: await applicant.remove_roles(old)
            await applicant.add_roles(role)
            ok_emb = discord.Embed(title="▫️ СТАТУС ОБНОВЛЕН", description=f"🤍 Игроку {applicant.mention} выдан статус **{name}**!", color=0x000000)
            await inter.followup.send(embed=ok_emb)
            success_msg = f"### ⠀⠀⠀⠀⠀⠀⠀⠀▫️ **ВЕРИФИКАЦИЯ TIER | HATRED** ▫️\n\n🤍 **Поздравляем! Ваша заявка успешно одобрена руководством 🤍**\n\n ▫️ **Присвоен статус:** {name}\n▫️ **Проверил:** {inter.user.display_name}\n▫️ **Дата:** {datetime.now().strftime('%d.%m.%Y в %H:%M')}\n\n▫️ *Роль выдана, покажи достойный уровень на каптах!* 🤍"
            await self.log_and_dm(inter, applicant, "▫️ ЛОГ: ВЫДАЧА TIER", f"▫️ Выдан **{name}**", success_msg)
        except discord.Forbidden: await inter.followup.send("▫️ Ошибка прав! Поставьте роль бота выше.", ephemeral=True)

    @discord.ui.button(label="Tier 1", style=discord.ButtonStyle.secondary, custom_id="htrd_p:t1")
    async def b3(self, inter, b): await inter.response.defer(); await self.give_tier(inter, "Tier 1")
    @discord.ui.button(label="Tier 2", style=discord.ButtonStyle.secondary, custom_id="htrd_p:t2")
    async def b4(self, inter, b): await inter.response.defer(); await self.give_tier(inter, "Tier 2")
    @discord.ui.button(label="Tier 3", style=discord.ButtonStyle.secondary, custom_id="htrd_p:t3")
    async def b5(self, inter, b): await inter.response.defer(); await self.give_tier(inter, "Tier 3")

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.secondary, custom_id="htrd_p:dec")
    async def b_decline(self, inter, b):
        applicant = await self.chk(inter, require_handler=True)
        if applicant: await inter.response.send_modal(DeclineReasonModal(self, applicant))

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.danger, custom_id="htrd_p:close_ticket")
    async def b_close_ticket(self, inter, b):
        applicant, handler_id = await self.get_context(inter)
        user_role_ids = [role.id for role in inter.user.roles]
        if not any(r_id in [ACCESS_ROLE_1_ID, ACCESS_ROLE_2_ID, ACCESS_ROLE_3_ID] for r_id in user_role_ids):
            return await inter.response.send_message("▫️ Нет прав.", ephemeral=True)
        if not handler_id: return await inter.response.send_message("▫️ Сначала нажмите 'Рассмотрение'!", ephemeral=True)
        if handler_id != inter.user.id: return await inter.response.send_message(f"▫️ Закрыть тикет может только: <@{handler_id}>!", ephemeral=True)
        await inter.response.send_message("▫️ Удаление канала через 5 секунд...")
        await asyncio.sleep(5)
        try: await inter.channel.delete()
        except: pass


class TierView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @discord.ui.button(label="Подать на Tier", style=discord.ButtonStyle.secondary, custom_id="btn_app_v10")
    async def b(self, inter, btn):
        await inter.response.send_modal(TierModal())
# --- ЧАСТЬ 3: ИНИЦИАЛИЗАЦИЯ И ЗАПУСК БОТА ---
import os
import discord
from discord.ext import commands

YOUR_DISCORD_ID = 813289862580928544

intents = discord.Intents.default()
intents.message_content = intents.members = intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    bot.add_view(TierView())
    bot.add_view(TierModerationView())
    print(f'Бот {bot.user.name} запущен. Доступ к !тир только у ID: {YOUR_DISCORD_ID}')

@bot.command()
async def тир(ctx):
    if ctx.author.id != YOUR_DISCORD_ID:
        return
    description_text = "### ⠀⠀⠀⠀⠀⠀🤍 **ПОЛУЧЕНИЕ TIER | HATRED** 🤍\n" \
                       "### ⠀⠀⠀⠀ ⠀⠀⠀⠀⠀⠀⠀ **🤍⭣ ВАЖНО ⭣🤍**\n" \
                       "### 🤍⭣ **Ознакомьтесь с правилами подачи заявки** ⭣🤍\n" \
                       "### ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[🤍 Правила подачи 🤍](https://discord.com)"
    embed = discord.Embed(description=description_text, color=0x000000)
    embed.set_footer(text="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀By Diego ")
    await ctx.send(embed=embed, view=TierView())
    try: await ctx.message.delete()
    except: pass

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
