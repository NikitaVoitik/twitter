import asyncio
import aiosqlite


class Database:
    def __init__(self):
        self.cursor = None
        self.connection = None

    async def connect(self):
        self.connection = await aiosqlite.connect('twitter.db')
        self.cursor = await self.connection.cursor()

    async def close(self):
        await self.connection.close()

    async def create_table(self, name: str, columns: list[str] | None):
        query = f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(columns)})"
        await self.cursor.execute(query)
        await self.connection.commit()

    async def select(self, table_name: str, columns: list[str] | None = '*', condition: str | None = None):
        if columns:
            query = f"SELECT {', '.join(columns)} FROM {table_name}"
        else:
            query = f"SELECT * FROM {table_name}"

        if condition:
            query += f" WHERE {condition}"

        await self.cursor.execute(query)
        res = await self.cursor.fetchall()
        return res

    async def insert(self, table_name: str, values: list, columns: list[str] | None = None):
        columns = f'({", ".join(columns)})' if columns else ''
        placeholders = '?, ' * (len(values) - 1) + '?'
        query = f"INSERT INTO {table_name} {columns} VALUES ({placeholders});"
        #print(query)
        await self.cursor.execute(query, values)
        await self.connection.commit()

    async def update(self, table_name: str, values: list, columns: list, condition: str):
        query = f"UPDATE {table_name} SET "
        for i in range(len(values)):
            query += f"{columns[i]} = '{values[i]}', "
        query = query[:-2]
        query += f" WHERE {condition}"
        #print(query)
        await self.cursor.execute(query)
        await self.connection.commit()

    async def delete_all(self, table_name: str):
        await self.cursor.execute(f"DELETE FROM {table_name}")
        await self.connection.commit()








