import asyncio

import orm
import sys
from models import User, Blog, Comment

loop = asyncio.get_event_loop()
async def test():
    await orm.create_pool(loop=loop, user='root', password='', db='test')

    u = User(name='test', email='test@example.com', passwd='1234', image='about:blank')

    await u.save()
    await orm.destory_pool()

loop.run_until_complete(test())
loop.close()
if loop.is_closed():
    sys.exit(0)
