import discord
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

            msg = await hunters_channel.send(
                f"🆕 Надійшло нове замовлення на **{selected}** від {user.mention}",
                view=AcceptOrderView(order_id)
            )
            await interaction.response.send_message(
                f"📨 Ваш запит на **{selected}** успішно зареєстровано. Очікуйте підтвердження.",
                ephemeral=True
            )

        elif custom_id.startswith("accept_"):
            order_id = int(custom_id.split("_")[1])
            await update_order_status_by_id(order_id, "В роботі", user.name)
            await interaction.response.send_message(f"🛠️ Ви прийняли замовлення #{order_id}", ephemeral=True)

        elif custom_id.startswith("ready_"):
            order_id = int(custom_id.split("_")[1])
            await update_order_status_by_id(order_id, "Готове", user.name)
            await interaction.response.send_message(f"📦 Ви позначили замовлення #{order_id} як готове", ephemeral=True)

        elif custom_id.startswith("finish_"):
            order_id = int(custom_id.split("_")[1])
            await update_order_status_by_id(order_id, "Виконано", user.name)
            await interaction.response.send_message(f"✅ Ви завершили замовлення #{order_id}", ephemeral=True)

class ResourceButtonsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="🪨 Камінь", style=discord.ButtonStyle.secondary, custom_id="stone"))
        self.add_item(Button(label="🌲 Дерево", style=discord.ButtonStyle.secondary, custom_id="wood"))
        self.add_item(Button(label="🐟 Риба", style=discord.ButtonStyle.secondary, custom_id="fish"))
        self.add_item(Button(label="🍄 Гриби", style=discord.ButtonStyle.secondary, custom_id="mushrooms"))
        self.add_item(Button(label="🧴 Миючі засоби", style=discord.ButtonStyle.secondary, custom_id="cleaner"))

class AcceptOrderView(View):
    def __init__(self, order_id):
        super().__init__(timeout=None)
        self.add_item(Button(label="✅ Прийняти", style=discord.ButtonStyle.success, custom_id=f"accept_{order_id}"))
        self.add_item(Button(label="📦 Готове", style=discord.ButtonStyle.primary, custom_id=f"ready_{order_id}"))
        self.add_item(Button(label="🏁 Завершити", style=discord.ButtonStyle.secondary, custom_id=f"finish_{order_id}"))

async def main():
    load_dotenv()
    await init_db()
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)

asyncio.run(main())