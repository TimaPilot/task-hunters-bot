import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import Interaction, Embed
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import asyncio
import os
import datetime
import psycopg2
import urllib.parse as urlparse
from db_logger import (
    save_order_to_db,
    update_order_status_by_id,
    get_order_by_id,
    get_orders_by_user,
    init_db,
    mark_order_accepted,
    mark_order_collected,
    delete_orders_by_customer,
    delete_orders_by_status
)
import traceback
OWNER_ID = 386329540353458186

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

 # 🌍 Reverse mapping: для зручності визначення ключа ресурсу
resource_reverse = {
"🪨 Камінь": "stone",
"🌲 Дерево": "wood",          
"🐟 Риба": "fish",          
"🍄 Гриби": "mushrooms",
"🧴 Миючі засоби": "cleaner"            
}

# ⏱️ Орієнтовний час виконання для кожного ресурсу
estimated_times = {
"stone": "30–60 хв",
"wood": "15–20 хв",
"fish": "25–35 хв",
"mushrooms": "30 хв",
"cleaner": "20–25 хв"
}


@bot.event
async def on_ready():
    await init_db()
    print(f"✅ Logged in as {bot.user}")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Slash-команди синхронізовано: {len(synced)}")
    except Exception as e:
        print("❌ Помилка при синхронізації слеш-команд:", e)

    bot.add_view(ResourceButtonsView())
    bot.add_view(CabinetButtonView())
    bot.add_view(ReferralView())

