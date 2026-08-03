"""
Balloon TD entry point.

Run the game with::

    python main.py

The body is deliberately tiny. The real loop lives in :mod:`btd.app` and is
``async``, which is what lets this same file be the entry point for the
browser build compiled by pygbag -- that runtime requires an awaitable entry
point and a loop that yields once per frame. See ``build_web.sh``.
"""

import asyncio

from btd.app import main

asyncio.run(main())
