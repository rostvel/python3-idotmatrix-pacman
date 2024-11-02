import random
import time
import keyboard  # using module keyboard

from idotmatrix import FullscreenColor
from idotmatrix import Graffiti
from idotmatrix import Clock
from idotmatrix import Image
from idotmatrix import Scoreboard

from game.board import board
from game.dots import *
from game.player import Player

# Constants
TRUE  = 1
FALSE = 0

# Enemy mode types
SCATTER = 0
CHASE   = 1
FRIGHT  = 2

MAX_DOT_LVL = 244

behaviors = [
    7000, 20000, 7000, 20000, 5000, 20000, 10, 0  # Trailing zero is a hack
]

# Color definitions
BLUE   = 0
YELLOW = 1
RED    = 2
PINK   = 3
ORANGE = 4
CYAN   = 5
BLACK  = 6
GREY   = 7
WHITE  = 8
LAVENDAR = 9
GREEN  = 10

# Color values
colors = [
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 0),      # Red
    (255, 153, 204),  # Pink
    (255, 102, 0),    # Orange
    (0, 255, 255),    # Cyan
    (0, 0, 0),        # Black
    (64, 64, 64),     # Grey
    (255, 255, 255),  # White
    (196, 64, 255),   # Lavendar
    (0, 255, 0)       # Green
]

# Enemy Data
playerColor = [YELLOW, RED, PINK, CYAN, ORANGE]
startingX = [15, 15, 17, 17, 14]
startingY = [26, 14, 16, 17, 17]
# Player doesn't have scatter so 0 index is retreat coordinates
scatterX = [15, 27, 4, 2, 29]
scatterY = [14, 0, 0, 35, 35]

"""TODO: Level change: Player and enemy speed changes
    100% = 10/second = 100ms ticks
    17ms speed penalty per dot gobbled
    50ms speed penalty for power pellet

                player  fright  enemy   fright  tunnel
    Level 1     80% 125 90% 111 75% 133 50% 200 40% 250
    Level 2-4   90% 111 95% 105 85% 118 55% 182 45% 222
    Level 5-20      100     100 95% 105 60% 167 50% 200
    Level 21+   90% 111     111 95% 105     105 50% 200
"""

"""Speed is indexed as follows: [(level * 5) + <index>]
    <index>: Player, Enemy, PlayerFright, EnemyFright, EnemyTunnel"""
speed = [
    125, 133, 111, 200, 250,
    111, 118, 105, 182, 222,
    100, 105, 100, 167, 200,
    111, 105, 111, 105, 200
]

dotLimitTable = [0, 0, 0, 30, 60, 0, 0, 0, 0, 50]

# Index values for the speed array
SPEEDPLAYER = 0
SPEEDENEMY = 1
SPEEDPLAYERFRIGHT = 2
SPEEDENEMYFRIGHT = 3
SPEEDENEMYTUNNEL = 4

# Directions of travel
UP      = 0
DOWN    = 1
LEFT    = 2
RIGHT   = 3
ESCAPE  = 4
NOINPUT = 5
BUTTON  = 6

# PowerPixel rows and columns
PP1COL = 3
PP2COL = 28
PP1ROW = 6
PP2ROW = 26

EATENEMYBASE = 20       # The least you'll get for eating enemy
EATPOWERDOT  = 4        # Power dot
EATSIMPLEDOT = 1        # Simple dot

