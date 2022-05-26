import contextlib

import disnake
from disnake.ext import commands
from db import set_balance, get_balance, add_role, remove_role, get_role_price, get_roles
from main import int_to_money


class RoleShop(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedInteractionBot = bot

    @commands.guild_only()
    @commands.slash_command(name="role")
    async def role(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @role.sub_command(name="add")
    async def role_add(self, inter: disnake.ApplicationCommandInteraction,
                       role: disnake.Role = commands.Param(description="The role you want to add to the role store"),
                       price: int = commands.Param(description="How much the role will be sold for")):
        if len(await get_roles(inter.guild_id)) >= 30:
            await inter.response.send_message("There can only be 30 roles in the shop.", ephemeral=True)
        elif not await add_role(inter.guild_id, role.id, price):
            await inter.response.send_message("That role is already in the shop.", ephemeral=True)
        else:
            await inter.response.send_message(
                f"@{role.name} has been added to the role shop for {int_to_money(price)}.", ephemeral=True)

    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @role.sub_command(name="remove")
    async def role_remove(self, inter: disnake.ApplicationCommandInteraction,
                          role: disnake.Role = commands.Param(
                              description="The role you want to remove from the role store")):
        if role.id not in await get_roles(inter.guild_id):
            await inter.response.send_message("That role is not in the shop.", ephemeral=True)
        else:
            await remove_role(inter.guild_id, role.id)
            await inter.response.send_message(f"@{role.name} has been removed from the role shop.",
                                              ephemeral=True)

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @role.sub_command(name="shop")
    async def role_shop(self, inter: disnake.ApplicationCommandInteraction):
        roles = await get_roles(inter.guild_id)
        if len(roles) == 0:
            await inter.response.send_message("There are no roles for sale on this server.", ephemeral=True)
            return
        embed = disnake.Embed(title="Role Shop", color=disnake.Color.blurple())
        text = ""
        for role_id in roles:
            role = inter.guild.get_role(role_id)
            if role is None:
                await remove_role(inter.guild_id, role_id)
                continue
            text += f"{role.mention}: {int_to_money(roles[role_id])}\n"
        embed.description = text
        await inter.response.send_message(embed=embed)

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(manage_roles=True, administrator=True)
    @role.sub_command(name="buy")
    async def role_buy(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role = commands.Param(
        description="The role you want to buy")):
        if role in inter.author.roles:
            await inter.response.send_message("You already have this role.", ephemeral=True)
            return
        roles = await get_roles(inter.guild_id)
        if role.id not in roles:
            await inter.response.send_message("That role is not for sale on this server.", ephemeral=True)
            return
        price = roles[role.id]
        bal = await get_balance(inter.guild_id, inter.author.id)
        if price > bal:
            await inter.response.send_message("You cannot afford this role.", ephemeral=True)
            return
        await set_balance(inter.guild_id, inter.author.id, bal - price)
        with contextlib.suppress(disnake.Forbidden, disnake.HTTPException):
            await inter.author.add_roles(role)
        await inter.response.send_message(f"You successfully bought @{role.name} for {int_to_money(price)}.")


def setup(bot):
    bot.add_cog(RoleShop(bot))
