import datetime

from discord import Role, Guild, Member, TextChannel, Message

from app.lib.db.schemes import *
from app.logger import logger
from app.rematch_tracker import ProfileResponse


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
    guild_model = await GuildSchema.get_or_none(guild_id=member.guild.id)
    member_model = await MemberSchema.get_or_none(discord_id=member.id)
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
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error("Guild not found in database, cannot add permission.")
        return None, None
    permission, created = await CommandPermissionSchema.get_or_create(
        guild_id=db_guild,
        command=command,
        role_id=role_id
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
        guild_id=db_guild,
        name=rank.name,
        defaults={
            "role_id": role.id,
            "rank_position": rank.value,
            "updated_at": datetime.datetime.now(datetime.UTC)
        }
    )
    if not created:
        updated = False
        if rank_link.role_id != role.id:
            rank_link.role_id = role.id
            updated = True
        if rank_link.rank_position != rank.value:
            rank_link.rank_position = rank.value
            updated = True
        if updated:
            rank_link.updated_at = datetime.datetime.now(datetime.UTC)
            await rank_link.save()
    return rank_link, created


async def get_role(guild: Guild, rank: RankLinkEnum) -> int | None:
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error(f"Guild {guild.name} ({guild.id}) not found in database")
        return None
    rank_obj = await Rank.get_or_none(guild_id = db_guild, name=rank.name)
    if not rank_obj:
        logger.error("Failed to retrieve rank object from database")
        return None
    return rank_obj.role_id

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
        guild_id=guild_db,
        channel_id=channel.id,
        message_id=message.id
    )
    if not created:
        persistent_view.message_id = message.id
        await persistent_view.save()
    return persistent_view


async def get_persistent_views(view_name: PersistentViewEnum) -> list[PersistentViews] | None:
    views = await PersistentViews.filter(view_name=view_name).prefetch_related("guild_id").all()
    if not views:
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


async def create_platform_link(
        member: Member, profile: ProfileResponse
) -> tuple[PlatformLink | None, bool]:
    member_db = await get_member(member)
    if not member_db:
        logger.error(f"Member {member.name} ({member.id}) not found in database.")
        return None, False
    cached_rank = RankLinkEnum(profile["rank"]["current_league"])
    platform = profile["player"]["platform"] if profile["player"]["platform"] != "psn" else "playstation"
    platform_link, created = await PlatformLink.get_or_create(
        discord_id=member_db,
        platform_id=profile["player"]["platform_id"],
        defaults={
            "platform": platform,
            "cached_rank": cached_rank,
            "last_checked": datetime.datetime.now(datetime.UTC),
            "rematch_display_name": profile["player"]["display_name"]
        }
    )
    if not created:
        if platform_link.cached_rank != cached_rank:
            platform_link.cached_rank = cached_rank
            platform_link.last_checked = datetime.datetime.now(datetime.UTC)
            platform_link.rematch_display_name = profile["player"]["display_name"]
            await platform_link.save()
    return platform_link, created


async def update_rank(
        member: Member, cached_rank: RankLinkEnum
) -> PlatformLink | None:
    member_db = await get_member(member)
    if not member_db:
        logger.error(f"Member {member.name} ({member.id}) not found in database.")
        return None
    platform_link = await PlatformLink.get_or_none(discord_id=member_db)
    if not platform_link:
        logger.error(f"No platform link found for member {member.name} ({member.id}).")
        return None
    platform_link.cached_rank = cached_rank
    platform_link.last_checked = datetime.datetime.now(datetime.UTC)
    await platform_link.save()
    logger.info(f"Updated cached rank for member {member.name} ({member.id}) to {cached_rank.name}.")
    return platform_link


async def get_platform_to_update() -> list[PlatformLink]:
    """
    Retrieves a list of platform links where their last checked time is older than 45 minutes.
    :return:
    """
    delay = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=45)
    platform_links = await PlatformLink.filter(last_checked__lt=delay).all()
    #platform_links = await PlatformLink.all()
    if not platform_links:
        logger.info("No platform links found that need updating.")
        return []
    logger.info(f"Found {len(platform_links)} platform links that need updating.")
    return platform_links


async def check_guild_rank(guild: Guild) -> bool:
    """
    Checks if the guild has linked ranks.
    :param guild:
        The guild to check for linked ranks.
    :return:
        True if the guild has linked ranks, False otherwise.
    """
    db_guild = await GuildSchema.get_or_none(guild_id=guild.id)
    if not db_guild:
        logger.error(f"Guild {guild.name} ({guild.id}) not found in database.")
        return False
    ranks = await Rank.filter(guild_id=db_guild).all()
    if not ranks:
        logger.info(f"No ranks linked for guild {guild.name} ({guild.id}).")
        return False
    logger.info(f"Guild {guild.name} ({guild.id}) has {len(ranks)} linked ranks.")
    return True