# ==============================================
#           [Блок: Slash команда]
# ==============================================
@bot.tree.command(name="ping", description="Перевірка чи бот живий")
async def ping(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: 
        await interaction.response.send_message("⛔ Ця команда лише для капітана!", ephemeral=True)
        return
    await interaction.response.send_message("🏓 Pong! Бот активний.", ephemeral=True)

# ==============================================
#           [Блок: Привітання новеньких]
# ==============================================
@bot.event
async def on_member_join(member):
    # 4️⃣ Привітання 
    channel = bot.get_channel(1356270026688041171)  # ID твого каналу
    image_path = os.path.join(os.path.dirname(__file__), "images", "Hello.png")
    file = discord.File(image_path, filename="Hello.png")

    embed = discord.Embed(
        title=f"👋 Вітаємо, {member.name}!",
        description="Інвентар ще порожній, але мисливці вже в дорозі 🎯",
        color=0x8B4513
    )
    embed.set_image(url="attachment://Hello.png")
    await channel.send(content=member.mention, embed=embed, file=file)
    role = discord.utils.get(member.guild.roles, name="Замовник 💼")
    if role:
        # Видаємо роль учаснику
        await member.add_roles(role)
        print(f"Роль '{role.name}' видано користувачу {member.name}")
    else:
        print("Роль 'Замовник 💼' не знайдена!")

    invites = await member.guild.invites()
    used_invite = max(invites, key=lambda i: i.uses)

    dsn = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()

    # Перевіряємо, чи вже записаний цей invited_id
    cursor.execute("SELECT * FROM referrals WHERE invited_id = %s", (used_invite.code,))
    referral = cursor.fetchone()

    if referral:
        # Оновлюємо запис — підтверджуємо реферал
        cursor.execute("""
            UPDATE referrals
            SET confirmed = TRUE
            WHERE invited_id = %s
        """, (used_invite.code,))
        conn.commit()
        print(f"✅ Реферал підтверджено для {member.name}")
    else:
        print(f"⚠️ Інвайт {used_invite.code} не знайдено в базі")

    cursor.close()
    conn.close()
# =======================================================================
#           [Блок: Очищення чату (крім закріплених повід.)]
# =======================================================================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx):
    # Очищаємо весь чат, але залишаємо закріплені повідомлення
    await ctx.channel.purge(check=lambda msg: not msg.pinned)
    await ctx.send("🧹 Чат очищено! Закріплені повідомлення залишились.", delete_after=5)

# ==============================================
#           [Блок: Очищення бази даних]
# ==============================================
@bot.command(name="очистити_замовлення_користувача")
async def clear_orders_by_user(ctx, member: discord.Member):
    if ctx.author.id != 386329540353458186:
        await ctx.send("❌ У вас немає прав на виконання цієї команди.")
        return

    await delete_orders_by_customer(member.id)
    await ctx.send(f"🧹 Видалено всі замовлення користувача {member.mention}.")

@bot.command(name="очистити_замовлення_id")
async def clear_orders_by_customer_id(ctx, customer_id: int):
    if ctx.author.id != 386329540353458186:
        await ctx.send("❌ У вас немає прав на виконання цієї команди.")
        return

    await delete_orders_by_customer(customer_id)
    await ctx.send(f"🧹 Усі замовлення користувача з ID `{customer_id}` видалено.")

@bot.command(name="очистити_за_статусом")
async def clear_orders_by_status(ctx, *, status: str):
    if ctx.author.id != 386329540353458186:
        await ctx.send("❌ У вас немає прав на виконання цієї команди.")
        return

    await delete_orders_by_status(status)
    await ctx.send(f"🧹 Видалено всі замовлення зі статусом: **{status}**.")

# ==============================================
#           [Блок: Особистий кабінет]
# ==============================================
@bot.command(name="панель")
async def show_panel(ctx):
    await ctx.send("Натисни кнопку нижче, щоб відкрити свій особистий кабінет:", view=CabinetButtonView())

# ==============================================
#           [Блок: Команда для замовлення]
# ==============================================
@bot.command()
async def start(ctx):
    class OrderButtonView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(Button(label="Замовити послугу", style=discord.ButtonStyle.primary, custom_id="order_service"))

    await ctx.send("Натисни кнопку нижче, щоб зробити замовлення:", view=OrderButtonView())

# ==============================================
#           [Блок: Особистий кабінет]
# ==============================================
def get_user_order_stats(customer_id: int):
    conn = psycopg2.connect(
        dbname="railway",
        user="postgres",
        password="FJKgjkxdKaPTNXfxSgbGKpDbVILNojHs",
        host="postgres.railway.internal",
        port="5432"
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM orders WHERE customer_id = %s
    """, (str(customer_id),))
    total_orders = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM orders WHERE customer_id = %s AND status = 'Виконано'
    """, (str(customer_id),))
    completed_orders = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return total_orders, completed_orders

def get_order_price(order, cursor):
    resource = order["details"]
    finished_at = order["finished_at"]
    discount = order.get("discount_percent") or 0  # якщо NULL — знижки нема

    # Отримати найновішу ціну, яка діяла на момент замовлення
    cursor.execute("""
        SELECT price FROM resource_prices
        WHERE resource = %s AND effective_from <= %s
        ORDER BY effective_from DESC
        LIMIT 1
    """, (resource, finished_at))
    result = cursor.fetchone()

    if not result:
        print(f"⚠️ Ціна не знайдена для {resource} на {finished_at}")
        return 0

    base_price = result[0]
    final_price = int(base_price * (1 - discount / 100))

    return final_price

def get_total_spent(customer_id: int):
    dsn = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(dsn)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM orders WHERE customer_id = %s AND status = 'Виконано'
    """, (str(customer_id),))

    # Отримаємо список замовлень як словники
    columns = [desc[0] for desc in cursor.description]
    orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

    total_spent = sum(get_order_price(order, cursor) for order in orders)

    cursor.close()
    conn.close()

    return total_spent

# ===============================================================
#           [Class: Вигляд кнопки особистий кабінет]
# ===============================================================
class CabinetButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📂 Зайти в особистий кабінет", style=discord.ButtonStyle.primary)
    async def open_cabinet(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        total_orders, completed_count = get_user_order_stats(user_id)
        total_spent = get_total_spent(user_id)

        embed = discord.Embed(title="🧾 Особистий кабінет", color=0x00ffcc)
        embed.add_field(name="Ім’я", value=f"<@{user_id}>", inline=False)
        embed.add_field(name="📦 Замовлень (всього)", value=str(total_orders), inline=True)
        embed.add_field(name="✅ Виконано", value=str(completed_count), inline=True)
        embed.add_field(name="💰 Витрачено", value=f"${total_spent}", inline=True)
        embed.add_field(name="🎟️ Знижка", value="0%", inline=True)
        embed.add_field(name="🎁 Безкоштовні замовлення", value="0", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ...............................................................
#           [Блок: Вигляд кнопки детальна статистика]
# ...............................................................
    @discord.ui.button(label="🔗 Реферальна система", style=discord.ButtonStyle.secondary)
    async def referral_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🧩 Обери дію нижче щодо твоєї реферальної системи:",
            view=ReferralView(),
            ephemeral=True
        )


# ...............................................................
#           [Блок: Вигляд кнопки детальна статистика]
# ...............................................................
    @discord.ui.button(label="📊 Детальна статистика", style=discord.ButtonStyle.secondary)
    async def detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        import os
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()

        dsn = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()

        user_id = str(interaction.user.id)

        cursor.execute("""
            SELECT details FROM orders
            WHERE customer_id = %s AND status = 'Виконано'
        """, (user_id,))

        rows = cursor.fetchall()
        resource_counts = {}

        for row in rows:
            resource = row[0]
            resource_counts[resource] = resource_counts.get(resource, 0) + 1

        # Формуємо текст
        if not resource_counts:
            description = "😔 У вас ще немає виконаних замовлень."
        else:
            description = f"Привіт, {interaction.user.mention}! Ось твоя особиста аналітика виконаних замовлень:\n\n"
            description += "\n".join([
                f"{emoji} {name}: {count} замовлення(нь)"
                for name, count in resource_counts.items()
                for emoji in [next((e for e, n in resource_reverse.items() if n == name), "")]
            ])

            # Знаходимо найпопулярніший ресурс
            top_resource = max(resource_counts.items(), key=lambda x: x[1], default=(None, 0))
            top_name, top_count = top_resource
            top_emoji = next((e for e, n in resource_reverse.items() if n == top_name), "")

            if top_name:
                description += f"\n\n🔥 Найчастіше ти замовляв: {top_emoji} {top_name} ({top_count} рази)"

            description += "\n\n🔁 Якщо будеш виконувати більше замовлень — тут з’явиться ще більше інформації!"

        embed = discord.Embed(title="📊 Детальна статистика", description=description, color=0x00ffcc)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        cursor.close()
        conn.close()


# ===============================================================
#           [Class: Вигляд кнопки реферальна система]
# ===============================================================
# ========================= [Referral View] =========================

class ReferralView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.custom_id = "get_referral_link"

    @discord.ui.button(
        label="📎 Отримати посилання",
        style=discord.ButtonStyle.primary
    )
    async def get_referral_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        # Підключення до БД
        dsn = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor()

        # Перевірка: чи є запис з цим inviter_id
        cursor.execute("SELECT invited_id FROM referrals WHERE inviter_id = %s", (user_id,))
        existing = cursor.fetchone()

        if existing:
            # Якщо є — беремо наявного invited_id
            invited_id = existing[0]
        else:
            # Якщо нема — створюємо інвайт
            channel = interaction.guild.system_channel or interaction.channel
            invite = await channel.create_invite(
                reason=f"Інвайт для {interaction.user.name}",
                max_uses=0,
                unique=True
            )
            invite_code = invite.code  # тільки для відображення
            invited_id = 0  # тимчасове значення, бо ще не відомо, хто приєднається

            # Зберігаємо лише inviter_id (user_id) — invited_id буде оновлений пізніше
            cursor.execute("""
                INSERT INTO referrals (inviter_id, invited_id, confirmed)
                VALUES (%s, %s, FALSE)
            """, (user_id, invited_id))
            conn.commit()

        referral_link = f"https://discord.gg/{invite.code}"

        await interaction.response.send_message(
            f"📎 Ось твоє індивідуальне реферальне посилання:\n`{referral_link}`\n"
            "Скопіюй його та передай другу. Після його першого замовлення ти отримаєш бонус 🎁",
            ephemeral=True
        )

        cursor.close()
        conn.close()


class ResourceButtonsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="🪨 Камінь", style=discord.ButtonStyle.secondary, custom_id="stone"))
        self.add_item(Button(label="🌲 Дерево", style=discord.ButtonStyle.secondary, custom_id="wood"))
        self.add_item(Button(label="🐟 Риба", style=discord.ButtonStyle.secondary, custom_id="fish"))
        self.add_item(Button(label="🍄 Гриби", style=discord.ButtonStyle.secondary, custom_id="mushrooms"))
        self.add_item(Button(label="🧴 Миючі засоби", style=discord.ButtonStyle.secondary, custom_id="cleaner"))

class OrderProgressView(View):
    def __init__(self, customer: discord.User, resource: str, order_id: int, stage: str = "new"):
        super().__init__(timeout=None)
        self.customer = customer
        self.resource = resource
        self.order_id = order_id

        if stage == "new":
            self.add_item(Button(label="✅ Прийняти замовлення", style=discord.ButtonStyle.success, custom_id=f"accept_order_{order_id}"))

        elif stage == "accepted":
            self.add_item(Button(label="📦 Зібрано", style=discord.ButtonStyle.primary, custom_id=f"ready_{order_id}"))

        elif stage == "ready":
            self.add_item(Button(label="✅ Завершено", style=discord.ButtonStyle.secondary, custom_id=f"finish_{order_id}"))

# ==============================================
#           [Блок: on_interaction]
# ==============================================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        user = interaction.user
        cid = interaction.data["custom_id"]

        if cid == "order_service":
            await interaction.response.send_message("🛒 Вибери ресурс для замовлення:", view=ResourceButtonsView(), ephemeral=False)

        elif cid in ["stone", "wood", "fish", "mushrooms", "cleaner"]:
            resource_names = {
                "stone": "🪨 Камінь",
                "wood": "🌲 Дерево",
                "fish": "🐟 Риба",
                "mushrooms": "🍄 Гриби",
                "cleaner": "🧴 Миючі засоби"
            }
            selected = resource_names[cid]

            order_data = {
                "customer": user.name,
                "customer_id": user.id,
                "details": selected,
                "hunter": None,
                "status": "Очікує"
            }

            order_id = await save_order_to_db(order_data)
            await interaction.message.delete()
            channel = discord.utils.get(interaction.guild.text_channels, name="✅-виконання-замовлень")
            if channel:
                await channel.send(
                    f"🆕 Надійшло нове замовлення на **{selected}** від {user.mention}",
                    view=OrderProgressView(user, cid, order_id, stage="new")
                )
            await interaction.response.send_message(
                f"📨 Ваш запит на **{selected}** успішно зареєстровано. Очікуйте підтвердження.", ephemeral=True
            )

        elif cid.startswith("accept_order_"):
            order_id = int(cid.replace("accept_order_", ""))
            order = await get_order_by_id(order_id)
            resource = order["details"]
            hunter = user

            try:
                customer = interaction.message.mentions[0]
            except IndexError:
                await interaction.response.send_message("❌ Не вдалося знайти замовника.", ephemeral=True)
                return

            await interaction.response.edit_message(
                content=f"🔔 Замовлення на **{resource}** прийнято мисливцем {hunter.mention}!",
                view=OrderProgressView(customer, cid.split("_")[2], order_id, stage="accepted")
            )

            await mark_order_accepted(order_id, hunter.name)
            notify_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if notify_channel:
                resource_key = resource_reverse.get(resource, "unknown")
                eta = estimated_times.get(resource_key, "20–30 хв")

                await notify_channel.send(
                    f"{customer.mention}, Ваше замовлення на **{resource}** прийняв {hunter.mention}! 🕒 Орієнтовний час виконання — {eta}!"
                )


        elif cid.startswith("ready_"):
            order_id = int(cid.replace("ready_", ""))
            order = await get_order_by_id(order_id)
            customer_id = order["customer_id"]
            customer = await interaction.guild.fetch_member(customer_id)
            resource = order["details"]
            resource_key = resource_reverse.get(resource, "unknown")

            await mark_order_collected(order_id)

            notify_channel = discord.utils.get(
                interaction.guild.text_channels,
                name="📝-зробити-замовлення"
            )

            # 📨 Надсилаємо повідомлення замовнику
            if notify_channel:
                if "камінь" in resource.lower():
                    await notify_channel.send(
                        f"{customer.mention}, 🪨 Ваш **камінь** готовий! Мисливець очікує Вас на кар'єрі.\n💡 Звільніть інвентар заздалегідь — буде важко!"
                    )
                else:
                    await notify_channel.send(
                        f"{customer.mention}, 📦 Ваш **{resource}** вже в рюкзаку мисливця! 📍З Вами зараз зв’яжуться для узгодження місця зустрічі"
                    )

            # 🛠️ Оновлюємо повідомлення з кнопкою
            await interaction.response.edit_message(
                content="📦 Замовлення зібране! Замовнику надіслано повідомлення.",
                view=OrderProgressView(customer, resource_key, order_id, stage="ready")
            )


        elif cid.startswith("finish_"):
            if interaction.user.bot:
                return

            order_id = int(cid.replace("finish_", ""))
            order = await get_order_by_id(order_id)
            customer_id = order["customer_id"]
            customer = await interaction.guild.fetch_member(customer_id)

            # Оновлюємо статус
            await update_order_status_by_id(order_id, "Виконано", hunter_name=user.name)

            # Повідомлення в тому ж повідомленні
            await interaction.response.edit_message(
                content="✅ Замовлення виконано.",
                view=None
            )

            # Надішлемо сповіщення в загальний канал
            notify_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if notify_channel:
                await notify_channel.send(
                    f"{customer.mention}, Ваше замовлення було позначено як **виконане**. Дякуємо, що скористались нашими послугами! 🤎"
                )
                await notify_channel.send(
                    "💬 Будемо раді бачити Ваш відгук в каналі <#1356362829099303160>!"
                )

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
