import discord
import logging
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
import os
import asyncio
from db_logger import (
    save_order_to_db,
    get_orders_by_user,
    get_order_by_id,
    update_order_status_by_id,
    init_db
)
import datetime

logging.basicConfig(
    level=logging.DEBUG,  # INFO, WARNING, ERROR — міняй якщо буде забагато шуму
    format="%(asctime)s [%(levelname)s] %(message)s"
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.add_view(ResourceButtonsView())

@bot.command()
async def start(ctx):
    class OrderButtonView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(Button(label="Замовити послугу", style=discord.ButtonStyle.primary, custom_id="order_service"))

    await ctx.send("Натисни кнопку нижче, щоб зробити замовлення:", view=OrderButtonView())

@bot.command(name="моїзамовлення")
async def my_orders(ctx):
    user_id = ctx.author.id
    orders = await get_orders_by_user(user_id)

    if not orders:
        await ctx.send("🔍 У вас поки немає замовлень.")
        return

    message = "📦 **Ваші замовлення:**\n"
    for order in orders:
        ts = order['timestamp']
        if isinstance(ts, str):
            ts = datetime.datetime.fromisoformat(ts)
        message += f"- `{ts.strftime('%Y-%m-%d %H:%M')}` {order['details']} — **{order['status']}**\n"

    await ctx.send(message)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    print("📩 Interaction received:", interaction.data)
    if interaction.type == discord.InteractionType.component:
        user = interaction.user
        custom_id = interaction.data["custom_id"]

        if custom_id == "order_service":
            await interaction.response.send_message("🛍️ Вибери ресурс для замовлення:", view=ResourceButtonsView(), ephemeral=True)

        elif custom_id in ["stone", "wood", "fish", "mushrooms", "cleaner"]:
            resource_names = {
                "stone": "🪨 Камінь",
                "wood": "🌲 Дерево",
                "fish": "🐟 Риба",
                "mushrooms": "🍄 Гриби",
                "cleaner": "🧴 Миючі засоби"
            }
            selected = resource_names[custom_id]
            order_data = {
                "customer": user.name,
                "customer_id": user.id,
                "type": "Доставка ресурсу",
                "details": selected,
                "hunter": None,
                "status": "Очікує"
            }
            order_id = await save_order_to_db(order_data)

            hunters_channel = discord.utils.get(interaction.guild.text_channels, name="✅-виконання-замовлень")
            if not hunters_channel:
                await interaction.response.send_message("❌ Канал `✅-виконання-замовлень` не знайдено.", ephemeral=True)
                return

            await hunters_channel.send(
                f"🆕 Надійшло нове замовлення на **{selected}** від {user.mention}",
                view=AcceptButtonView(order_id)
            )
            await interaction.response.send_message(
                f"📨 Ваш запит на **{selected}** успішно зареєстровано. Очікуйте підтвердження.",
                ephemeral=True
            )

        elif custom_id.startswith("accept_"):
            order_id = int(custom_id.split("_")[1])
            await interaction.response.defer(ephemeral=True)  # 👉 Це важливо!
            await update_order_status_by_id(order_id, "В роботі", user.name)
            order = await get_order_by_id(order_id)

            target_channel = discord.utils.get(interaction.guild.text_channels, name="зробити-замовлення")
            if target_channel:
                await target_channel.send(
                    f"✅ Мисливець {user.mention} прийняв Ваше замовлення на **{order['details']}**\nОрієнтовний час очікування — 20–25 хв."
                )

            await interaction.message.edit(view=ReadyButtonView(order_id))
            await interaction.followup.send(f"🛠️ Ви прийняли замовлення #{order_id}", ephemeral=True)


        elif custom_id.startswith("ready_"):
            order_id = int(custom_id.split("_")[1])
            await update_order_status_by_id(order_id, "Готове", user.name)
            order = await get_order_by_id(order_id)
            target_channel = discord.utils.get(interaction.guild.text_channels, name="зробити-замовлення")
            if target_channel:
                if "камінь" in order['details'].lower():
                    await target_channel.send(
                        f"🪨 Мисливець зібрав Ваше замовлення і очікує Вас на кар'єрі!"
                    )
                else:
                    await target_channel.send(
                        f"📦 Мисливець зібрав Ваше замовлення. Найближчим часом зв’яжеться з Вами, щоб узгодити місце зустрічі!"
                    )
            await interaction.message.edit(view=FinishButtonView(order_id))
            await interaction.response.send_message(f"📦 Ви позначили замовлення #{order_id} як зібране", ephemeral=True)

        elif custom_id.startswith("finish_"):
            order_id = int(custom_id.split("_")[1])
            await update_order_status_by_id(order_id, "Виконано", user.name)
            order = await get_order_by_id(order_id)
            target_channel = discord.utils.get(interaction.guild.text_channels, name="зробити-замовлення")
            if target_channel:
                await target_channel.send(
                    f"🏁 Мисливець позначив Ваше замовлення як **виконане**!\nДякуємо, що скористались нашими послугами ❤️\nВи можете залишити відгук у #📨-відгуки"
                )
            await interaction.response.send_message(f"✅ Замовлення #{order_id} завершено", ephemeral=True)

class ResourceButtonsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="🪨 Камінь", style=discord.ButtonStyle.secondary, custom_id="stone"))
        self.add_item(Button(label="🌲 Дерево", style=discord.ButtonStyle.secondary, custom_id="wood"))
        self.add_item(Button(label="🐟 Риба", style=discord.ButtonStyle.secondary, custom_id="fish"))
        self.add_item(Button(label="🍄 Гриби", style=discord.ButtonStyle.secondary, custom_id="mushrooms"))
        self.add_item(Button(label="🧴 Миючі засоби", style=discord.ButtonStyle.secondary, custom_id="cleaner"))

class AcceptButtonView(View):
    def __init__(self, order_id: int):
        super().__init__(timeout=None)
        self.order_id = order_id
        self.add_item(Button(label="✅ Прийняти замовлення", style=discord.ButtonStyle.success, custom_id=f"accept_{order_id}"))

    @classmethod
    def is_persistent(cls):
        return True

class ReadyButtonView(View):
    def __init__(self, order_id: int):
        super().__init__(timeout=None)
        self.add_item(Button(label="📦 Зібрано", style=discord.ButtonStyle.primary, custom_id=f"ready_{order_id}"))

class FinishButtonView(View):
    def __init__(self, order_id: int):
        super().__init__(timeout=None)
        self.add_item(Button(label="🏁 Виконано", style=discord.ButtonStyle.secondary, custom_id=f"finish_{order_id}"))

logging.basicConfig(level=logging.DEBUG)

async def main():
    load_dotenv()
    await init_db()
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)

try:
    asyncio.run(main())
except Exception as e:
    logging.exception("❌ Бот звалився з помилкою:")
