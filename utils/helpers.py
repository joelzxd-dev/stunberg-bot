import re
import discord


def parse_durasi_ke_menit(teks_durasi: str) -> int:
    """Convert duration string (e.g. '2 Hari 3 Jam 15 Menit') to total minutes."""
    hari, jam, menit = 0, 0, 0

    match_hari = re.search(r'(\d+)\s*(?:Hari|Day|Days)', teks_durasi, re.IGNORECASE)
    if match_hari:
        hari = int(match_hari.group(1))

    match_jam = re.search(r'(\d+)\s*(?:Jam|Hour|Hours)', teks_durasi, re.IGNORECASE)
    if match_jam:
        jam = int(match_jam.group(1))

    match_menit = re.search(r'(\d+)\s*(?:Menit|Minute|Minutes)', teks_durasi, re.IGNORECASE)
    if match_menit:
        menit = int(match_menit.group(1))

    return (hari * 24 * 60) + (jam * 60) + menit


def is_admin(interaction: discord.Interaction) -> bool:
    user_roles = [role.name for role in interaction.user.roles]
    return any(role in user_roles for role in interaction.client.config.ROLES_ADMIN)


def can_wd(interaction: discord.Interaction) -> bool:
    user_roles = [role.name for role in interaction.user.roles]
    return any(role in user_roles for role in interaction.client.config.ROLES_WD)
