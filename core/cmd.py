# python imports
from datetime import datetime
import logging
import os
import time

import game.pac_man

# idotmatrix imports
from idotmatrix import ConnectionManager
from idotmatrix import Common


class CMD:
    conn = ConnectionManager()
    logging = logging.getLogger("idmgame." + __name__)

    def add_arguments(self, parser):
        # scan
        parser.add_argument(
            "--scan",
            action="store_true",
            help="scans all bluetooth devices in range for iDotMatrix displays",
        )
        # game
        parser.add_argument(
            "--game",
            action="store_true",
            help="run the PAC-MAN Game function from the command line class",
        )
        # time sync
        parser.add_argument(
            "--sync-time",
            action="store_true",
            help="sync time to device",
        )
        # brightness
        parser.add_argument(
            "--set-brightness",
            action="store",
            help="sets the brightness of the screen in percent: range 5..100",
        )

    async def run(self, args):
        self.logging.info("initializing command line")
        address = None
        if args.scan:
            await self.conn.scan()
            quit()
        if args.address:
            self.logging.debug("using --address")
            address = args.address
        elif "IDOTMATRIX_ADDRESS" in os.environ:
            self.logging.debug("using IDOTMATRIX_ADDRESS")
            address = os.environ["IDOTMATRIX_ADDRESS"]
        if address is None:
            self.logging.error("no device address given")
            quit()
        elif str(address).lower() == "auto":
            await self.conn.connectBySearch()
        else:
            await self.conn.connectByAddress(address)
        # arguments which can be run in parallel
        if args.sync_time:
            await self.sync_time(datetime.now().strftime("%d-%m-%Y-%H:%M:%S"))
        if args.set_brightness:
            await self.set_brightness(int(args.set_brightness))
            
        # arguments which cannot run in parallel
        if args.game:
            await self.game()

    async def game(self):
        """Play Game"""
        self.logging.info("starting game of device")
        ## game
        pm = game.pac_man.PacMan()
        await pm.play_matrixman()
        time.sleep(2)

    async def sync_time(self, argument):
        """Synchronize local time to device"""
        self.logging.info("starting to synchronize time")
        try:
            date = datetime.strptime(argument, "%d-%m-%Y-%H:%M:%S")
        except ValueError:
            self.logging.error(
                "wrong format of --set-time: please use dd-mm-YYYY-HH-MM-SS"
            )
            quit()
        await Common().setTime(
            date.year,
            date.month,
            date.day,
            date.hour,
            date.minute,
            date.second,
        )
        time.sleep(2)

    async def set_brightness(self, argument: int) -> None:
        """sets the brightness of the screen"""
        if argument in range(5, 101):
            self.logging.info(f"setting brightness of the screen: {argument}%")
            await Common().setBrightness(argument)
        else:
            self.logging.error("brightness out of range (should be between 5 and 100)")
        time.sleep(2)
