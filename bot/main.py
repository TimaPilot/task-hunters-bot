import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import Interaction, Embed
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import asyncio
import os
import datetime
import psycopg2
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

# =========================================================
#                  МАПИ І ЧАСИ ДЛЯ РЕСУРСІВ
# =========================================================
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

invite_cache = {}

# =========================================================
#               БЛОК: ПОДІЇ on_ready та on_member_join
# =========================================================
# on_ready — ініціалізація бота та відправка панелі
# on_member_join — видача ролі і привітання новачка
@bot.event
async def on_ready():
    await init_db()
    print(f"✅ Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"📦 Slash-команди синхронізовано: {len(synced)}")
    except Exception as e:
        print("❌ Помилка при синхронізації слеш-команд:", e)

    bot.add_view(ResourceButtonsView())
    bot.add_view(CabinetButtonView())
    
    # 🧩 Перевірка і надсилання панелі, якщо ще немає
    channel = bot.get_channel(1361872158435053759)  # 📂-особистий-кабінет
    if channel:
        async for msg in channel.history(limit=10):
            if msg.author == bot.user and "особистий кабінет" in msg.content:
                print("ℹ️ Панель вже є — пропускаємо.")
                break
        else:
            await channel.send("Натисни кнопку нижче, щоб відкрити свій особистий кабінет:", view=CabinetButtonView())
            print("📌 Панель відправлено автоматично.")


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


# =======================================================================
#           [Блок: Очищення вітання з @TH Dev Tester]
# =======================================================================
@bot.command(name="clear_tester")
@commands.has_permissions(administrator=True)
async def clear_tester_messages(ctx):
    target_id = 1356372930476507367  # ID користувача @TH Dev Tester
    deleted = 0

    async for msg in ctx.channel.history(limit=300):
        if msg.author == bot.user and str(target_id) in msg.content:
            try:
                await msg.delete()
                deleted += 1
            except:
                pass

    await ctx.send(f"🧹 Видалено {deleted} повідомлень, повʼязаних із @TH Dev Tester.", delete_after=5)


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
#           [Блок: Додавання реферала]
# ==============================================
@bot.command(name="додати_реферала")
@commands.is_owner()
async def add_referral(ctx, inviter_id: int, invited_id: int):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO referrals (inviter_id, invited_id)
            VALUES (%s, %s)
            ON CONFLICT (invited_id) DO NOTHING
        """, (inviter_id, invited_id))
        conn.commit()
        cursor.close()
        conn.close()
        await ctx.send(f"✅ Реферал доданий: `{inviter_id}` → `{invited_id}`.")
    except Exception as e:
        print("❌ Помилка при додаванні реферала:", e)
        await ctx.send("❌ Помилка при додаванні реферала.")

# =======================================================
#           [Блок: Статистика рефералів (Адмін)]
# =======================================================
@bot.command(name="рефстатистика")
@commands.is_owner()
async def referral_stats(ctx):
    """Показує кількість рефералів у кожного"""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT inviter_id,
                   COUNT(*) as total,
                   COUNT(*) FILTER (WHERE confirmed = TRUE) as confirmed
            FROM referrals
            GROUP BY inviter_id
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            await ctx.send("📉 Немає жодного реферала в системі.")
            return

        msg = "**📊 Статистика рефералів:**\n\n"
        for inviter_id, total, confirmed in rows:
            msg += f"👤 <@{inviter_id}> — **{total}** всього / ✅ **{confirmed}** підтверджено\n"

        await ctx.send(msg)
    except Exception as e:
        print("❌ Помилка статистики:", e)
        await ctx.send("❌ Не вдалося отримати статистику.")

@bot.command(name="рефдетальна")
@commands.is_owner()
async def detailed_referral_stats(ctx):
    """Показує, кого конкретно запросив кожен"""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT inviter_id, invited_id, confirmed FROM referrals
            ORDER BY inviter_id
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            await ctx.send("📉 Немає жодного реферала.")
            return

        ref_map = {}
        for inviter_id, invited_id, confirmed in rows:
            ref_map.setdefault(inviter_id, []).append((invited_id, confirmed))

        msg = "**📋 Детальна реферальна статистика:**\n\n"
        for inviter_id, invited_list in ref_map.items():
            mentions = [
                f"{'✅' if confirmed else '❌'} <@{invited_id}>"
                for invited_id, confirmed in invited_list
            ]
            msg += f"<@{inviter_id}>:\n" + "\n".join(mentions) + "\n\n"

        await ctx.send(msg[:2000])  # Discord ліміт
    except Exception as e:
        print("❌ Помилка при detailed_referral_stats:", e)
        await ctx.send("❌ Не вдалося отримати детальну статистику.")


# ===========================================
#           [Блок: Оновити бонуси]
# ===========================================
@bot.command(name="оновити_бонуси")
@commands.has_permissions(administrator=True)
async def update_bonuses(ctx):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        # Витягуємо всі непідтверджені реферали
        cursor.execute("""
            SELECT id, inviter_id, invited_id
            FROM referrals
            WHERE confirmed = false
        """)
        referrals = cursor.fetchall()

        updated_count = 0

        for ref_id, inviter_id, invited_id in referrals:
            # Перевірка, чи реферал зробив хоч одне замовлення
            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE customer_id = %s AND status = 'Виконано'
            """, (invited_id,))
            order_count = cursor.fetchone()[0]

            if order_count > 0:
                # Позначаємо реферал як підтверджений
                cursor.execute("""
                    UPDATE referrals SET confirmed = true WHERE id = %s
                """, (ref_id,))

                # Додаємо бонус inviter'у (перевірка наявності рядка опускається, бо ми це вже робили раніше)
                cursor.execute("""
                    UPDATE user_bonuses SET permanent_discount = 10
                    WHERE user_id = %s
                """, (inviter_id,))
                updated_count += 1

        conn.commit()
        await ctx.send(f"✅ Оновлено {updated_count} бонус(ів) для підтверджених рефералів.")

        cursor.close()
        conn.close()

    except Exception as e:
        await ctx.send(f"❌ Помилка при оновленні бонусів: {e}")

