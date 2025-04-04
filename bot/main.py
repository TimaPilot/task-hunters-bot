import discord
from discord.ext import commands
from discord.ui import View, Button
from order_logger import save_order_to_json, update_order_status_by_id
from order_logger import get_order_by_id
from dotenv import load_dotenv
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def start(ctx):
    class OrderButtonView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(Button(label="Замовити послугу", style=discord.ButtonStyle.primary, custom_id="order_service"))

    await ctx.send("Натисни кнопку нижче, щоб зробити замовлення:", view=OrderButtonView())

@bot.command(name="моїзамовлення")
async def my_orders(ctx):
    from order_logger import get_orders_by_user

    user_id = ctx.author.id
    orders = get_orders_by_user(user_id)

    if not orders:
        await ctx.send("🔍 У вас поки немає замовлень.")
        return

    # Формуємо красивий список
    message = "📦 **Ваші замовлення:**\n"
    for order in orders[-10:]:  # показуємо тільки останні 10
        message += f"- `{order['timestamp']}` {order['details']} — **{order['status']}**\n"

    await ctx.send(message)

@bot.command(name="кабінет")
async def user_dashboard(ctx):
    from order_logger import get_orders_by_user
    import datetime

    user = ctx.author
    orders = get_orders_by_user(user.id)

    if not orders:
        await ctx.send("📭 У вас ще не було жодного замовлення.")
        return

    total = len(orders)

    # 🎖️ Система досягнень
    if total >= 20:
        status = "ВІП-клієнт 🏆"
    elif total >= 12:
        status = "Постійний клієнт 🔥"
    elif total >= 5:
        status = "Активний замовник 🌿"
    else:
        status = "Новачок 🐣"

    timestamps = [datetime.datetime.strptime(o["timestamp"], "%Y-%m-%d %H:%M:%S") for o in orders]
    first = min(timestamps).strftime("%Y-%m-%d %H:%M")
    last = max(timestamps).strftime("%Y-%m-%d %H:%M")

    message = (
        f"👤 **{user.name}**\n"
        f"📦 Всього замовлень: **{total}**\n"
        f"🏅 Ваш статус: **{status}**\n"
        f"🕓 Перше замовлення: `{first}`\n"
        f"📅 Останнє замовлення: `{last}`"
    )

    await ctx.send(message)


