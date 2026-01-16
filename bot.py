import discord
from discord.ext import commands, tasks
from logic import DatabaseManager, hide_img
from config import TOKEN, DATABASE
import os
import cv2
import numpy as np
import os
from logic import *
from math import sqrt, ceil, floor

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

manager = DatabaseManager(DATABASE)
manager.create_tables()

# Perintah untuk user mendaftar
@bot.command()
async def start(ctx):
    user_id = ctx.author.id
    if user_id in manager.get_users():
        await ctx.send("Kamu sudah terdaftar!")
    else:
        manager.add_user(user_id, ctx.author.name)
        await ctx.send("""Hai! Selamat datang! Kamu telah berhasil terdaftar! Kamu akan menerima gambar baru setiap menit, dan kamu memiliki kesempatan untuk mendapatkannya! Untuk melakukannya, kamu perlu mengklik tombol 'Ambil!'! Hanya tiga pengguna pertama yang mengklik tombol 'Ambil!' yang akan mendapatkan gambarnya! =)""")

# Tugas terjadwal untuk mengirim gambar
@tasks.loop(minutes=1)
async def send_message():
    for user_id in manager.get_users():
        prize_id, img = manager.get_random_prize()[:2]
        hide_img(img)
        user = await bot.fetch_user(user_id) 
        if user:
            await send_image(user, f'hidden_img/{img}', prize_id)
        manager.mark_prize_used(prize_id)

async def send_image(user, image_path, prize_id):
    with open(image_path, 'rb') as img:
        file = discord.File(img)
        button = discord.ui.Button(label="Ambil!", custom_id=str(prize_id))
        view = discord.ui.View()
        view.add_item(button)
        await user.send(file=file, view=view)

@bot.command()
async def rating(ctx):
    res = manager.get_rating()
    res = [f'| @{x[0]:<11} | {x[1]:<11}|\n{"_"*26}' for x in res]
    res = '\n'.join(res)
    res = f'|USER_NAME    |COUNT_PRIZE|\n{"_"*26}\n' + res
    await ctx.send(f"```\n{res}\n```")

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data['custom_id']
        user_id = interaction.user.id

        if manager.get_winners_count(custom_id) < 3:
            res = manager.add_winner(user_id, custom_id)
            if res:
                img = manager.get_prize_img(custom_id)
                with open(f'img/{img}', 'rb') as photo:
                    file = discord.File(photo)
                    await interaction.response.send_message(file=file, content="Selamat, kamu mendapatkan gambar!")
            else:
                await interaction.response.send_message(content="Kamu sudah mendapatkan gambar!", ephemeral=True)
        else:
            await interaction.response.send_message(content="Maaf, seseorang sudah mendapatkan gambar ini.", ephemeral=True)


def create_collage(image_paths):
    images = []
    for path in image_paths:
        image = cv2.imread(path)
        images.append(image)

    num_images = len(images)
    num_cols = floor(sqrt(num_images)) # Cari jumlah gambar secara horizontal
    num_rows = ceil(num_images/num_cols)  # Cari jumlah gambar secara vertikal
    # Membuat kolase kosong
    collage = np.zeros((num_rows * images[0].shape[0], num_cols * images[0].shape[1], 3), dtype=np.uint8)
    # Menempatkan gambar pada kolase
    for i, image in enumerate(images):
        row = i // num_cols
        col = i % num_cols
        collage[row*image.shape[0]:(row+1)*image.shape[0], col*image.shape[1]:(col+1)*image.shape[1], :] = image
    return collage




@bot.command()
async def get_my_score(ctx):
    user_id = ctx.author.id
    m = DatabaseManager(DATABASE)
    info = m.get_winners_img(user_id)
    prizes = [x[0] for x in info]
    image_paths = os.listdir('img')
    image_paths = [f'img/{x}' if x in prizes else f'hidden_img/{x}' for x in image_paths]
    collage = create_collage(image_paths)

    output_path = f"collage_{ctx.author.id}.png"
    cv2.imwrite(output_path, collage)

    await ctx.send(
        content="Ini kolase hadiah kamu 🎉",
        file=discord.File(output_path)
    )

    await ctx.send(f"Kamu telah memenangkan {len(prizes)} hadiah!")


    os.remove(output_path)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    if not send_message.is_running():
        send_message.start()

bot.run(TOKEN)