# =================================================================
#           [Блок: Подивитись особистий кабінет інших гравців]
# =================================================================
@bot.command(name="кабінет_за_id")
@commands.is_owner()
async def cabinet_by_id(ctx, user_id: int):
    total_orders, completed_count = get_user_order_stats(user_id)
    total_spent = get_total_spent(user_id)

    bonus_row = None
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT permanent_discount, used_discount_10, free_orders
            FROM user_bonuses
            WHERE user_id = %s
        """, (user_id,))
        bonus_row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Помилка при отриманні бонусів:", e)

    discount_text = "0%"
    free_orders_text = "0"

    if bonus_row:
        permanent_discount, used_discount_10, free_orders = bonus_row
        if permanent_discount > 0:
            discount_text = f"{'Одноразова' if not used_discount_10 else 'Постійна'} {permanent_discount}%"
        if free_orders > 0:
            free_orders_text = str(free_orders)

    embed = discord.Embed(title="🧾 Особистий кабінет (через ID)", color=0x00ffcc)
    embed.add_field(name="👤 User ID", value=str(user_id), inline=False)
    embed.add_field(name="📦 Замовлень (всього)", value=str(total_orders), inline=True)
    embed.add_field(name="✅ Виконано", value=str(completed_count), inline=True)
    embed.add_field(name="💰 Витрачено", value=f"${total_spent}", inline=True)
    embed.add_field(name="🎟️ Знижка", value=discount_text, inline=True)
    embed.add_field(name="🎁 Безкоштовні замовлення", value=free_orders_text, inline=True)

    await ctx.send(embed=embed)

# ========================================================
#           [Блок: Розсилка знижок за рефералів]
# ========================================================
@bot.command()
@commands.is_owner()  # лише для тебе
async def сповістити_знижку(ctx):
    channel = ctx.guild.get_channel(1361872158435053759)  # 📂-особистий-кабінет

    if not channel:
        await ctx.send("❌ Канал не знайдено.")
        return

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, permanent_discount, used_discount_10, free_orders
        FROM user_bonuses
        WHERE (permanent_discount = 10 AND used_discount_10 = false) OR free_orders > 0
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        await ctx.send("ℹ️ Немає користувачів зі знижкою.")
        return

    for user_id, permanent_discount, used_discount_10, free_orders in rows:
        try:
            member = await ctx.guild.fetch_member(user_id)

            descriptions = []
            if permanent_discount == 10 and not used_discount_10:
                descriptions.append(
                    "🎯 Ви отримали **одноразову знижку 10%** на замовлення.\n"
                    "Вона активується після завершення найближчого виконаного замовлення."
                )
            if free_orders > 0:
                word = "замовлення" if free_orders == 1 else "замовлення(нь)"
                descriptions.append(
                    f"🎁 У вас є **{free_orders} безкоштовне(і) {word}**! Воно буде застосовано автоматично."
                )

            if descriptions:
                embed = discord.Embed(
                    title="🎉 Ви отримали бонус!",
                    description="\n\n".join(descriptions) + "\n\n🔥 Приємного полювання!",
                    color=0x00ff99
                )

                await channel.send(
                    content=f"{member.mention}",
                    embed=embed
                )

            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Не вдалося надіслати повідомлення для {user_id}: {e}")


    await ctx.send("✅ Повідомлення надіслані всім користувачам зі знижкою.")

# ==============================================
#           [Блок: Особистий кабінет мисливця]
# ==============================================
@bot.command(name="моя_статистика")
async def my_stats(ctx):
    user_id = str(ctx.author.id)
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
              COUNT(*) as total_orders,
              COALESCE(SUM(rp.price), 0) as total_earned
            FROM orders o
            JOIN resource_prices rp ON o.details = rp.resource
            WHERE o.hunter = %s AND o.status = 'Виконано';
        """, (ctx.author.name,))  # або user_id якщо поле hunter — ID
        result = cursor.fetchone()

        total_orders = result[0]
        total_earned = result[1]

        await ctx.send(
            f"📊 **Ваша статистика:**\n"
            f"🔹 Виконано замовлень: **{total_orders}**\n"
            f"💰 Зароблено: **{total_earned:,} $**"
        )

        cursor.close()
        conn.close()
    except Exception as e:
        await ctx.send(f"❌ Помилка при отриманні статистики: {e}")


