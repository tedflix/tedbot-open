import asyncio
import datetime
import random
import sqlite3

from enum import IntEnum

# reminder parameters and their indices in the JSON
class ReminderParams(IntEnum):
    REMINDER_ID = 0
    REMINDER_AUTHOR = 1
    REMINDER_CHANNEL_ID = 2
    REMINDER_TIMESTAMP = 3
    REMINDER_MESSAGE = 4

class Reminder:
    def __init__(self, client):
        self.client = client
        self.reminder_tasks = {}

        # SQLite connection
        self.conn = None

        # load existing
        for reminder in self.__get_reminders():
            self.create_reminder_task(*reminder)

    def __get_cursor(self):
        if self.conn is None:
            try:
                self.conn = sqlite3.connect('reminders.db')
                print('INFO: Opened reminders.db')

                cur = self.conn.cursor()

                # stored as string to allow arbitrary precision
                cur.execute('CREATE TABLE IF NOT EXISTS reminders(reminder_id TEXT PRIMARY KEY, reminder_author TEXT, reminder_channel_id TEXT, reminder_timestamp TEXT, reminder_message TEXT)')
                
                cur.close()

            except:
                print('ERROR: Unable to open reminders.db')
        
        if self.conn:
            return self.conn.cursor()
        else:
            return None
    
    def __get_reminders(self, reminder_id=None):
        cursor = self.__get_cursor()
        if reminder_id:
            reminders = cursor.execute(f'SELECT * FROM reminders WHERE reminder_id = "{reminder_id}"').fetchall()
        else:
            reminders = cursor.execute(f'SELECT * FROM reminders').fetchall()
        cursor.close()
        
        def parse_raw(reminder):
            return (
                int(reminder[ReminderParams.REMINDER_ID]), 
                int(reminder[ReminderParams.REMINDER_AUTHOR]), 
                int(reminder[ReminderParams.REMINDER_CHANNEL_ID]), 
                int(reminder[ReminderParams.REMINDER_TIMESTAMP]), 
                    reminder[ReminderParams.REMINDER_MESSAGE]
            )
        
        for i, reminder in enumerate(reminders):
            reminders[i] = parse_raw(reminder)

        return reminders

    def __get_reminder(self, reminder_id):
        reminders = self.__get_reminders(reminder_id)
        return reminders[0] if len(reminders) > 0 else None
    
    async def __get_channel_from_id(self, channel_id):
        # retrieve channel
        channel = self.client.get_channel(channel_id)

        # if not in cache (most likely DM?)
        if channel == None:
            channel = await self.client.fetch_channel(channel_id)

        return channel
    
    def schedule(self, reminder_id, reminder_author, reminder_channel_id, reminder_timestamp, reminder_message):
        # 1 in a morbillion chance of actually running
        while self.__get_reminder(reminder_id) is not None:
            print(f'WARNING: Reminder id {reminder_id} already exists. Generating a new one (THIS WILL BREAK THE REMINDER CONTROLLER)')
            reminder_id = random.randint(2**64, 2 ** 128)

        cursor = self.__get_cursor()
        cursor.execute(f'INSERT INTO reminders (reminder_id, reminder_author, reminder_channel_id, reminder_timestamp, reminder_message) VALUES ("{reminder_id}", "{reminder_author}", "{reminder_channel_id}", "{reminder_timestamp}", "{reminder_message}")')
        self.conn.commit()
        cursor.close()

        self.create_reminder_task(reminder_id, reminder_author, reminder_channel_id, reminder_timestamp, reminder_message)

    def create_reminder_task(self, reminder_id, reminder_author, reminder_channel_id, reminder_timestamp, reminder_message):
        # calculate time
        current_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        remind_in_seconds = reminder_timestamp - current_timestamp

        if remind_in_seconds < 0:
            print('WARN: reminder waiting time less than 0 seconds')
            remind_in_seconds = 0

        async def remind_task():
            try:
                await asyncio.sleep(remind_in_seconds)

                reminder_channel = await self.__get_channel_from_id(reminder_channel_id)
                if reminder_channel != None:
                    while True:
                        try:
                            await reminder_channel.send(reminder_message)
                        except e:
                            # TODO: better way of rescheduling
                            print('ERROR: Could not send reminder message. Retrying in 15 seconds')
                            print(e)
                            await asyncio.sleep(15)
                        else:
                            # success, we can finally remove it
                            await self.__cleanup(reminder_id)
                            break
            except Exception as e:
                print(e)

        task = asyncio.create_task(remind_task())
        self.reminder_tasks[reminder_id] = task

    async def cancel(self, reminder_id, requestor, reply_channel):
        reminder = self.__get_reminder(reminder_id)
        if reminder and requestor == reminder[ReminderParams.REMINDER_AUTHOR]:
            self.reminder_tasks[reminder_id].cancel()
            await reply_channel.send_message(reminder[ReminderParams.REMINDER_MESSAGE] + ' cancelled')
            
            await self.__cleanup(reminder_id)
        
    async def __cleanup(self, reminder_id):
        if reminder_id < 2**64: # discord id most likely
            try:
                reminder = self.__get_reminder(reminder_id)
                reminder_channel = await self.__get_channel_from_id(reminder[ReminderParams.REMINDER_CHANNEL_ID])
                bot_og_message = await reminder_channel.fetch_message(reminder_id)
                await bot_og_message.edit(content=bot_og_message.content, view=None)
            except:
                pass

        self.reminder_tasks.pop(reminder_id)

        cursor = self.__get_cursor()
        cursor.execute(f'DELETE FROM reminders WHERE reminder_id = "{reminder_id}"')
        self.conn.commit()
        cursor.close()

