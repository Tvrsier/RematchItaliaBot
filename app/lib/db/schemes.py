from enum import Enum

from tortoise import fields, models


class PlatformEnum(str, Enum):
    STEAM = "steam"
    PSN = "psn"
    XBOX = "xbox"


class Guild(models.Model):
    guild_id = fields.BigIntField(primary_key=True, unique=True)
    name = fields.CharField(max_length=255, null=True)
    icon_has = fields.CharField(max_length=255, null=True)
    owner_id = fields.BigIntField(null=True)
    region = fields.CharField(max_length=255, null=True)
    member_count = fields.IntField(default=0)
    log_chanel_id = fields.BigIntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Member(models.Model):
    discord_id = fields.BigIntField(primary_key=True, unique=True)
    username = fields.CharField(max_length=255, null=True)
    discriminator = fields.CharField(max_length=10, null=True)
    avatar_hash = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_bot = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=False, null=True)


class PlatformLink(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    discord_id = fields.ForeignKeyField("models.Member", related_name="platform_links",
                                        on_delete=fields.CASCADE, null=False)
    platform = fields.CharEnumField(PlatformEnum, null=False, max_length=10)
    platform_id = fields.CharField(max_length=255, null=False)
    cached_rank = fields.CharField(max_length=255, null=True)
    last_checked = fields.DatetimeField(auto_now_add=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Rank(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    guild_id = fields.ForeignKeyField("models.Guild", related_name="ranks",
                                      on_delete=fields.CASCADE, null=False)
    name = fields.CharField(max_length=255, null=True)
    role_id = fields.BigIntField(null=True)
    rank_position = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True, null=True)


class GuildMember(models.Model):
    id = fields.IntField(primary_key=True, unique=True)
    guild_id = fields.ForeignKeyField("models.Guild", related_name="members",
                                        on_delete=fields.CASCADE, null=False)
    discord_id = fields.ForeignKeyField("models.Member", related_name="guild_members",
                                        on_delete=fields.CASCADE, null=False)
    joined_at = fields.DatetimeField(null=True)
    left_at = fields.DatetimeField(null=True)
    guild_name = fields.CharField(max_length=255, null=True)


