import discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
import os
import datetime
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

@bot.command(name="очистити_за_статусом")
async def clear_orders_by_status(ctx, *, status: str):
    if ctx.author.id != 386329540353458186:
        await ctx.send("❌ У вас немає прав на виконання цієї команди.")
        return

    await delete_orders_by_status(status)
    await ctx.send(f"🧹 Видалено всі замовлення зі статусом: **{status}**.")

# ==============================================
#           [Блок: Статистика]
# ==============================================
@bot.command(name="моїзамовлення")
async def my_orders(ctx):
    user_id = ctx.author.id
    orders = await get_orders_by_user(user_id)

    if not orders:
        await ctx.send("🔍 У вас поки немає замовлень.")
        return

    message = "📦 **Ваші замовлення:**\n"
    for order in orders[-10:]:
        ts = order['timestamp']
        if isinstance(ts, str):
            ts = datetime.datetime.fromisoformat(ts)

        formatted_ts = ts.strftime("%Y-%m-%d %H:%M")  # формат виводу часу
        message += f"- `{formatted_ts}` {order['details']} — **{order['status']}**\n"

    await ctx.send(message)

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