class PacMan:
    # Game State Variables
    enemyMode = SCATTER     # SCATTER, CHASE, or FRIGHT
    gameRunning = FALSE     # TRUE unless game over: FALSE
    frightTimer = 0         # Counts down to end of FRIGHT mode
    lastBehavior = 0        # Saves mode before entering FRIGHT
    dotTimer = 0            # Countdown to release enemies if dots not eaten
    level = 0               # Which self.level is currently running (zero index)
    nextDir = 0             # Stores the newest direction input from user
    powerPixelColor = 0     # Used to facilitate flashing of the powerPixels
    lives = 3               # Remaining extra self.lives (example value)
    behaviorTicks = 0       # Timer for switch from scatter to chase
    behaviorIndex = 0       # Index that tracks timer values for mode changes
    useGlobalDot = FALSE    # FALSE = use enemy dot counters, TRUE = use self.globalDotCounter
    globalDotCounter = 0    # After death, release ghosts on dots eaten: 7/17/32
    score = 0               # Keeps score
    eatNextEnemyscore = EATENEMYBASE  # Doubles with each enemy eaten

    dotTracker = [0] * 36  # Initialize a list with 36 elements, all set to 0

    myGuy  = Player()
    enemy1 = Player()
    enemy2 = Player()
    enemy3 = Player()
    enemy4 = Player()

    def displayLatch(self):
        return

    def init_display(self):
        return

    def init_control(self):
        return

    async def display_game_screen(self):
        ## diy image (png)
        await Image().setMode(1)
        await Image().uploadUnprocessed("./images/game_screen.png")

    async def display_control_screen(self):
        ## diy image (png)
        await Image().setMode(1)
        await Image().uploadUnprocessed("./images/control.png")

    async def display_game_over(self):
        ## diy image (png)
        await Image().setMode(1)
        await Image().uploadUnprocessed("./images/game_over.png")

    async def display_close(self):
        ## clock
        await Clock().setTimeIndicator(True)
        await Clock().setMode(0, True, True)
        quit()

    def get_control(self):
        if keyboard.is_pressed('down'):
            return DOWN
        elif keyboard.is_pressed('up'):
            return UP
        elif keyboard.is_pressed('left'):
            return LEFT
        elif keyboard.is_pressed('right'):
            return RIGHT
        elif keyboard.is_pressed('esc'):
            return ESCAPE
        elif keyboard.is_pressed('r'):
            return BUTTON

        return NOINPUT

    async def displayPixel(self, x, y, ncolor):
        await Graffiti().setPixel(colors[ncolor][0], colors[ncolor][1], colors[ncolor][2], x, y-2)

    async def display_clear(self, ncolor):
        await FullscreenColor().setMode(colors[ncolor][0], colors[ncolor][1], colors[ncolor][2])

    def can_move(self, nextX, nextY):
        # Check if the next position is valid
        if board[nextY] & (1 << (31 - nextX)):
            return FALSE
        return TRUE

    def gobble_count(self):
        self.myGuy.dotCount += 1
        if self.myGuy.dotCount == MAX_DOT_LVL:
            # All dots have been eaten, time for next self.level
            self.gameRunning = FALSE
            return

        self.dotTimer = 0  # Reset timer

        if self.useGlobalDot:
            if self.globalDotCounter <= 32:
                self.globalDotCounter += 1
        else:
            if not self.enemy1.inPlay:
                self.enemy1.dotCount += 1
                return
            if not self.enemy2.inPlay:
                self.enemy2.dotCount += 1
                return
            if not self.enemy3.inPlay:
                self.enemy3.dotCount += 1
                return
            if not self.enemy4.inPlay:
                self.enemy4.dotCount += 1
                return

        # Handle global dot counter logic here...

    def is_pixel(self, x, y):
        return bool(self.dotTracker[y] & (1 << (31 - x)))

    def is_power_pixel(self, x, y):
        if (x == PP1COL or x == PP2COL) and (y == PP1ROW or y == PP2ROW):
            return TRUE
        return FALSE

    async def move_player(self, pawn):
        test_x = pawn.x
        test_y = pawn.y

        if pawn.color == GREEN and pawn.x == scatterX[0] and pawn.y == scatterY[0]:
            # Gobbled enemy has made it home, put it in the house
            await self.displayPixel(pawn.x, pawn.y, BLACK)
            self.enterHouse(pawn)
            await self.displayPixel(pawn.x, pawn.y, pawn.color)
            self.displayLatch()  # redraws display (if necessary)
            return
        else:
            if pawn.travelDir == UP:
                test_y -= 1
            elif pawn.travelDir == DOWN:
                test_y += 1
            elif pawn.travelDir == LEFT:
                test_x -= 1
            elif pawn.travelDir == RIGHT:
                test_x += 1

        # Is next space unoccupied?
        if self.can_move(test_x, test_y):
            # Erase player at current spot (redraw dot if necessary)
            if self.is_pixel(pawn.x, pawn.y):
                if self.is_power_pixel(pawn.x, pawn.y):
                    await self.displayPixel(pawn.x, pawn.y, WHITE)
                else:
                    await self.displayPixel(pawn.x, pawn.y, GREY)
            else:
                await self.displayPixel(pawn.x, pawn.y, BLACK)

            # Tunnel Tests
            if test_y == 17:
                if test_x == 1:
                    test_x = 29  # Warp left to right
                elif test_x == 30:
                    test_x = 2  # Warp right to left
                elif pawn.id and pawn.travelDir == LEFT:
                    if test_x == 7:
                        pawn.speedMode = SPEEDENEMYTUNNEL  # Slow down
                    if test_x == 23:
                        # Speed Up
                        pawn.speedMode = SPEEDENEMY if self.enemyMode != FRIGHT else SPEEDENEMYFRIGHT
                elif pawn.id and pawn.travelDir == RIGHT:
                    if test_x == 24:
                        pawn.speedMode = SPEEDENEMYTUNNEL  # Slow down
                    if test_x == 8:
                        # Speed Up
                        pawn.speedMode = SPEEDENEMY if self.enemyMode != FRIGHT else SPEEDENEMYFRIGHT

            # Increment player position
            pawn.x = test_x
            pawn.y = test_y
            # Redraw player at new spot
            await self.displayPixel(pawn.x, pawn.y, pawn.color)

            # Gobble the dot
            if pawn == self.myGuy and self.is_pixel(pawn.x, pawn.y):
                self.dotTracker[pawn.y] &= ~(1 << (31 - pawn.x))  # Remove dot from the board
                self.score += EATSIMPLEDOT
                await self.draw_score()
                self.gobble_count()  # Increment dot counts

                # There is a speed hit for each dot
                pawn.speed += 17  # ~1/60th of a second
                if self.is_power_pixel(pawn.x, pawn.y):
                    # Additional speed hit for PowerPixels
                    pawn.speed += 33  # ~2/60th of a second
                    # Additional points for gobbling this powerPixel
                    self.score += EATPOWERDOT
                    await self.draw_score()

                    # ---Switch to Fright mode---
                    # Save last mode but don't if last mode was FRIGHT
                    if self.enemyMode != FRIGHT:
                        self.lastBehavior = self.enemyMode
                    self.enemyMode = FRIGHT
                    self.frightTimer = 6000  # TODO: This should change with each self.level
                    # Reset eatNextEnemyscore to default
                    self.eatNextEnemyscore = EATENEMYBASE

                    self.change_behavior(self.myGuy, self.enemyMode)
                    self.change_behavior(self.enemy1, self.enemyMode)
                    self.change_behavior(self.enemy2, self.enemyMode)
                    self.change_behavior(self.enemy3, self.enemyMode)
                    self.change_behavior(self.enemy4, self.enemyMode)

        self.displayLatch()  # Redraw display (if necessary)

    def get_distance(self, x, y, targetX, targetY):
        # Takes point and a target point and returns squared distance between them
        hor = abs(x - targetX)
        vert = abs(y - targetY)
        return (hor * hor) + (vert * vert)


    def player_route(self, pawn, next_dir):
        if next_dir == pawn.travelDir:
            return

        test_x = pawn.x
        test_y = pawn.y

        if next_dir == UP:
            test_y -= 1
        elif next_dir == DOWN:
            test_y += 1
        elif next_dir == LEFT:
            test_x -= 1
        elif next_dir == RIGHT:
            test_x += 1

        if self.can_move(test_x, test_y):
            pawn.travelDir = next_dir

    def route_choice(self, pawn):
        #This function is only used for enemies. NEVER for the player
        #TODO: This function works but seems overly complex

        #Does the pawn have a choice of routes right now?
        test_x = pawn.x
        test_y = pawn.y

        # Check for intersections where turning upward is forbidden
        if (test_x == 14 or test_x == 17) and (test_y == 14 or test_y == 26) and pawn.travelDir != DOWN:
            return

        # Set high initial distances
        route1, route2, route3 = 6000, 6000, 6000

        # If in FRIGHT mode and not GREEN, choose route randomly
        if self.enemyMode == FRIGHT and pawn.color != GREEN:
            finding_path = TRUE
            while finding_path:
                direction = random.randint(0, 3)
                if direction == UP and pawn.travelDir != DOWN and self.can_move(test_x, test_y - 1):
                    pawn.travelDir = UP
                    finding_path = FALSE
                elif direction == DOWN and pawn.travelDir != UP and self.can_move(test_x, test_y + 1):
                    pawn.travelDir = DOWN
                    finding_path = FALSE
                elif direction == LEFT and pawn.travelDir != RIGHT and self.can_move(test_x - 1, test_y):
                    pawn.travelDir = LEFT
                    finding_path = FALSE
                elif direction == RIGHT and pawn.travelDir != LEFT and self.can_move(test_x + 1, test_y):
                    pawn.travelDir = RIGHT
                    finding_path = FALSE
            return

        # Calculate routes based on current travel direction
        if pawn.travelDir == UP:
            if self.can_move(test_x - 1, test_y):
                route1 = self.get_distance(test_x - 1, test_y, pawn.tarX, pawn.tarY)
            if self.can_move(test_x + 1, test_y):
                route2 = self.get_distance(test_x + 1, test_y, pawn.tarX, pawn.tarY)
            if self.can_move(test_x, test_y - 1):
                route3 = self.get_distance(test_x, test_y - 1, pawn.tarX, pawn.tarY)

            if route1 < route2 and route1 < route3:
                pawn.travelDir = LEFT
            elif route2 < route1 and route2 < route3:
                pawn.travelDir = RIGHT

        elif pawn.travelDir == DOWN:
            if self.can_move(test_x - 1, test_y):
                route1 = self.get_distance(test_x - 1, test_y, pawn.tarX, pawn.tarY)
            if self.can_move(test_x + 1, test_y):
                route2 = self.get_distance(test_x + 1, test_y, pawn.tarX, pawn.tarY)
            if self.can_move(test_x, test_y + 1):
                route3 = self.get_distance(test_x, test_y + 1, pawn.tarX, pawn.tarY)

            if route1 < route2 and route1 < route3:
                pawn.travelDir = LEFT
            elif route2 < route1 and route2 < route3:
                pawn.travelDir = RIGHT

        elif pawn.travelDir == LEFT:
            if self.can_move(test_x, test_y - 1):
                route1 = self.get_distance(test_x, test_y - 1, pawn.tarX, pawn.tarY)
            if self.can_move(test_x, test_y + 1):
                route2 = self.get_distance(test_x, test_y + 1, pawn.tarX, pawn.tarY)
            if self.can_move(test_x - 1, test_y):
                route3 = self.get_distance(test_x - 1, test_y, pawn.tarX, pawn.tarY)

            if route1 < route2 and route1 < route3:
                pawn.travelDir = UP
            elif route2 < route1 and route2 < route3:
                pawn.travelDir = DOWN

        elif pawn.travelDir == RIGHT:
            if self.can_move(test_x, test_y - 1):
                route1 = self.get_distance(test_x, test_y - 1, pawn.tarX, pawn.tarY)
            if self.can_move(test_x, test_y + 1):
                route2 = self.get_distance(test_x, test_y + 1, pawn.tarX, pawn.tarY)
            if self.can_move(test_x + 1, test_y):
                route3 = self.get_distance(test_x + 1, test_y, pawn.tarX, pawn.tarY)

            if route1 < route2 and route1 < route3:
                pawn.travelDir = UP
            elif route2 < route1 and route2 < route3:
                pawn.travelDir = DOWN

    def set_target(self, pawn):
        if self.enemyMode != CHASE or pawn.color == GREEN:
            return

        if pawn.id == 1:
            # self.enemy1 targets self.myGuy
            self.enemy1.tarX = self.myGuy.x
            self.enemy1.tarY = self.myGuy.y

        elif pawn.id == 2:
            # self.enemy2 targets based on self.myGuy's direction
            if self.myGuy.travelDir == UP:
                self.enemy2.tarY = max(0, self.myGuy.y - 4)
                self.enemy2.tarX = max(0, self.myGuy.x - 4)
            elif self.myGuy.travelDir == DOWN:
                self.enemy2.tarY = min(35, self.myGuy.y + 4)
                self.enemy2.tarX = max(0, self.myGuy.x - 4)
            elif self.myGuy.travelDir == LEFT:
                self.enemy2.tarX = max(0, self.myGuy.x - 4)
            elif self.myGuy.travelDir == RIGHT:
                self.enemy2.tarX = min(31, self.myGuy.x + 4)

        elif pawn.id == 3:
            # self.enemy3 targets based on the position of self.myGuy and self.enemy1
            temp_x = self.myGuy.x - (self.enemy1.x - self.myGuy.x)
            temp_y = self.myGuy.y - (self.enemy1.y - self.myGuy.y)
            pawn.tarX = max(0, min(31, temp_x))
            pawn.tarY = max(0, min(35, temp_y))

        elif pawn.id == 4:
            # self.enemy4 logic
            if self.get_distance(self.enemy4.x, self.enemy4.y, self.myGuy.x, self.myGuy.y) > 64:
                self.enemy4.tarX = self.myGuy.x
                self.enemy4.tarY = self.myGuy.y
            else:
                self.enemy4.tarX = scatterX[self.enemy4.id]
                self.enemy4.tarY = scatterY[self.enemy4.id]

    async def check_dots(self, pawn, force):
        if pawn.inPlay:
            return
        release_enemy = force or (self.useGlobalDot and ((pawn.id == 2 and self.globalDotCounter >= 7) or
                                                        (pawn.id == 3 and self.globalDotCounter >= 17) or
                                                        (pawn.id == 4 and self.globalDotCounter >= 32)))

        if release_enemy or pawn.dotCount >= pawn.dotLimit:
            await self.displayPixel(pawn.x, pawn.y, BLACK)  # Erase current location
            pawn.x = 18
            pawn.y = 14
            await self.displayPixel(pawn.x, pawn.y, pawn.color)  # Draw new location
            self.displayLatch()  # Redraw display
            pawn.inPlay = TRUE
            pawn.travelDir = LEFT

    def setup_player(self, pawn, new_id):
        pawn.id = new_id
        pawn.x = startingX[pawn.id]
        pawn.y = startingY[pawn.id]
        self.change_speed(pawn, SPEEDENEMY if new_id else SPEEDPLAYER)
        pawn.travelDir = LEFT
        pawn.color = playerColor[pawn.id]
        pawn.tarX = scatterX[pawn.id]
        pawn.tarY = scatterY[pawn.id]
        pawn.dotCount = 0
        pawn.dotLimit = 0 if self.level >= 2 else dotLimitTable[(self.level * 5) + pawn.id]
        pawn.inPlay = FALSE

    def setup_player_after_death(self, pawn):
        pawn.x = startingX[pawn.id]
        pawn.y = startingY[pawn.id]
        self.change_speed(pawn, SPEEDENEMY if pawn.id else SPEEDPLAYER)
        pawn.travelDir = LEFT
        pawn.color = playerColor[pawn.id]
        pawn.tarX = scatterX[pawn.id]
        pawn.tarY = scatterY[pawn.id]
        pawn.inPlay = FALSE

    def reverse_dir(self, pawn):
        if pawn.travelDir == UP:
            pawn.travelDir = DOWN
        elif pawn.travelDir == DOWN:
            pawn.travelDir = UP
        elif pawn.travelDir == LEFT:
            pawn.travelDir = RIGHT
        elif pawn.travelDir == RIGHT:
            pawn.travelDir = LEFT

    def set_scatter_target(self, pawn):
        pawn.tarX = scatterX[pawn.id]
        pawn.tarY = scatterY[pawn.id]

    def change_speed(self, pawn, index):
        if self.level == 0:
            row_offset = 0
        elif 1 <= self.level <= 3:
            row_offset = 5
        elif 4 <= self.level <= 19:
            row_offset = 10
        else:
            row_offset = 15

        pawn.speed = speed[index + row_offset]

    def change_behavior(self, pawn, mode):
        #GREEN means enemy is in retreat mode; do nothing
        if pawn.color == GREEN:
            return

        if self.enemyMode != FRIGHT and pawn.id:
            #Enemies should reverse current direction when modes change
            #Unless coming out of FRIGHT mode
            self.reverse_dir(pawn)
            
            #Not FRIGHT mode so revive natural color
            pawn.color = playerColor[pawn.id]

        if mode == SCATTER:
            if pawn.id == 0:
                pawn.speedMode = SPEEDPLAYER
            else:
                pawn.speedMode = SPEEDENEMY
                self.set_scatter_target(pawn)

        elif mode == CHASE:
            if pawn.id == 0:
                pawn.speedMode = SPEEDPLAYER
            else:
                pawn.speedMode = SPEEDENEMY

        elif mode == FRIGHT:
            if pawn.id == 0:
                pawn.speedMode = SPEEDPLAYERFRIGHT
            else:
                pawn.speedMode = SPEEDENEMYFRIGHT
                pawn.color = LAVENDAR

    def was_eaten(self, player, pawn):
        return pawn.color != GREEN and (player.x == pawn.x and player.y == pawn.y)

    async def perform_retreat(self, pawn):
        #TODO: Each player should have enemyMode setting and it should be checked here
        #Add to the score and double the next score
        self.score += self.eatNextEnemyscore
        self.eatNextEnemyscore *= 2
        await self.draw_score()

        pawn.color = GREEN
        pawn.tarX = scatterX[0]
        pawn.tarY = scatterY[0]

    def enterHouse(self, pawn):
        #TODO: Each player should have enemyMode setting and it should be checked here
        pawn.color = playerColor[pawn.id]
        pawn.x = scatterX[0]
        pawn.y = scatterY[0] + 2
        pawn.tarX = scatterX[pawn.id]
        pawn.tarY = scatterY[pawn.id]
        pawn.inPlay = FALSE

    async def check_eaten(self):
        if self.enemyMode != FRIGHT:
            for enemy in [self.enemy1, self.enemy2, self.enemy3, self.enemy4]:
                if self.was_eaten(self.myGuy, enemy):
                    # Game over
                    self.gameRunning = FALSE
                    if self.lives == 0:
                        await self.display_game_over()
                    return
        else:
            # Enemies should change color and go home when eaten
            for enemy in [self.enemy1, self.enemy2, self.enemy3, self.enemy4]:
                if self.was_eaten(self.myGuy, enemy) and enemy.color != GREEN:
                    await self.perform_retreat(enemy)

    async def flash_enemy(self, pawn, color):
        if pawn.color in [WHITE, LAVENDAR]:
            pawn.color = color
            await self.displayPixel(pawn.x, pawn.y, pawn.color)
            self.displayLatch()

    async def expired_dotTimer(self):
        self.dotTimer = 0  # Reset timer

        for enemy in [self.enemy1, self.enemy2, self.enemy3, self.enemy4]:
            if not enemy.inPlay:
                await self.check_dots(enemy, TRUE)
                return

    async def enemy_tick(self, pawn):
        pawn.speed -= 1
        if pawn.speed <= 0:
            self.set_target(pawn)
            self.route_choice(pawn)
            await self.move_player(pawn)
            await self.check_eaten()
            self.change_speed(pawn, pawn.speedMode)

    async def player_tick(self, pawn):
        pawn.speed -= 1
        if pawn.speed <= 0:
            self.player_route(self.myGuy, self.nextDir)
            self.change_speed(pawn, pawn.speedMode)
            await self.move_player(self.myGuy)
            await self.check_eaten()

    async def setup_level(self):
        # Redraw self.level
        await Image().setMode(1)
        if self.score == 0:
            await Image().uploadUnprocessed("./images/labyrinth_full.png")
        else:
            await Image().uploadUnprocessed("./images/labyrinth.png")
        time.sleep(1.2)
        
        """ If labyrinth image not exist or we want to redraw by pixels
        for i in range(2, 34):
            for j in range(32):
                if board[i] & (1 << (31 - j)):
                    await self.displayPixel(j, i, BLUE)
        """
        
        # Draw the dots
        for i in range(2, 34):
            for j in range(32):
                if self.dotTracker[i] & (1 << (31 - j)):
                    color = WHITE if self.is_power_pixel(j, i) else GREY
                    await self.displayPixel(j, i, color)
        
        # Draw the player
        await self.displayPixel(self.myGuy.x, self.myGuy.y, self.myGuy.color)
        await self.draw_lives()
        self.displayLatch()

    def setup_defaults(self):
        self.refresh_dotTracker()
        self.setup_player(self.myGuy, 0)
        self.setup_player(self.enemy1, 1)
        self.enemy1.inPlay = TRUE  # self.enemy1 always starts in play
        self.setup_player(self.enemy2, 2)
        self.setup_player(self.enemy3, 3)
        self.setup_player(self.enemy4, 4)
        self.enemyMode = SCATTER
        self.useGlobalDot = FALSE

    def death_restart(self):
        self.behaviorIndex = 0
        self.behaviorTicks = 0
        self.setup_player_after_death(self.myGuy)
        self.setup_player_after_death(self.enemy1)
        self.enemy1.inPlay = TRUE
        self.setup_player_after_death(self.enemy2)
        self.setup_player_after_death(self.enemy3)
        self.setup_player_after_death(self.enemy4)
        self.enemyMode = SCATTER
        self.useGlobalDot = TRUE

    def refresh_dotTracker(self):
        for i in range(36):
            self.dotTracker[i] = 0x00000000
        for j in range(2, 34):
            self.dotTracker[j] = dots[j]

    async def draw_lives(self):
        for i in range(self.lives):
            await self.displayPixel(0, 33 - i, YELLOW)

    async def draw_score(self):
        #Uncomment next line if we want to accelerate game (for a big score)!
        #return
        
        #Score as binary system
        larger_dgt = 0
        for i in range(20):
            if self.score & (1 << i):
                larger_dgt = i
        for i in range(larger_dgt+1):
            if self.score & (1 << i):
                await self.displayPixel(31, 33 - i, WHITE)
            else:
                await self.displayPixel(31, 33 - i, BLACK)

    async def play_matrixman(self):
        self.level = 0
        self.lives = 2  # Including the one in play

        await self.display_game_screen()
        time.sleep(2.6)
        await self.display_control_screen()
        time.sleep(3.7)
        await Scoreboard().setMode(self.level+1, self.lives+1)
        time.sleep(2)

        self.setup_defaults()
        self.init_display()
        self.init_control()
        await self.setup_level()  # Show everything on the display

        programRunning = TRUE

        self.gameRunning = TRUE
        self.behaviorTicks = 0
        self.behaviorIndex = 0
        self.nextDir = RIGHT
        self.dotTimer = 0
        self.score = 0

        while programRunning:
            control = self.get_control()
            if control == NOINPUT:
                pass
            elif control == ESCAPE:
                self.gameRunning = FALSE
                programRunning = FALSE
                continue
            elif control == BUTTON:
                if not self.gameRunning:
                    self.gameRunning = TRUE
                    self.behaviorTicks = 0
                    self.behaviorIndex = 0
                    self.nextDir = RIGHT
                    self.dotTimer = 0
                    self.score = 0
                    self.level = 0
                    self.lives = 2  # Including the one in play
                    await Scoreboard().setMode(self.level+1, self.lives+1)
                    time.sleep(2)
                    self.setup_defaults()
                    await self.setup_level()  # Show everything on the display
            else:
                self.nextDir = control

            if self.gameRunning:
                if self.enemyMode == FRIGHT:
                    self.frightTimer -= 1
                    if self.frightTimer <= 1800:
                        if self.frightTimer % 200 == 0:
                            flashColor = WHITE if (self.frightTimer // 200) % 2 else LAVENDAR
                            await self.flash_enemy(self.enemy1, flashColor)
                            await self.flash_enemy(self.enemy2, flashColor)
                            await self.flash_enemy(self.enemy3, flashColor)
                            await self.flash_enemy(self.enemy4, flashColor)

                    if self.frightTimer == 0:
                        self.enemyMode = self.lastBehavior

                    self.change_behavior(self.myGuy, self.enemyMode)
                    self.change_behavior(self.enemy1, self.enemyMode)
                    self.change_behavior(self.enemy2, self.enemyMode)
                    self.change_behavior(self.enemy3, self.enemyMode)
                    self.change_behavior(self.enemy4, self.enemyMode)
                else:
                    if self.behaviorTicks > behaviors[self.behaviorIndex]:
                        self.behaviorTicks += 1
                        if behaviors[self.behaviorIndex] > 0:
                            self.behaviorIndex += 1
                            self.behaviorTicks = 0
                            self.enemyMode = CHASE if self.behaviorIndex % 2 else SCATTER
                            self.change_behavior(self.myGuy, self.enemyMode)
                            self.change_behavior(self.enemy1, self.enemyMode)
                            self.change_behavior(self.enemy2, self.enemyMode)
                            self.change_behavior(self.enemy3, self.enemyMode)
                            self.change_behavior(self.enemy4, self.enemyMode)
                    else:
                        self.behaviorTicks += 1

                # Execute game ticks
                if self.gameRunning: await self.enemy_tick(self.enemy1)
                if self.gameRunning: await self.enemy_tick(self.enemy2)
                if self.gameRunning: await self.enemy_tick(self.enemy3)
                if self.gameRunning: await self.enemy_tick(self.enemy4)
                if self.gameRunning: await self.player_tick(self.myGuy)

                # Check dot counters
                await self.check_dots(self.enemy1, FALSE)
                await self.check_dots(self.enemy2, FALSE)
                await self.check_dots(self.enemy3, FALSE)
                await self.check_dots(self.enemy4, FALSE)

                self.dotTimer += 1
                if self.dotTimer >= 4000:  # Change this for higher self.levels
                    await self.expired_dotTimer()

                #control_delay_ms(1)
                time.sleep(0.001)

            # Restart if necessary
            if self.myGuy.dotCount == MAX_DOT_LVL:
                self.level += 1
                await Scoreboard().setMode(self.level+1, self.lives+1)
                time.sleep(2)
                self.setup_defaults()
                await self.setup_level()
                self.gameRunning = TRUE
            elif self.lives and not self.gameRunning:
                self.lives -= 1
                await Scoreboard().setMode(self.level+1, self.lives+1)
                time.sleep(2)
                self.death_restart()
                await self.setup_level()
                await self.draw_score()
                self.gameRunning = TRUE

        time.sleep(1)
        await self.display_close()

        return 0
