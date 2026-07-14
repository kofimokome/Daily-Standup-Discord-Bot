"""
Scheduler module for handling daily standup messages and follow-ups.

Uses APScheduler to schedule:
- Daily standup prompts at 5:00 PM
- Follow-up messages before the next standup
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import discord
import pytz

logger = logging.getLogger(__name__)


class StandupScheduler:
    """Manages scheduled tasks for standup messages."""
    
    def __init__(self, bot: discord.Client, database, message_parser, channel_id: Optional[int] = None, timezone: Optional[str] = None):
        """
        Initialize the scheduler.
        
        Args:
            bot: Discord bot instance
            database: Database instance
            message_parser: Message parser instance
            channel_id: Discord channel ID for standup messages
            timezone: Timezone string (e.g., 'America/New_York', 'UTC'). Defaults to UTC if not specified.
        """
        self.bot = bot
        self.database = database
        self.message_parser = message_parser
        self.scheduler = AsyncIOScheduler()
        self.channel_id = channel_id
        
        # Set timezone
        if timezone:
            try:
                self.timezone = pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone '{timezone}', defaulting to UTC")
                self.timezone = pytz.UTC
        else:
            self.timezone = pytz.UTC
        
        self.is_running = False
    
    async def send_daily_standup(self):
        """Send the daily standup prompt message."""
        if not self.channel_id:
            logger.warning("No channel ID set. Cannot send daily standup.")
            return
        
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Channel {self.channel_id} not found.")
                return
            
            # Create an embed for a more appealing message
            embed = discord.Embed(
                title="🌅 Daily Standup Time!",
                description="Time to share your progress and plans with the team!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📝 Today's Question",
                value="What did you work on today for the project?",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Tomorrow's Question",
                value="What will you work on tomorrow?",
                inline=False
            )
            
            embed.add_field(
                name="💬 How to Respond",
                value="Reply to this message with your standup update!",
                inline=False
            )
            
            embed.set_footer(text="💡 Tip: Be specific about your accomplishments and plans!")
            embed.timestamp = datetime.now()
            
            # Find and mention the intern role
            mention_text = ""
            if channel.guild:
                # Try to find the intern role (case-insensitive)
                developer_role = discord.utils.get(channel.guild.roles, name="intern")
                if not developer_role:
                    # Try alternative common names
                    developer_role = discord.utils.get(channel.guild.roles, name="developer")
                if not developer_role:
                    developer_role = discord.utils.get(channel.guild.roles, name="interns")
                
                if developer_role:
                    mention_text = f"{developer_role.mention}\n\n"
                    logger.info(f"Mentioning role: {developer_role.name}")
                else:
                    logger.warning("intern role not found. Standup sent without role mention.")
            
            sent_message = await channel.send(content=mention_text, embed=embed)
            logger.info(f"Sent daily standup message to channel {self.channel_id}")
            
            # Update bot's tracking if it's a StandupBot instance
            if hasattr(self.bot, 'last_standup_time'):
                self.bot.last_standup_time = datetime.now()
                self.bot.standup_message_id = sent_message.id
            
        except Exception as e:
            logger.error(f"Error sending daily standup: {e}")
    
    async def send_follow_ups(self):
        """Send follow-up messages for yesterday's commitments."""
        try:
            # Get yesterday's date
            yesterday = datetime.now().date() - timedelta(days=1)
            
            # Get pending follow-ups
            commitments = self.database.get_pending_follow_ups(yesterday)
            
            if not commitments:
                logger.info(f"No follow-ups needed for {yesterday}")
                return
            
            if not self.channel_id:
                logger.warning("No channel ID set. Cannot send follow-ups.")
                return
            
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Channel {self.channel_id} not found.")
                return
            
            # Send follow-up for each commitment
            for commitment in commitments:
                user_id = commitment['user_id']
                username = commitment['username']
                commitment_text = commitment['tomorrow_commitment']
                commitment_id = commitment['id']
                
                try:
                    user = self.bot.get_user(user_id)
                    mention = user.mention if user else f"@{username}"
                    
                    # Create an embed for a more appealing message
                    embed = discord.Embed(
                        title="📋 Accountability Check-in",
                        description=f"Hey {mention}! Let's check in on your commitment from yesterday.",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(
                        name="🎯 Your Commitment",
                        value=f"*\"{commitment_text}\"*",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="❓ Status",
                        value="Did you get this done?",
                        inline=False
                    )
                    
                    embed.set_footer(text="Reply with ✅ if done, or let us know your progress!")
                    embed.timestamp = datetime.now()
                    
                    await channel.send(embed=embed)
                    logger.info(f"Sent follow-up to user {username} for commitment: {commitment_text}")
                    
                    # Mark follow-up as sent
                    self.database.mark_follow_up_sent(commitment_id, datetime.now().date())
                    
                except Exception as e:
                    logger.error(f"Error sending follow-up to user {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending follow-ups: {e}")
    
    def start(self, hour: int = 17, minute: int = 0):
        """
        Start the scheduler with daily standup at specified time.
        
        Args:
            hour: Hour of day (24-hour format, default 17 for 5:00 PM)
            minute: Minute of hour (default 0)
        """
        if self.is_running:
            logger.warning("Scheduler is already running.")
            return
        
        # Schedule daily standup with timezone
        self.scheduler.add_job(
            self.send_daily_standup,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
            id='daily_standup',
            name='Daily Standup Message',
            replace_existing=True
        )
        
        # Schedule follow-ups 30 minutes before standup
        follow_up_hour = hour
        follow_up_minute = minute - 30
        if follow_up_minute < 0:
            follow_up_minute += 60
            follow_up_hour -= 1
            if follow_up_hour < 0:
                follow_up_hour = 23
        
        self.scheduler.add_job(
            self.send_follow_ups,
            trigger=CronTrigger(hour=follow_up_hour, minute=follow_up_minute, timezone=self.timezone),
            id='follow_ups',
            name='Follow-up Messages',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        tz_name = self.timezone.zone if hasattr(self.timezone, 'zone') else str(self.timezone)
        logger.info(f"Scheduler started. Standup at {hour:02d}:{minute:02d}, follow-ups at {follow_up_hour:02d}:{follow_up_minute:02d} ({tz_name})")
    
    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
    
    def update_standup_time(self, hour: int, minute: int):
        """
        Update the standup time.
        
        Args:
            hour: New hour (24-hour format)
            minute: New minute
        """
        if not self.is_running:
            logger.warning("Scheduler is not running. Cannot update time.")
            return
        
        # Remove old jobs
        self.scheduler.remove_job('daily_standup')
        self.scheduler.remove_job('follow_ups')
        
        # Add new jobs with updated time
        self.start(hour, minute)
        logger.info(f"Updated standup time to {hour:02d}:{minute:02d}")
    
    def set_channel(self, channel_id: int):
        """
        Set the channel for standup messages.
        
        Args:
            channel_id: Discord channel ID
        """
        self.channel_id = channel_id
        self.database.set_config('standup_channel_id', str(channel_id))
        logger.info(f"Set standup channel to {channel_id}")
    
    def schedule_test_standup(self, minutes_from_now: int):
        """
        Schedule a one-time test standup message X minutes from now.
        
        Args:
            minutes_from_now: Number of minutes from now to send the standup
            
        Returns:
            Job ID of the scheduled job
        """
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
        
        # Calculate the target time
        target_time = datetime.now(self.timezone) + timedelta(minutes=minutes_from_now)
        
        # Schedule a one-time job
        job = self.scheduler.add_job(
            self.send_daily_standup,
            trigger='date',
            run_date=target_time,
            id=f'test_standup_{target_time.timestamp()}',
            replace_existing=True
        )
        
        logger.info(f"Scheduled test standup for {target_time} ({minutes_from_now} minutes from now)")
        return job.id