# =================================================
#           [Блок: команда: Особистий кабінет]
# =================================================
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


# ...............................................................
#           [Блок: нагорода за рефералку]
# ............................................................... 
async def check_and_grant_referral_bonus(guild: discord.Guild, inviter_id: int):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        # Рахуємо підтверджених
        cursor.execute("""
            SELECT COUNT(*) FROM referrals
            WHERE inviter_id = %s AND confirmed = TRUE
        """, (str(inviter_id),))
        confirmed_count = cursor.fetchone()[0]

        # Отримуємо бонуси користувача
        cursor.execute("""
            SELECT * FROM user_bonuses WHERE user_id = %s
        """, (inviter_id,))
        user_bonus = cursor.fetchone()

        if not user_bonus:
            cursor.execute("""
                INSERT INTO user_bonuses (user_id) VALUES (%s)
            """, (inviter_id,))
            conn.commit()
            # перезапит для доступу до колонок
            cursor.execute("""
                SELECT * FROM user_bonuses WHERE user_id = %s
            """, (inviter_id,))
            user_bonus = cursor.fetchone()

        columns = [desc[0] for desc in cursor.description]
        bonus_dict = dict(zip(columns, user_bonus))

        updates = []
        log_channel_id = 1361872158435053759  # Особистий кабінет
        channel = guild.get_channel(log_channel_id)

        member = await guild.fetch_member(inviter_id)

        # За 10 рефералів
        if confirmed_count >= 10 and not bonus_dict["used_bonus_10"]:
             # Постійна знижка
            updates.append("used_bonus_10 = TRUE")
            updates.append("permanent_discount = 10")
            role = discord.utils.get(guild.roles, name="VIP Амбасадор")
            if role:
                await member.add_roles(role)
            await channel.send(f"💎 <@{inviter_id}>, ти отримав **роль `VIP Амбасадор` та постійну знижку 10%** за 10 рефералів!")
 
        # За 5 рефералів
        elif confirmed_count >= 5 and not bonus_dict["used_bonus_5"]:
             # Безкоштовне замовлення + роль
            updates.append("used_bonus_5 = TRUE")
            updates.append("free_orders = free_orders + 1")
            role = discord.utils.get(guild.roles, name="Амбасадор")
            if role:
                await member.add_roles(role)
            await channel.send(f"👑 <@{inviter_id}>, ти отримав **ще 1 безкоштовне замовлення та роль `Амбасадор`** за 5 рефералів!")
        
        # За 3 реферали
        elif confirmed_count >= 3 and not bonus_dict["used_bonus_3"]:
             # Безкоштовне замовлення
            updates.append("used_bonus_3 = TRUE")
            updates.append("free_orders = free_orders + 1")
            await channel.send(f"🎁 <@{inviter_id}>, ти отримав **1 безкоштовне замовлення** за 3 реферали!")
        
        # За 1 реферала
        elif confirmed_count >= 1 and not bonus_dict["used_bonus_1"]:
            # Одноразова знижка
            updates.append("used_bonus_1 = TRUE")
            updates.append("permanent_discount = 10")
            await channel.send(f"💰 <@{inviter_id}>, ти отримав **одноразову знижку 10%** за першого реферала!")

        if updates:
            update_query = f"UPDATE user_bonuses SET {', '.join(updates)} WHERE user_id = %s"
            cursor.execute(update_query, (inviter_id,))
            conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        print("❌ Помилка при нарахуванні бонусів:", e)

# =========================================================
#         [БЛОК: ОТРИМАННЯ І ПЕРЕВІРКА СТАТУСУ ЗНИЖОК]
# =========================================================
async def get_user_discount_status(user_id: int) -> int:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT permanent_discount, used_discount_10, free_orders
            FROM user_bonuses
            WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return 0

        permanent_discount, used_discount_10, free_orders = row

        # Якщо є безкоштовні — вважаємо 100%
        if free_orders > 0:
            return 100
        elif permanent_discount > 0 and not used_discount_10:
            return permanent_discount
        else:
            return 0

    except Exception as e:
        print("❌ Помилка при перевірці знижки:", e)
        return 0

