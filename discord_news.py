import requests
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
nltk.download('vader_lexicon')

class NewsTracker:
    def __init__(self):
        # Load environment variables
        load_dotenv(r'C:\Users\Chris\Documents\discord_bot/apis.env')
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.discord_token = os.getenv('DISCORD_TOKEN')
        
        # Discord bot setup
        self.bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))  # Add your channel ID to .env
        
        # Sentiment analyzer
        self.sid = SentimentIntensityAnalyzer()
        
        # News API endpoint
        self.news_endpoint = "https://newsapi.org/v2/top-headlines"
        
    def get_top_news(self, country='us', page_size=5):
        """Fetch top news headlines using NewsAPI"""
        try:
            params = {
                'country': country,
                'apiKey': self.news_api_key,
                'pageSize': page_size,
                'category': 'general'
            }
            
            response = requests.get(self.news_endpoint, params=params)
            response.raise_for_status()
            news_data = response.json()
            
            return news_data['articles']
        except requests.RequestException as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text"""
        scores = self.sid.polarity_scores(text)
        compound_score = scores['compound']
        
        if compound_score >= 0.05:
            return "Positive"
        elif compound_score <= -0.05:
            return "Negative"
        else:
            return "Neutral"

    def summarize_text(self, text, max_length=200):
        """Create a summary of the text"""
        if len(text) <= max_length:
            return text
        
        # Simple summarization: take first few sentences
        sentences = text.split('. ')
        summary = '. '.join(sentences[:2]) + '.'
        return summary[:max_length]

    async def format_news_message(self, article):
        """Format news article into Discord-friendly message"""
        title = article.get('title', 'No title')
        description = article.get('description', 'No description') or ''
        url = article.get('url', 'No URL')
        
        summary = self.summarize_text(description)
        sentiment = self.analyze_sentiment(f"{title} {description}")
        
        embed = discord.Embed(
            title=title[:256],  # Discord embed title limit
            description=summary,
            url=url,
            color=0x00ff00 if sentiment == "Positive" else 0xff0000 if sentiment == "Negative" else 0x808080,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Sentiment", value=sentiment, inline=True)
        embed.set_footer(text="News Bot | Powered by NewsAPI")
        
        if article.get('urlToImage'):
            embed.set_thumbnail(url=article['urlToImage'])
            
        return embed

    async def send_news_update(self):
        """Send news updates to Discord channel"""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.error("Channel not found")
            return

        articles = self.get_top_news()
        if not articles:
            await channel.send("No news articles found at this time.")
            return

        for article in articles:
            embed = await self.format_news_message(article)
            await channel.send(embed=embed)
            await asyncio.sleep(1)  # Rate limiting

    def setup_bot(self):
        """Setup Discord bot events and commands"""
        @self.bot.event
        async def on_ready():
            logger.info(f'Bot connected as {self.bot.user}')
            # Schedule news updates every hour
            while True:
                await self.send_news_update()
                await asyncio.sleep(3600)  # 1 hour

        @self.bot.command()
        async def news(ctx):
            """Manual command to fetch news"""
            await self.send_news_update()
            await ctx.send("News update complete!")

    def run(self):
        """Start the bot"""
        try:
            self.setup_bot()
            self.bot.run(self.discord_token)
        except Exception as e:
            logger.error(f"Error running bot: {e}")

def main():
    
    tracker = NewsTracker()
    tracker.run()

if __name__ == "__main__":
    main()
