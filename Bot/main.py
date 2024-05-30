import os
import discord
import requests
import logging
import sqlite3
from discord.ext import commands
from dotenv import load_dotenv
from discord import ButtonStyle
from discord.ui import View, Button

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
API_KEY = os.getenv('API_KEY')
UPLOAD_URL = os.getenv('UPLOAD_URL')

conn = sqlite3.connect('image_database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS images (user_id INTEGER, image_url TEXT)''')
conn.commit()

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="nht!",
    intents=intents,
    status=discord.Status.dnd,
    activity=discord.Activity(type=discord.ActivityType.watching, name="Starting...")
)

@bot.event
async def on_ready():
    print("Bot is ready!")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="you")
    )

def insert_image(user_id, image_url):
    cursor.execute("INSERT INTO images VALUES (?, ?)", (user_id, image_url))
    conn.commit()

def get_images_by_user(user_id):
    cursor.execute("SELECT image_url FROM images WHERE user_id=?", (user_id,))
    return cursor.fetchall()

@bot.tree.command(name="uploadimage", description="Upload an image to the server")
async def upload_image(interaction: discord.Interaction, attachment: discord.Attachment):
    if not any(attachment.filename.lower().endswith(image_type) for image_type in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
        await interaction.response.send_message("Please provide a valid image file.", ephemeral=True)
        return

    await interaction.response.send_message("Uploading image...", ephemeral=True)
    
    try:
        image_data = await attachment.read()
        files = {"file": (attachment.filename, image_data)}
        headers = {"x-api-key": API_KEY}
        
        response = requests.post(UPLOAD_URL, headers=headers, files=files)

        if response.status_code == 200:
            response_json = response.json()
            image_url = response_json.get("url")
            
            if image_url:
                insert_image(interaction.user.id, image_url)
                embed = discord.Embed(title="Image Uploaded Successfully", description="Here is your uploaded image:")
                embed.set_image(url=image_url)
                await interaction.edit_original_response(embed=embed)
            else:
                logging.error("No URL in response JSON.")
                await interaction.edit_original_response(content='Failed to upload the image. No URL returned.')
        else:
            logging.error(f"Failed to upload image: {response.status_code} {response.text}")
            await interaction.edit_original_response(content='Failed to upload the image. Please try again later.')
    except Exception as e:
        logging.exception("Error processing image attachment.")
        await interaction.edit_original_response(content='An error occurred while processing the image. Please try again later.')

@bot.tree.command(name="myimages", description="View all uploaded images with pagination")
async def my_images(interaction: discord.Interaction):
    user_id = interaction.user.id
    images = get_images_by_user(user_id)
    if not images:
        await interaction.response.send_message("You haven't uploaded any images yet.", ephemeral=True)
        return

    def create_embed(image_url):
        embed = discord.Embed(title="Your Uploaded Images", color=discord.Color.blurple())
        embed.set_image(url=image_url)
        return embed

    pages = [[image[0]] for image in images]

    current_page = 0

    embed = create_embed(pages[current_page][0])
    
    class PaginatorView(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.current_page = current_page
            self.pages = pages
        
        @discord.ui.button(label="Previous", style=ButtonStyle.gray, disabled=True)
        async def previous_button(self, interaction: discord.Interaction, button: Button):
            self.current_page = max(0, self.current_page - 1)
            if self.current_page == 0:
                button.disabled = True
            self.children[1].disabled = False

            embed = create_embed(self.pages[self.current_page][0])
            await interaction.response.edit_message(embed=embed, view=self)
        
        @discord.ui.button(label="Next", style=ButtonStyle.gray)
        async def next_button(self, interaction: discord.Interaction, button: Button):
            self.current_page = min(len(self.pages) - 1, self.current_page + 1)
            if self.current_page == len(self.pages) - 1:
                button.disabled = True
            self.children[0].disabled = False

            embed = create_embed(self.pages[self.current_page][0])
            await interaction.response.edit_message(embed=embed, view=self)

    view = PaginatorView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

bot.run(TOKEN)