@bot.command(name="мисливець")
async def hunter_dashboard(ctx):
    from order_logger import load_orders
    import datetime

    user = ctx.author
    all_orders = load_orders()

    # Вибираємо лише ті, де користувач був мисливцем і статус = "Виконано"
    hunter_orders = [
        o for o in all_orders
        if o.get("hunter") == user.name and o.get("status") == "Виконано"
    ]

    if not hunter_orders:
        await ctx.send("📭 Ви ще не виконали жодного замовлення.")
        return

    total = len(hunter_orders)
    timestamps = [datetime.datetime.strptime(o["timestamp"], "%Y-%m-%d %H:%M:%S") for o in hunter_orders]
    first = min(timestamps).strftime("%Y-%m-%d %H:%M")
    last = max(timestamps).strftime("%Y-%m-%d %H:%M")

    message = (
        f"🧑‍🌾 **{user.name}**\n"
        f"✅ Виконано замовлень: **{total}**\n"
        f"📅 Перше виконане: `{first}`\n"
        f"🕓 Останнє виконане: `{last}`"
    )

    await ctx.send(message)

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
            self.add_item(Button(
                label="✅ Прийняти замовлення",
                style=discord.ButtonStyle.success,
                custom_id=f"accept_order_{order_id}"
            ))

        elif stage == "accepted":
            self.add_item(Button(
                label="✅ Зібрано",
                style=discord.ButtonStyle.secondary,
                custom_id=f"ready_{order_id}"
            ))

        elif stage == "ready":
            self.add_item(Button(
                label="✅ Завершити замовлення",
                style=discord.ButtonStyle.success,
                custom_id=f"finish_{order_id}"
            ))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:

        # Натискання "Замовити послугу"
        if interaction.data["custom_id"] == "order_service":
            await interaction.response.send_message("🛒 Вибери ресурс для замовлення:", view=ResourceButtonsView(), ephemeral=True)

        # Вибір ресурсу
        elif interaction.data["custom_id"] in ["stone", "wood", "fish", "mushrooms", "cleaner"]:
            from order_logger import save_order_to_json  # імпортуємо тут

            resource_names = {
                "stone": "🪨 Камінь",
                "wood": "🌲 Дерево",
                "fish": "🐟 Риба",
                "mushrooms": "🍄 Гриби",
                "cleaner": "🧴 Миючі засоби"
            }
            selected = resource_names[interaction.data["custom_id"]]
            user = interaction.user

            # ⬇️ ЛОГУЄМО ЗАМОВЛЕННЯ
            order_data = {
                "customer": user.name,
                "customer_id": user.id,
                "type": "Доставка ресурсу",
                "details": selected,
                "hunter": None,
                "status": "Очікує"
            }
            order_id = save_order_to_json(order_data)

            guild = interaction.guild
            hunters_channel = discord.utils.get(guild.text_channels, name="✅-виконання-замовлень")

            if not hunters_channel:
                await interaction.response.send_message("❌ Канал `✅-виконання-замовлень` не знайдено.", ephemeral=True)
                return

            await hunters_channel.send(
                f"🆕 Надійшло нове замовлення на **{selected}** від {user.mention}",
                view=OrderProgressView(user, interaction.data["custom_id"], order_id, stage="new")
            )

            await interaction.response.send_message(
                f"📨 Ваш запит на **{selected}** успішно зареєстровано. Очікуйте підтвердження.",
                ephemeral=True
            )

        # Прийняття замовлення
        elif interaction.data["custom_id"].startswith("accept_order_"):
            from order_logger import get_order_by_id, update_order_status_by_id

            order_id = int(interaction.data["custom_id"].replace("accept_order_", ""))
            order = get_order_by_id(order_id)

            details = order["details"]
            hunter = interaction.user

            # 🧠 Reverse mapping
            resource_reverse = {
                "🪨 Камінь": "stone",
                "🌲 Дерево": "wood",
                "🐟 Риба": "fish",
                "🍄 Гриби": "mushrooms",
                "🧴 Миючі засоби": "cleaner"
            }
            estimated_times = {
                "stone": "30–60 хв",
                "wood": "15–20 хв",
                "fish": "25–35 хв",
                "mushrooms": "30 хв",
                "cleaner": "20–25 хв"
            }

            resource_key = resource_reverse.get(details, "unknown")
            estimated_time = estimated_times.get(resource_key, "⏳")

            try:
                customer = interaction.message.mentions[0]
            except IndexError:
                await interaction.response.send_message("Не вдалося знайти замовника 🫠", ephemeral=True)
                return

            await interaction.response.edit_message(
                content=f"🔔 Замовлення на **{details}** прийнято мисливцем {hunter.mention}!",
                view=OrderProgressView(customer, resource_key, order_id, stage="accepted")
            )

            update_order_status_by_id(order_id, "В роботі", hunter_name=hunter.name)

            order_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if order_channel:
                await order_channel.send(
                    f"{customer.mention}, ваше замовлення на {details} прийняв {hunter.mention}, Орієнтовний час виконання ~{estimated_time}!"
                )

        # Натиснуто "✅ Зібрано"
        elif interaction.data["custom_id"].startswith("ready_"):
            from order_logger import get_order_by_id

            order_id = int(interaction.data["custom_id"].replace("ready_", ""))
            order = get_order_by_id(order_id)
            customer_id = order["customer_id"]
            resource = order["details"]  # Тут вже буде 🪨 Камінь, 🌲 Дерево і т.д.

            try:
                customer = await interaction.guild.fetch_member(customer_id)
            except:
                await interaction.response.send_message("❌ Не вдалося знайти замовника по ID.", ephemeral=True)
                return

            order_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if not order_channel:
                await interaction.response.send_message("❌ Канал '📝-зробити-замовлення' не знайдено.", ephemeral=True)
                return

            if "камінь" in resource.lower() or "🪨" in resource:
                text = (
                    f"✅ Мисливець вже зібрав необхідну кількість руди та очікує Вас на кар'єрі!\n"
                    f"💡 *Порада: не забудьте звільнити інвентар.*"
                )
            else:
                text = f"✅ Мисливець вже зібрав {resource} та зв'яжеться з Вами для узгодження місця зустрічі!"

            await order_channel.send(f"{customer.mention}, {text}")
            await interaction.response.edit_message(
                content=interaction.message.content,
                view=OrderProgressView(customer, resource, order_id, stage="ready")
            )
            await interaction.followup.send("📨 Повідомлення замовнику відправлено.", ephemeral=True)

       # ⬇️ Натиснуто "✅ Завершити замовлення"
        elif interaction.data["custom_id"].startswith("finish_"):
            from order_logger import update_order_status_by_id, get_order_by_id

            order_id = int(interaction.data["custom_id"].replace("finish_", ""))
            order = get_order_by_id(order_id)
            customer_id = order["customer_id"]

            try:
                customer = await interaction.guild.fetch_member(customer_id)
            except:
                await interaction.response.send_message("❌ Не вдалося знайти замовника по ID.", ephemeral=True)
                return

            update_order_status_by_id(order_id, "Виконано", hunter_name=interaction.user.name)

            await interaction.response.edit_message(
                content="✅ Замовлення позначене як *виконане*.",
                view=None
            )

            order_channel = discord.utils.get(interaction.guild.text_channels, name="📝-зробити-замовлення")
            if order_channel:
                await order_channel.send(
                    f"{customer.mention}, ваше замовлення було позначено як **виконане**. "
                    "Дякуємо, що скористались нашими послугами!\n"
                    "💬 Будемо раді бачити Ваш відгук в каналі <#1356362829099303160>!"
                )


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)