# ...............................................................
#           [Блок: Використання знижки]
# ............................................................... 
async def get_user_discount_and_update(user_id: int) -> int:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT free_orders, permanent_discount, used_discount_10
            FROM user_bonuses
            WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()

        discount = 0

        if row:
            free_orders, permanent_discount, used_discount_10 = row

            if free_orders > 0:
                discount = 100
                cursor.execute("""
                    UPDATE user_bonuses
                    SET free_orders = free_orders - 1
                    WHERE user_id = %s
                """, (user_id,))
                print(f"🎁 Використано безкоштовне замовлення для {user_id}")

            elif permanent_discount == 10 and not used_discount_10:
                discount = 10
                cursor.execute("""
                    UPDATE user_bonuses
                    SET used_discount_10 = TRUE, permanent_discount = 0
                    WHERE user_id = %s
                """, (user_id,))
                print(f"💸 Використано одноразову знижку 10% для {user_id}")

            elif permanent_discount > 0:
                discount = permanent_discount
                print(f"🔁 Використано постійну знижку {permanent_discount}% для {user_id}")

        conn.commit()
        cursor.close()
        conn.close()

        return discount

    except Exception as e:
        print("❌ Помилка при визначенні знижки:", e)
        return 0

# ..............................................................................
#           [Блок: Нагадування про знижку у замовника]
# ............................................................... ..............
async def get_discount_notice_text(order_id: int) -> str:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("SELECT discount_percent FROM orders WHERE id = %s", (order_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return ""

        discount = row[0]

        if discount is None:
            return ""

        if discount >= 100:
            return "💎 Це безкоштовне замовлення! Клієнт нічого не платить."
        elif discount > 0:
            return f"💸 Увага! Клієнт має знижку {discount}%. Врахуй це при передачі ресурсу."
        else:
            return ""

    except Exception as e:
        print("❌ Помилка при перевірці знижки на замовлення:", e)
        return ""

# ==================================================
# [Функція]: Отримати статус бонусів користувача
# ==================================================
async def get_user_bonus_status(user_id: int) -> dict:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT used_discount_10, permanent_discount, free_orders
            FROM user_bonuses
            WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if not row:
            return {}

        return {
            "used_discount_10": row[0],
            "permanent_discount": row[1],
            "free_orders": row[2]
        }

    except Exception as e:
        print("❌ Помилка при зчитуванні статусу бонусів:", e)
        return {}

# ===============================================================
#           [Class: Вигляд кнопки особистий кабінет]
# ===============================================================
class CabinetButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📂 Зайти в особистий кабінет", style=discord.ButtonStyle.primary, custom_id="open_cabinet")
    async def open_cabinet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        user_id = interaction.user.id

        total_orders, completed_count = get_user_order_stats(user_id)
        total_spent = get_total_spent(user_id)

        # Отримуємо бонуси користувача
        bonus_row = None
        try:
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT permanent_discount, used_discount_10, free_orders
                FROM user_bonuses
                WHERE user_id = %s
            """, (user_id,))
            bonus_row = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            print("❌ Помилка при отриманні бонусів:", e)

        # Значення за замовчуванням
        discount_text = "0%"
        free_orders_text = "0"

        if bonus_row:
            permanent_discount, used_discount_10, free_orders = bonus_row
            if permanent_discount > 0:
                if used_discount_10:
                    discount_text = f"Постійна {permanent_discount}%"
                else:
                    discount_text = f"Одноразова {permanent_discount}%"
            if free_orders > 0:
                free_orders_text = str(free_orders)


        embed = discord.Embed(title="🧾 Особистий кабінет", color=0x00ffcc)
        embed.add_field(name="Ім’я", value=f"<@{user_id}>", inline=False)
        embed.add_field(name="📦 Замовлень (всього)", value=str(total_orders), inline=True)
        embed.add_field(name="✅ Виконано", value=str(completed_count), inline=True)
        embed.add_field(name="💰 Витрачено", value=f"${total_spent}", inline=True)
        embed.add_field(name="🎟️ Знижка", value=discount_text, inline=True)
        embed.add_field(name="🎁 Безкоштовні замовлення", value=free_orders_text, inline=True)


        await interaction.followup.send(embed=embed, ephemeral=True)

# ...............................................................
#           [Блок: Вигляд кнопки реферальна система]
# ...............................................................
    @discord.ui.button(label="🔗 Реферальна система", style=discord.ButtonStyle.secondary, custom_id="referral_system")
    async def referral_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed(
            title="🧩 Реферальна система",
            description=(
                "🎯 **Запрошуй друзів — отримуй бонуси!**\n"
                "Створи своє унікальне посилання та поділись ним із друзями. "
                "Коли хтось приєднається і зробить своє перше замовлення — ти отримаєш нагороду.\n\n"
                "📊 Натисни **«Мої реферали»**, щоб переглянути, кого ти вже запросив і хто підтверджений."
            ),
            color=0x00ffcc
        )

        await interaction.followup.send(embed=embed, view=ReferralView(), ephemeral=True)


# ...............................................................
#           [Блок: Вигляд кнопки детальна статистика]
# ...............................................................
    @discord.ui.button(label="📊 Детальна статистика", style=discord.ButtonStyle.secondary, custom_id="detailed_stats")
    async def detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
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
        await interaction.followup.send(embed=embed, ephemeral=True)

        cursor.close()
        conn.close()

# ===============================================================
#           [Class: Вигляд кнопки скасувати замовлення]
# ===============================================================
class CancelOrderButtonView(View):
    def __init__(self, order_id: int):
        super().__init__(timeout=None)
        self.add_item(Button(label="❌ Скасувати замовлення", style=discord.ButtonStyle.danger, custom_id=f"cancel_user_{order_id}"))

class ReferralView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="👥 Мої реферали", style=discord.ButtonStyle.secondary, custom_id="my_referrals"))

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

            discount = await get_user_discount_status(user.id)  

            order_data = {
                "customer": user.name,
                "customer_id": user.id,
                "details": selected,
                "hunter": None,
                "status": "Очікує",
                "discount_percent": discount  
            }

            order_id = await save_order_to_db(order_data)
            await interaction.message.delete()

            # ⬇️ Вставляємо розумну перевірку типу знижки
            discount_text = await get_discount_notice_text(order_id)
            bonus_status = await get_user_bonus_status(user.id)

            if discount_text and bonus_status:
                if bonus_status["permanent_discount"] > 0:
                    if bonus_status["used_discount_10"]:
                        discount_text = discount_text.replace("💸", "🔁").replace("знижку", "постійну знижку")
                    else:
                        discount_text = discount_text.replace("💸", "🟢").replace("знижку", "одноразову знижку")

            channel = discord.utils.get(interaction.guild.text_channels, name="✅-виконання-замовлень")
            if channel:
                content = f"📦 Надійшло нове замовлення на **{selected}** від {user.mention}"
                
                if discount_text:
                    content += f"\n{discount_text}"

                message = await channel.send(
                content,
                view=OrderProgressView(user, cid, order_id, stage="new")
            )
                # Зберігаємо ID повідомлення в БД
                conn_save = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor_save = conn_save.cursor()
                cursor_save.execute("""
                    UPDATE orders
                    SET hunter_accept_message_id = %s
                    WHERE id = %s
                """, (message.id, order_id))
                conn_save.commit()
                cursor_save.close()
                conn_save.close()

            # Отримуємо дані про бонуси
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT permanent_discount, used_discount_10, free_orders
                FROM user_bonuses
                WHERE user_id = %s
            """, (user.id,))

            bonus_row = cursor.fetchone()
            cursor.close()
            conn.close()

            discount_reminder = ""

            if bonus_row:
                permanent_discount, used_discount_10, free_orders = bonus_row

                if permanent_discount > 0 and not used_discount_10:
                    discount_reminder += f"\n\n💸 У вас є знижка {permanent_discount}%! Вона застосується після виконання цього замовлення."

                if free_orders > 0:
                    discount_reminder += f"\n\n🎁 У вас є {free_orders} безкоштовне(і) замовлення! Воно буде використано автоматично при виконанні."


            user_channel = interaction.guild.get_channel(1356283008478478546)  # зробити замовлення
            message_content = (
                f"{user.mention}, ваш запит на **{selected}** успішно зареєстровано. Якщо передумали — можете скасувати:"
            )

            if discount_reminder:
                message_content += f"\n{discount_reminder}"

            user_message = await user_channel.send(
                content=message_content,
                view=CancelOrderButtonView(order_id)
            )

            # 💾 Зберігаємо user_message.id в orders.user_message_id
            try:
                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE orders SET user_message_id = %s WHERE id = %s",
                    (user_message.id, order_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                print(f"💾 Збережено user_message_id: {user_message.id}")
            except Exception as e:
                print(f"❌ Не вдалося зберегти user_message_id: {e}")
            
        elif cid.startswith("cancel_user_"):
            order_id = int(cid.replace("cancel_user_", ""))
            order = await get_order_by_id(order_id)
            
            if order["customer_id"] != user.id:
                await interaction.response.send_message("⛔ Ви не можете скасувати чуже замовлення!", ephemeral=True)
                return

            if order["status"] != "Очікує":
                await interaction.response.send_message("⚠️ Це замовлення вже прийнято і не може бути скасоване.", ephemeral=True)
                return

            await update_order_status_by_id(order_id, "Скасовано", hunter_name=None)

            resource = order["details"]
            customer = interaction.user

            # 🧹 Видалення повідомлення замовника з кнопкою скасування
            msg_id = order.get("user_message_id")
            if msg_id:
                try:
                    user_channel = interaction.guild.get_channel(1356283008478478546)  # #зробити-замовлення
                    old_msg = await user_channel.fetch_message(msg_id)
                    await old_msg.delete()
                    print(f"🧹 Видалено user_message_id: {msg_id}")
                except Exception as e:
                    print(f"⚠️ Не вдалося видалити повідомлення замовника: {e}")

            await interaction.response.defer()
            msg = await interaction.channel.send(
            content=f"{user.mention}, ❌ Ви скасували своє замовлення на **{resource}**."
            )

            # 🕓 Видалення повідомлення про скасування через 5 хвилин
            async def delete_cancel_message():
                await asyncio.sleep(300)
                try:
                    await msg.delete()
                    print(f"🧹 Видалено повідомлення про скасування: {msg.id}")
                except Exception as e:
                    print(f"⚠️ Не вдалося видалити повідомлення про скасування: {e}")

            asyncio.create_task(delete_cancel_message())

            # Видаляємо повідомлення про нове замовлення з "виконання-замовлень"
            try:
                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor = conn.cursor()
                cursor.execute("SELECT hunter_accept_message_id FROM orders WHERE id = %s", (order_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                if result and result[0]:
                    hunters_channel_obj = interaction.guild.get_channel(1356291670110507069)
                    if hunters_channel_obj:
                        old_message = await hunters_channel_obj.fetch_message(result[0])
                        await old_message.delete()
            except Exception as e:
                print(f"⚠️ Не вдалося видалити повідомлення про замовлення: {e}")


            hunters_channel = interaction.guild.get_channel(1356291670110507069)
            if hunters_channel:
                await hunters_channel.send(f"⚠️ Замовник {customer.mention} скасував замовлення на **{resource}**.")



        elif cid.startswith("accept_order_"):
            order_id = int(cid.replace("accept_order_", ""))
            order = await get_order_by_id(order_id)

            # 🧹 Видалення повідомлення користувача з кнопкою ❌
            msg_id = order.get("user_message_id")
            if msg_id:
                try:
                    user_channel = interaction.guild.get_channel(1356283008478478546)  # #зробити-замовлення
                    msg = await user_channel.fetch_message(msg_id)
                    await msg.delete()
                    print(f"🧹 Видалено user_message_id: {msg_id}")
                except Exception as e:
                    print(f"⚠️ Не вдалося видалити повідомлення замовника: {e}")

            resource = order["details"]
            hunter = user

            try:
                customer = interaction.message.mentions[0]
            except IndexError:
                await interaction.response.send_message("❌ Не вдалося знайти замовника.", ephemeral=True)
                return

            await interaction.response.edit_message(
                content=(
                    f"🔔 Замовлення на **{resource}** прийнято!\n"
                    f"👤 Замовник: {customer.mention}\n"
                    f"🧭 Мисливець: {hunter.mention}"
                ),
                view=OrderProgressView(customer, cid.split("_")[2], order_id, stage="accepted")
            )


            await mark_order_accepted(order_id, hunter.name)
            notify_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if notify_channel:
                resource_key = resource_reverse.get(resource, "unknown")
                eta = estimated_times.get(resource_key, "20–30 хв")

                msg = await notify_channel.send(
    f"{customer.mention}, Ваше замовлення на **{resource}** прийняв {hunter.mention}! 🕓 Орієнтовний час виконання — ({eta})!"
)

                # 💾 Зберігаємо user_accept_message_id
                try:
                    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE orders SET user_accept_message_id = %s WHERE id = %s",
                        (msg.id, order_id)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print("❌ Не вдалося зберегти user_accept_message_id:", e)
                    
        elif cid.startswith("cancel_"):
            order_id = int(cid.replace("cancel_", ""))
            order = await get_order_by_id(order_id)
            
            if order["status"] != "Очікує":
                await interaction.response.send_message("⚠️ Це замовлення вже в роботі й не може бути скасоване.", ephemeral=True)
                return

            # оновлюємо статус
            await update_order_status_by_id(order_id, "Скасовано", hunter_name=None)

            customer = interaction.user
            resource = order["details"]

            # Повідомлення замовнику
            channel_customer = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if channel_customer:
                await channel_customer.send(f"{customer.mention}, ❌ Ви скасували своє замовлення на **{resource}**.")

            # Повідомлення мисливцям
            channel_hunters = discord.utils.get(interaction.guild.text_channels, name="✅-виконання-замовлень")
            if channel_hunters:
                await channel_hunters.send(f"⚠️ Замовник {customer.mention} скасував замовлення на **{resource}**.")

            # Оновлення повідомлення з кнопками
            await interaction.response.edit_message(
                content=f"❌ Замовлення на **{resource}** було скасовано користувачем.",
                view=None
            )


        elif cid.startswith("ready_"):
            order_id = int(cid.replace("ready_", ""))
            order = await get_order_by_id(order_id)

#=========== Захст кнопок від взаємодії іншими ===========
            if interaction.user.name != order["hunter"]:
                await interaction.response.send_message("⛔ Ви не є виконавцем цього замовлення!", ephemeral=True)
                return

            # 🧹 Видалення повідомлення користувачу з ETA (user_accept_message_id)
            msg_id = order.get("user_accept_message_id")
            if msg_id:
                try:
                    user_channel = interaction.guild.get_channel(1356283008478478546)  # #зробити-замовлення
                    msg = await user_channel.fetch_message(msg_id)
                    await msg.delete()
                    print(f"🧹 Видалено user_accept_message_id: {msg_id}")
                except Exception as e:
                    print(f"⚠️ Не вдалося видалити повідомлення з ETA: {e}")

            customer_id = order["customer_id"]
            customer = await interaction.guild.fetch_member(customer_id)
            resource = order["details"]
            resource_key = resource_reverse.get(resource, "unknown")

            await mark_order_collected(order_id)

            # 💸 Перевірка наявності знижки
            discount_notice = await get_discount_notice_text(order_id)
            if discount_notice:
                await interaction.channel.send(discount_notice)

            notify_channel = discord.utils.get(

                interaction.guild.text_channels,
                name="📝-зробити-замовлення"
            )

            if notify_channel:
                discount = await get_user_discount_status(customer.id)

                if "камінь" in resource.lower():
                    message_text = (
                        f"{customer.mention}, 🪨 Ваш **камінь** готовий! "
                        "Мисливець очікує Вас на кар'єрі.\n"
                        "💡 Звільніть інвентар заздалегідь — буде важко!"
                    )
                else:
                    message_text = (
                        f"{customer.mention}, 📦 Ваш **{resource}** вже в рюкзаку мисливця!\n"
                        "📍 З Вами зараз звʼяжуться для узгодження місця зустрічі."
                    )

                if discount > 0:
                    message_text += (
                        f"\n\n💸 Нагадування! На це замовлення діє знижка **{discount}%**.\n"
                        "Не забудьте про це при сплаті ресурсу 😉"
                    )

                msg = await notify_channel.send(message_text)

            # 💾 Зберігаємо user_ready_message_id
            try:
                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE orders SET user_ready_message_id = %s WHERE id = %s",
                    (msg.id, order_id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                print(f"💾 Збережено user_ready_message_id: {msg.id}")
            except Exception as e:
                print(f"❌ Не вдалося зберегти user_ready_message_id: {e}")

            # 🛠️ Оновлюємо повідомлення з кнопкою
            await interaction.response.edit_message(
                content=(
                    f"📦 Замовлення **{customer.mention}** на {resource} зібране!\n"
                    f"🧭 Виконавець: {interaction.user.mention}"
                ),
                view=OrderProgressView(customer, resource_key, order_id, stage="ready")
            )

        elif cid.startswith("finish_"):
            if interaction.user.bot:
                return

            order_id = int(cid.replace("finish_", ""))
            order = await get_order_by_id(order_id)

#=========== Захст кнопок від взаємодії іншими ===========
            if interaction.user.name != order["hunter"]:
                await interaction.response.send_message("⛔ Ви не є виконавцем цього замовлення!", ephemeral=True)
                return

            # 🧹 Видалення повідомлення з кар'єром
            msg_id = order.get("user_ready_message_id")
            if msg_id:
                try:
                    user_channel = interaction.guild.get_channel(1356283008478478546)  # #зробити-замовлення
                    msg = await user_channel.fetch_message(msg_id)
                    await msg.delete()
                    print(f"🧹 Видалено user_ready_message_id: {msg_id}")
                except Exception as e:
                    print(f"⚠️ Не вдалося видалити повідомлення з кар'єром: {e}")

            customer_id = order["customer_id"]
            customer = await interaction.guild.fetch_member(customer_id)

            # Оновлюємо статус
            await update_order_status_by_id(order_id, "Виконано", hunter_name=user.name)

            # 💸 Застосування знижки після завершення замовлення
            discount = await get_user_discount_and_update(customer_id)

            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET discount_percent = %s WHERE id = %s",
                (discount, order_id)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Повідомлення в тому ж повідомленні
            await interaction.response.edit_message(
                content="✅ Замовлення виконано.",
                view=None
            )

            # Надішлемо сповіщення в загальний канал
            notify_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if notify_channel:
                msg = await notify_channel.send(
                    f"{customer.mention}, Ваше замовлення було позначено як **виконане**. Дякуємо, що скористались нашими послугами! 🤎"
                )

                # ⏳ Видаляємо через 5 хвилин
                async def delayed_delete():
                    await asyncio.sleep(300)  # 300 секунд = 5 хв
                    try:
                        await msg.delete()
                        print(f"🧽 Повідомлення про виконання видалено: {msg.id}")
                    except Exception as e:
                        print(f"⚠️ Не вдалося видалити повідомлення про виконання: {e}")

                asyncio.create_task(delayed_delete())

                try:
                    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT COUNT(*) FROM orders WHERE customer_id = %s AND status = 'Виконано'
                    """, (str(customer_id),))
                    completed_orders = cursor.fetchone()[0]

                    cursor.close()
                    conn.close()

                    if completed_orders == 1:
                        msg = await notify_channel.send(
                        f"💬 Будемо раді бачити Ваш відгук в каналі <#1356362829099303160>!"
                    )

                    # ⏳ Видаляємо через 5 хв
                    async def delete_review_prompt():
                        await asyncio.sleep(300)
                        try:
                            await msg.delete()
                            print(f"🧽 Повідомлення про відгук видалено: {msg.id}")
                        except Exception as e:
                            print(f"⚠️ Не вдалося видалити повідомлення про відгук: {e}")

                    asyncio.create_task(delete_review_prompt())

                except Exception as e:
                    print("❌ Помилка при перевірці кількості виконаних замовлень:", e)

# ...............................................................
#           [Блок: підтвердження реферала]
# ...............................................................                
            try:
                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor = conn.cursor()

                # Перевіряємо, чи вже підтверджений
                cursor.execute("""
                    SELECT confirmed FROM referrals WHERE invited_id = %s
                """, (str(customer_id),))
                confirmed_row = cursor.fetchone()

                if confirmed_row and confirmed_row[0]:  # Якщо confirmed = TRUE
                    print("🔁 Реферал вже підтверджений — пропускаємо.")
                    cursor.close()
                    conn.close()
                    return

                # Перевірка, чи це перше завершене замовлення
                cursor.execute("""
                    SELECT COUNT(*) FROM orders
                    WHERE customer_id = %s AND status = 'Виконано'
                """, (str(customer_id),))
                completed_orders = cursor.fetchone()[0]

                if completed_orders == 1:
                    # ✅ Оновлюємо confirmed
                    cursor.execute("""
                        UPDATE referrals
                        SET confirmed = TRUE
                        WHERE invited_id = %s
                    """, (str(customer_id),))
                    conn.commit()

                    # Отримуємо inviter_id
                    cursor.execute("""
                        SELECT inviter_id FROM referrals
                        WHERE invited_id = %s
                    """, (str(customer_id),))
                    inviter_row = cursor.fetchone()

                    if inviter_row:
                        inviter_id = int(inviter_row[0])
                        bot_id = bot.user.id

                        if inviter_id == bot_id:
                            print("⚠️ Реферал прив'язаний до самого бота — бонус не нараховується.")
                            cursor.close()
                            conn.close()
                            return

                        # ✅ Видати бонус
                        await check_and_grant_referral_bonus(interaction.guild, inviter_id)

                        # Надсилаємо повідомлення в канал
                        cabinet_channel_id = 1361871258435023759  # ID каналу "Особистий кабінет"
                        cabinet_channel = bot.get_channel(cabinet_channel_id)

                        if cabinet_channel:
                            await cabinet_channel.send(
                                f"🎉 <@{inviter_id}>, твій реферал <@{customer_id}> підтверджений! "
                                f"Він виконав перше замовлення. Дякуємо за активність ❤️"
                            )

                cursor.close()
                conn.close()

            except Exception as e:
                print("❌ Помилка при підтвердженні реферала:", e)

# ...............................................................
#           [Блок: кнопка "Мої реферали"]
# ............................................................... 
        elif cid == "my_referrals":
            user_id = interaction.user.id

            try:
                conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                cursor = conn.cursor()

                # Отримуємо всіх рефералів
                cursor.execute("""
                    SELECT invited_id, confirmed FROM referrals
                    WHERE inviter_id = %s
                """, (str(user_id),))
                referrals = cursor.fetchall()

                total = len(referrals)
                confirmed = sum(1 for _, is_confirmed in referrals if is_confirmed)

                if referrals:
                    mention_list = []
                    for invited_id, is_confirmed in referrals:
                        status = "✅" if is_confirmed else "❌"
                        mention_list.append(f"{status} <@{invited_id}>")

                    list_text = "\n".join(mention_list)
                else:
                    list_text = "😔 У тебе ще немає рефералів."

                embed = discord.Embed(
                    title="👥 Твої реферали",
                    description=(
                        f"📌 Запрошено всього: **{total}**\n"
                        f"🟢 Підтверджено: **{confirmed}**\n\n"
                        f"{list_text}"
                    ),
                    color=0x00ffcc
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

                cursor.close()
                conn.close()

            except Exception as e:
                print("❌ Помилка при показі рефералів:", e)
                await interaction.response.send_message(
                    "⚠️ Сталася помилка при завантаженні твоїх рефералів.",
                    ephemeral=True
                )


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)