"""
Scheduler module for handling daily standup messages and follow-ups.

Uses APScheduler to schedule:
- Daily standup prompts at 5:00 PM
- Follow-up messages before the next standup
"""

import logging
import os
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
            
            # Find and mention the configured role
            mention_text = ""
            role_name = self.database.get_config('standup_role_name') or os.getenv('STANDUP_ROLE') or 'intern'
            developer_role = None
            
            if channel.guild:
                developer_role = discord.utils.get(channel.guild.roles, name=role_name)
                if not developer_role:
                    developer_role = discord.utils.get(channel.guild.roles, name=role_name.lower())
                if not developer_role:
                    developer_role = discord.utils.get(channel.guild.roles, name=role_name.capitalize())
                
                if developer_role:
                    mention_text = f"{developer_role.mention}\n\n"
                    logger.info(f"Mentioning role: {developer_role.name}")
                else:
                    logger.warning(f"Standup role '{role_name}' not found. Standup sent without role mention.")
            
            # Record last standup time
            now_time = datetime.now()
            self.database.set_config('last_standup_time', now_time.isoformat())
            
            # Update bot's tracking if it's a StandupBot instance
            if hasattr(self.bot, 'last_standup_time'):
                self.bot.last_standup_time = now_time
                self.bot.standup_message_id = None
                
            # Send DM reminders privately to members of the configured role
            if developer_role:
                for member in developer_role.members:
                    if not member.bot:
                        try:
                            embed_dm = discord.Embed(
                                title="🌅 Standup Reminder",
                                description="Hi there! It's time for the daily standup. Please reply directly to me (via DM) with your update.",
                                color=discord.Color.green()
                            )
                            embed_dm.add_field(name="📝 Today's Question", value="What did you work on today for the project?", inline=False)
                            embed_dm.add_field(name="🚀 Tomorrow's Question", value="What will you work on tomorrow?", inline=False)
                            await member.send(embed=embed_dm)
                            logger.info(f"Sent standup DM reminder to {member.name}")
                        except Exception as dm_err:
                            logger.warning(f"Could not send DM reminder to {member.name}: {dm_err}")
                            
            # Schedule summary checking after configured timeout minutes
            timeout_min = int(self.database.get_config('standup_timeout_minutes') or os.getenv('STANDUP_TIMEOUT_MINUTES') or '30')
            summary_time = datetime.now(self.timezone) + timedelta(minutes=timeout_min)
            self.scheduler.add_job(
                self.send_standup_summary,
                trigger='date',
                run_date=summary_time,
                id='standup_summary_job',
                replace_existing=True
            )
            logger.info(f"Scheduled standup status summary in {timeout_min} minutes")
            
        except Exception as e:
            logger.error(f"Error sending daily standup: {e}")
    
    async def send_standup_summary(self):
        """Send a summary of standup submissions, late submissions, and non-submissions."""
        if not self.channel_id:
            logger.warning("No channel ID set. Cannot send standup summary.")
            return
            
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Channel {self.channel_id} not found.")
                return

            role_name = self.database.get_config('standup_role_name') or os.getenv('STANDUP_ROLE') or 'intern'
            developer_role = None
            if channel.guild:
                developer_role = discord.utils.get(channel.guild.roles, name=role_name)
                if not developer_role:
                    developer_role = discord.utils.get(channel.guild.roles, name=role_name.lower())
                if not developer_role:
                    developer_role = discord.utils.get(channel.guild.roles, name=role_name.capitalize())

            if not developer_role:
                logger.warning(f"Role '{role_name}' not found. Cannot compile summary report.")
                return

            # Get target users
            role_members = [m for m in developer_role.members if not m.bot]
            member_ids = {m.id: m for m in role_members}

            # Get today's responses
            from datetime import date
            today_responses = self.database.get_responses_for_date(date.today())
            
            # Retrieve last standup time
            last_standup_str = self.database.get_config('last_standup_time')
            last_standup = datetime.fromisoformat(last_standup_str) if last_standup_str else datetime.now()
            
            # Configured timeout
            timeout_min = int(self.database.get_config('standup_timeout_minutes') or os.getenv('STANDUP_TIMEOUT_MINUTES') or '30')

            submitted_ontime = []
            submitted_late = []
            not_submitted = []

            # Map responses by user_id
            responses_by_user = {r['user_id']: r for r in today_responses}

            for member_id, member in member_ids.items():
                if member_id in responses_by_user:
                    resp = responses_by_user[member_id]
                    # Parse created_at to compare
                    created_at = datetime.fromisoformat(resp['created_at'].replace('Z', '+00:00')) if isinstance(resp['created_at'], str) else resp['created_at']
                    # Localize created_at if naive
                    if created_at.tzinfo is None:
                        created_at = pytz.UTC.localize(created_at)
                    
                    # Localize last_standup if naive
                    last_standup_tz = last_standup
                    if last_standup_tz.tzinfo is None:
                        last_standup_tz = pytz.UTC.localize(last_standup_tz)
                    
                    time_diff = (created_at - last_standup_tz).total_seconds() / 60
                    if time_diff > timeout_min:
                        submitted_late.append((member, resp))
                    else:
                        submitted_ontime.append((member, resp))
                else:
                    not_submitted.append(member)

            # Build embed
            embed = discord.Embed(
                title=f"📊 Daily Standup Status Summary ({timeout_min}-Min Check-in)",
                description=f"Status of standup submissions for {date.today().strftime('%Y-%m-%d')}.",
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )

            # On-time submissions section
            if submitted_ontime:
                ontime_text = ""
                for member, resp in submitted_ontime:
                    ontime_text += f"**{member.display_name}**:\n"
                    if resp.get('today_work'):
                        ontime_text += f"- Today: {resp['today_work']}\n"
                    if resp.get('tomorrow_commitment'):
                        ontime_text += f"- Tomorrow: {resp['tomorrow_commitment']}\n"
                embed.add_field(name=f"✅ Submitted On-Time ({len(submitted_ontime)})", value=ontime_text[:1024], inline=False)
            else:
                embed.add_field(name="✅ Submitted On-Time (0)", value="No on-time submissions.", inline=False)

            # Late submissions section
            if submitted_late:
                late_text = ""
                for member, resp in submitted_late:
                    late_text += f"**{member.display_name}**:\n"
                    if resp.get('today_work'):
                        late_text += f"- Today: {resp['today_work']}\n"
                    if resp.get('tomorrow_commitment'):
                        late_text += f"- Tomorrow: {resp['tomorrow_commitment']}\n"
                embed.add_field(name=f"⚠️ Submitted Late ({len(submitted_late)})", value=late_text[:1024], inline=False)

            # Not submitted section
            if not_submitted:
                unsubmitted_names = ", ".join([f"[@{m.display_name}](https://discord.com/users/{m.id})" for m in not_submitted])
                embed.add_field(name=f"⏳ Pending Submissions ({len(not_submitted)})", value=unsubmitted_names[:1024], inline=False)
            else:
                embed.add_field(name="⏳ Pending Submissions (0)", value="Everyone has submitted!", inline=False)

            await channel.send(embed=embed)
            logger.info("Sent daily standup status summary report.")

        except Exception as e:
            logger.error(f"Error compiling standup summary: {e}")

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
                    # Fetch user dynamically
                    user = self.bot.get_user(user_id)
                    if not user:
                        try:
                            user = await self.bot.fetch_user(user_id)
                        except Exception:
                            pass
                            
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
                    
                    if user:
                        await user.send(embed=embed)
                        logger.info(f"Sent DM follow-up to user {username} for commitment: {commitment_text}")
                        # Mark follow-up as sent
                        self.database.mark_follow_up_sent(commitment_id, datetime.now().date())
                    else:
                        logger.warning(f"Could not send DM follow-up to user {username} (user object not resolvable). Skipping fallback to channel.")
                    
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
        
        # Get configured days (e.g., 'tue,wed,thu,fri,sat')
        days = self.database.get_config('standup_days') or os.getenv('STANDUP_DAYS') or 'mon,tue,wed,thu,fri,sat,sun'
        days = days.lower().strip()
        
        # Schedule daily standup with timezone and days filter
        self.scheduler.add_job(
            self.send_daily_standup,
            trigger=CronTrigger(day_of_week=days, hour=hour, minute=minute, timezone=self.timezone),
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
            trigger=CronTrigger(day_of_week=days, hour=follow_up_hour, minute=follow_up_minute, timezone=self.timezone),
            id='follow_ups',
            name='Follow-up Messages',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        tz_name = self.timezone.zone if hasattr(self.timezone, 'zone') else str(self.timezone)
        logger.info(f"Scheduler started. Standup at {hour:02d}:{minute:02d} on ({days}), follow-ups at {follow_up_hour:02d}:{follow_up_minute:02d} ({tz_name})")
    
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

