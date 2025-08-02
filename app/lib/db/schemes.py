from enum import Enum, IntEnum

from tortoise import fields, models


class PlatformEnum(str, Enum):
    STEAM = "steam"
    PSN = "playstation"
    XBOX = "xbox"


class CommandEnum(str, Enum):
    SYNC_GUILD = "sync_guild"
    RANK_LINK = "rank_link"
    REMATCH_FORM = "rematch_form"
    LOAD_PERSISTENT_VIEW = "load_persistent_view"
    SET_LOG_CHANNEL = "set_log_channel"


class RankLinkEnum(IntEnum):
    BRONZO = 0
    ARGENTO = 1
    ORO = 2
    PLATINO = 3
    DIAMANTE = 4
    ESPERTO = 5
    ELITE = 6


class PersistentViewEnum(str, Enum):
    REMATCH_FORM = "rematch_form"


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
    platform = fields.CharEnumField(PlatformEnum, null=False, max_length=20)
    platform_id = fields.CharField(max_length=255, null=False)
    rematch_display_name = fields.CharField(max_length=255, null=False)
    cached_rank = fields.IntEnumField(RankLinkEnum)
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
        table = "command_permission"
        unique_together = (("guild_id", "command", "role_id"),)


class PersistentViews(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    view_name = fields.CharEnumField(PersistentViewEnum, null=False, max_length=50)
    guild_id = fields.ForeignKeyField("models.GuildSchema", related_name="persistent_views",
                                      on_delete=fields.CASCADE, null=False)
    channel_id = fields.BigIntField(null=False)
    message_id = fields.BigIntField(null=False)
