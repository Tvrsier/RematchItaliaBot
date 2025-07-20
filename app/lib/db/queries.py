from discord import Role, Guild, Member, TextChannel, User, Message
import datetime

from app.logger import logger
from app.lib.db.schemes import *

async def add_or_get_guild(guild: Guild) -> tuple[GuildSchema, bool]:
    db_guild, created = await GuildSchema.get_or_create(
        guild_id=guild.id,
        defaults={
            "name": guild.name,
            "icon_hash": str(guild.icon.url) if guild.icon else None,
            "owner_id": guild.owner_id if guild.owner_id else None,
        }
    )
    if not created and db_guild.name != guild.name:
        db_guild.name = guild.name
        await db_guild.save()
    return db_guild, created


async def add_or_get_member(member: Member) -> tuple[MemberSchema, GuildMemberSchema | None, bool]:
    guild_member_db = None
    db_member, created = await MemberSchema.get_or_create(
        discord_id=member.id,
        defaults={
            "username": member.name,
            "discriminator": member.discriminator,
            "avatar_hash": str(member.avatar.url) if member.avatar else None,
            "is_bot": member.bot,
            "updated_at": datetime.datetime.now(datetime.UTC)
        }
    )
    if not created:
        if (db_member.username != member.name or
                db_member.discriminator != member.discriminator):
            db_member.username = member.name
            db_member.discriminator = member.discriminator
            db_member.avatar_hash = str(member.avatar.url) if member.avatar else None
            db_member.updated_at = datetime.datetime.now(datetime.UTC)
            await db_member.save()
    if created:
        guild_member_db = await add_or_get_guild_member(member)
    return db_member, guild_member_db, created


async def add_or_get_guild_member(member: Member) -> GuildMemberSchema | None:
    guild_model = await GuildSchema.get_or_none(guild_id = member.guild.id)
    member_model = await MemberSchema.get_or_none(discord_id = member.id)
    if guild_model:
        guild_member, created = await GuildMemberSchema.get_or_create(
            guild_id=guild_model,
            discord_id=member_model,
            defaults={"joined_at": member.joined_at or None}
        )
        if not created:
            if guild_member.joined_at != member.joined_at:
                guild_member.joined_at = member.joined_at or None
                await guild_member.save()
        return guild_member
    logger.warn(f"Guild not found for member {member.name}")
    return None


async def member_left(discord_user: Member, left_at: datetime.datetime, guild_id: int) -> GuildMemberSchema | None:
    guild_db = await GuildSchema.get_or_none(guild_id=guild_id)
    if not guild_db:
        logger.error(f"Guild with ID {guild_id} not found in database.")
        return None
    member_db = await MemberSchema.get_or_none(discord_id=discord_user.id)
    if not member_db:
        logger.error(f"Member with ID {discord_user.id} not found in database.")
        return None
    guild_member = await GuildMemberSchema.filter(
        guild_id=guild_db,
        discord_id=member_db
    ).first()
    if guild_member:
        guild_member.left_at = left_at
        await guild_member.save()

    return guild_member


async def add_command_permission(
        guild: Guild, command: CommandEnum, role_id: int
) -> tuple[CommandPermissionSchema | None, bool | None]:
    db_guild = await GuildSchema.get_or_none(guild_id = guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot add permission.")
        return None, None
    permission, created = await CommandPermissionSchema.get_or_create(
        guild_id = db_guild,
        command = command,
        role_id = role_id
    )
    if created:
        logger.info(f"Command permission {command} for role {role_id} added to guild {guild.name}")
        return permission, created
    else:
        logger.info(f"Command permission {command} for role {role_id} already exists in guild {guild.name}")
        return permission, None


async def get_command_permission(guild: Guild, command: CommandEnum) -> list[CommandPermissionSchema]:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot retrieve permissions.")
        return []
    permissions = await CommandPermissionSchema.filter(
        guild_id=db_guild,
        command=command
    ).all()
    return permissions

async def get_command_permissions(guild: Guild) -> list[CommandPermissionSchema]:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot retrieve permissions.")
        return []
    permissions = await CommandPermissionSchema.filter(
        guild_id=db_guild
    ).all()
    return permissions

async def remove_command_permission(
        guild: Guild, command: CommandEnum, role_id: int
) -> bool:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot remove permission.")
        return False
    permission = await CommandPermissionSchema.filter(
        guild_id=db_guild,
        command=command,
        role_id=role_id
    ).first()
    if permission:
        await permission.delete()
        logger.info(f"Command permission {command} for role {role_id} removed from guild {guild.name}")
        return True
    else:
        logger.warning(f"No command permission {command} for role {role_id} found in guild {guild.name}")
        return False

async def set_guild_log_channel(guild: Guild, channel: TextChannel) -> bool:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot set log channel.")
        return False
    db_guild.log_chanel_id = channel.id
    await db_guild.save()
    logger.debug(f"Log channel set to {channel.name} for guild {guild.name}")
    return True


async def link_rank(guild: Guild, role: Role, rank: RankLinkEnum) -> tuple[Rank | None, bool]:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot link rank.")
        return None, False
    rank_link, created = await Rank.get_or_create(
        guild_id = db_guild,
        name=rank.name,
        defaults={
            "role_id": role.id,
            "rank_position": rank.value,
            "updated_at": datetime.datetime.now(datetime.UTC)
        }
    )
    if not created:
        if rank_link.role_id != role.id or rank_link.rank_position != rank.value:
            rank_link.role_id = role.id
            rank_link.rank_position = rank.value
            rank_link.updated_at = datetime.datetime.now(datetime.UTC)
            await rank_link.save()
    return rank_link, created

async def get_guild(guild: Guild) -> GuildSchema | None:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error(f"Guild {guild.name} ({guild.id}) not found in database.")
        return None
    return db_guild


async def get_member(member: Member) -> MemberSchema | None:
    db_member = await MemberSchema.get_or_none(discord_id=member.id)
    if not db_member:
        logger.error(f"Member {member.name} ({member.id}) not found in database.")
        return None
    return db_member


async def create_persistent_view(
    view_name: PersistentViewEnum, guild: Guild, channel: TextChannel, message: Message
) -> PersistentViews:
    guild_db = await GuildSchema.get_or_none(guild_id=guild.id)
    persistent_view, created = await PersistentViews.get_or_create(
        view_name=view_name,
        guild_id = guild_db,
        channel_id = channel.id,
        message_id = message.id
    )
    if not created:
        persistent_view.message_id = message.id
        await persistent_view.save()
    return persistent_view

async def get_persistent_views(view_name: PersistentViewEnum) -> list[PersistentViews] | None:
    views = await PersistentViews.filter(view_name=view_name).prefetch_related("guild_id").all()
    if not views:
        logger.debug(f"No persistent views found for {view_name.name}.")
        return None
    return views

async def remove_persistent_view(
    view_name: PersistentViewEnum, message_id: int
) -> bool:
    persistent_view = await PersistentViews.filter(
        view_name=view_name,
        message_id=message_id
    ).first()
    if persistent_view:
        await persistent_view.delete()
        logger.info(f"Persistent view {view_name.name} with message ID {message_id} removed.")
        return True
    else:
        logger.warning(f"No persistent view {view_name.name} with message ID {message_id} found.")
        return False


