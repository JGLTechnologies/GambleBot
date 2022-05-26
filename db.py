import time
import typing
import sqlite3
import aiosqlite

DB: aiosqlite.Connection


async def setup(db: aiosqlite.Connection):
    global DB
    DB = db


async def get_balance(guild_id: int, member_id: int) -> int:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS balances(
            guild INTEGER,
            member INTEGER,
            balance INTEGER,
            PRIMARY KEY (guild, member)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("SELECT balance FROM balances WHERE guild=? and member=?",
                          (guild_id, member_id)) as cursor:
        bal = await cursor.fetchone()
        if bal is not None:
            return round(bal[0], 2)
        else:
            return 0


async def set_balance(guild_id: int, member_id: int, balance: int) -> None:
    balance = round(balance, 2)
    async with DB.execute("""CREATE TABLE IF NOT EXISTS balances(
            guild INTEGER,
            member INTEGER,
            balance INTEGER,
            PRIMARY KEY (guild, member)
        )"""):
        pass
    await DB.commit()
    try:
        async with DB.execute("INSERT INTO balances (guild,member,balance) VALUES (?,?,?)",
                              (guild_id, member_id, balance)):
            pass
    except sqlite3.IntegrityError:
        async with DB.execute("UPDATE balances SET balance=? WHERE guild=? and member=?",
                              (balance, guild_id, member_id)):
            pass
    finally:
        await DB.commit()


async def set_channel(guild_id: int, channel_id: int, channel_name: str) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS channels(
            guild INTEGER,
            name TEXT,
            id INTEGER,
            PRIMARY KEY (guild, name)
        )"""):
        pass
    await DB.commit()
    try:
        async with DB.execute("INSERT INTO channels (guild,id,name) VALUES (?,?,?)",
                              (guild_id, channel_id, channel_name)):
            pass
    except sqlite3.IntegrityError:
        async with DB.execute("UPDATE channels SET id=? WHERE guild=? and name=?",
                              (channel_id, guild_id, channel_name)):
            pass
    finally:
        await DB.commit()


async def get_channel(guild_id: int, channel_name: str) -> typing.Optional[int]:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS channels(
            guild INTEGER,
            name TEXT,
            id INTEGER,
            PRIMARY KEY (guild, name)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("SELECT id FROM channels WHERE guild=? and name=?",
                          (guild_id, channel_name)) as cursor:
        id = await cursor.fetchone()
        if id is not None:
            return id[0]
        else:
            return None


async def set_tz(guild_id: int, tz: str) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS tz(
            guild INTEGER PRIMARY KEY,
            tz TEXT,
        )"""):
        pass
    await DB.commit()
    try:
        async with DB.execute("INSERT INTO tz (guild,tz) VALUES (?,?)",
                              (guild_id, tz)):
            pass
    except sqlite3.IntegrityError:
        async with DB.execute("UPDATE tz SET tz=? WHERE guild=?",
                              (guild_id,)):
            pass
    finally:
        await DB.commit()


async def get_tz(guild_id: int) -> str:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS tz(
            guild INTEGER PRIMARY KEY,
            tz TEXT,
        )"""):
        pass
    await DB.commit()
    async with DB.execute("SELECT tz FROM tz WHERE guild=?",
                          (guild_id,)) as cursor:
        id = await cursor.fetchone()
    if id is not None:
        return id[0]
    else:
        return "UTC"


async def credit_add(guild_id: int, member_id: int, amount: float, message_id: int,
                     channel_id: int) -> None:
    due_date = time.time() + 3600 * 48
    async with DB.execute("""CREATE TABLE IF NOT EXISTS credit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild INTEGER,
            member INTEGER,
            channel INTEGER,
            message INTEGER,
            amount FLOAT,
            due_date INTEGER
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "INSERT INTO credit (guild,member,amount,due_date,message,channel) VALUES (?,?,?,?,?,?)",
            (guild_id, member_id, amount, due_date, message_id, channel_id)):
        pass
    await DB.commit()


