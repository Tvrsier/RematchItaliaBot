import datetime
from enum import Enum

from discord import Guild, Member, User
from tortoise import fields, models

from app.logger import logger


class PlatformEnum(str, Enum):
    STEAM = "steam"
    PSN = "psn"
    XBOX = "xbox"


class CommandEnum(str, Enum):
    SYNC_GUILD = "sync_guild"



class GuildSchema(models.Model):
    guild_id = fields.BigIntField(primary_key=True, unique=True)
    name = fields.CharField(max_length=255, null=True)
    icon_hash = fields.CharField(max_length=255, null=True)
    owner_id = fields.BigIntField(null=True)
    log_chanel_id = fields.BigIntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guild"


class MemberSchema(models.Model):
    discord_id = fields.BigIntField(primary_key=True, unique=True)
    username = fields.CharField(max_length=255, null=True)
    discriminator = fields.CharField(max_length=10, null=True)
    avatar_hash = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_bot = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=False, null=True)

    class Meta:
        table = "member"


class PlatformLink(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    discord_id = fields.ForeignKeyField("models.MemberSchema", related_name="platform_links",
                                        on_delete=fields.CASCADE, null=False)
    platform = fields.CharEnumField(PlatformEnum, null=False, max_length=10)
    platform_id = fields.CharField(max_length=255, null=False)
    cached_rank = fields.CharField(max_length=255, null=True)
    last_checked = fields.DatetimeField(auto_now_add=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Rank(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    guild_id = fields.ForeignKeyField("models.GuildSchema", related_name="ranks",
                                      on_delete=fields.CASCADE, null=False)
    name = fields.CharField(max_length=255, null=True)
    role_id = fields.BigIntField(null=True)
    rank_position = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)


class GuildMemberSchema(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    guild_id = fields.ForeignKeyField("models.GuildSchema", related_name="members",
                                        on_delete=fields.CASCADE, null=False)
    discord_id = fields.ForeignKeyField("models.MemberSchema", related_name="guild_members",
                                        on_delete=fields.CASCADE, null=False)
    joined_at = fields.DatetimeField(null=True)
    left_at = fields.DatetimeField(null=True)

    class Meta:
        table = "guildmember"
        unique_together = (("guild_id", "discord_id"),)


class CommandPermissionSchema(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    guild_id = fields.ForeignKeyField("models.GuildSchema", related_name="command_permissions",
                                      on_delete=fields.CASCADE, null=False)
    command = fields.CharEnumField(CommandEnum, null=False, max_length=50)
    role_id = fields.BigIntField(null=False)

    class Meta:
        table="command_permission"
        unique_together = (("guild_id", "command", "role_id"),)



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


async def member_left(discord_user: User, left_at: datetime.datetime, guild_id: int) -> GuildMemberSchema | None:
    guild_member = await GuildMemberSchema.filter(
        guild_id=guild_id,
        discord_id=discord_user.id
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