async def add_security(guild_id: int, member_id: int) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS security(
            member INTEGER,
            guild INTEGER,
            last_paid INTEGER,
            PRIMARY KEY (member,guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "INSERT INTO security (guild,member,last_paid) VALUES (?,?,?)",
            (guild_id, member_id, time.time())):
        pass
    await DB.commit()


async def has_security(guild_id: int, member_id: int) -> bool:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS security(
            member INTEGER,
            guild INTEGER,
            last_paid INTEGER,
            PRIMARY KEY (member,guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("SELECT * FROM security WHERE member=? and guild=?", (member_id, guild_id)) as cursor:
        if await cursor.fetchone() is None:
            return False
        else:
            return True


async def remove_security(guild_id: int, member_id: int) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS security(
            member INTEGER,
            guild INTEGER,
            last_paid INTEGER,
            PRIMARY KEY (member,guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("DELETE FROM security WHERE member=? and guild=?", (member_id, guild_id)):
        pass
    await DB.commit()


async def add_business(guild_id: int, member_id: int, name: str) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS business(
            member INTEGER,
            guild INTEGER,
            upgraded INTEGER,
            name TEXT,
            supplies INT,
            product INT,
            PRIMARY KEY (name, member, guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "INSERT INTO business (guild,member,name,upgraded,supplies,product) VALUES (?,?,?,?,?,?)",
            (guild_id, member_id, name, 0, 0, 0)):
        pass
    await DB.commit()


async def has_business(guild_id: int, member_id: int, name: str) -> bool:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS business(
            member INTEGER,
            guild INTEGER,
            upgraded INTEGER,
            name TEXT,
            supplies INT,
            product INT,
            PRIMARY KEY (name, member, guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "SELECT * FROM business WHERE guild=? and member=? and name=?",
            (guild_id, member_id, name)) as cursor:
        if await cursor.fetchone() is None:
            return False
        else:
            return True


async def upgrade_business(guild_id: int, member_id: int, name: str) -> bool:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS business(
            member INTEGER,
            guild INTEGER,
            upgraded INTEGER,
            name TEXT,
            supplies INT,
            product INT,
            PRIMARY KEY (name, member, guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "SELECT * FROM business WHERE guild=? and member=? and name=?",
            (guild_id, member_id, name)) as cursor:
        if await cursor.fetchone() is None:
            return False
        else:
            return True


async def get_business_stats(guild_id: int, member_id: int, name: str) -> tuple:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS business(
            member INTEGER,
            guild INTEGER,
            upgraded INTEGER,
            name TEXT,
            supplies INT,
            product INT,
            PRIMARY KEY (name, member, guild)
        )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "SELECT product,supplies,upgraded FROM business WHERE guild=? and member=? and name=?",
            (guild_id, member_id, name)) as cursor:
        return await cursor.fetchone()


async def update_business_stats(guild_id: int, member_id: int, name: str, product: int, supplies: int,
                                upgraded: int) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS business(
        member INTEGER,
        guild INTEGER,
        upgraded INTEGER,
        name TEXT,
        supplies INT,
        product INT,
        PRIMARY KEY (name, member, guild)
    )"""):
        pass
    await DB.commit()
    async with DB.execute(
            "UPDATE business SET product=?,supplies=?,upgraded=? WHERE guild=? and member=? and name=?",
            (round(product, 2), round(supplies, 2), upgraded, guild_id, member_id, name)):
        await DB.commit()


async def add_role(guild_id: int, role_id: int, price: int) -> bool:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS role_shop(
            guild INTEGER,
            role INTEGER,
            price INTEGER,
            PRIMARY KEY (guild, role)
        )"""):
        pass
    await DB.commit()
    try:
        async with DB.execute("INSERT INTO role_shop (guild,role,price) VALUES (?,?,?)",
                              (guild_id, role_id, price)):
            await DB.commit()
            return True
    except sqlite3.IntegrityError:
        return False


async def remove_role(guild_id: int, role_id: int) -> None:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS role_shop(
            guild INTEGER,
            role INTEGER,
            price INTEGER,
            PRIMARY KEY (guild, role)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("DELETE FROM role_shop WHERE guild = ? and role = ?",
                          (guild_id, role_id)):
        await DB.commit()


async def get_roles(guild_id: int) -> dict:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS role_shop(
            guild INTEGER,
            role INTEGER,
            price INTEGER,
            PRIMARY KEY (guild, role)
        )"""):
        pass
    await DB.commit()
    roles = {}
    async with DB.execute("SELECT role, price FROM role_shop WHERE guild = ?", (guild_id,)) as cursor:
        async for entry in cursor:
            role, price = entry
            roles[role] = price
    return roles


async def get_role_price(guild_id: int, role_id: int) -> typing.Optional[int]:
    async with DB.execute("""CREATE TABLE IF NOT EXISTS role_shop(
            guild INTEGER,
            role INTEGER,
            price INTEGER,
            PRIMARY KEY (guild, role)
        )"""):
        pass
    await DB.commit()
    async with DB.execute("SELECT price FROM role_shop WHERE guild = ? and role = ?", (guild_id, role_id)) as cursor:
        price = await cursor.fetchone()
        if price is not None:
            return price[0]
        return price
