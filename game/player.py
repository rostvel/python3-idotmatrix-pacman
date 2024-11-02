class Player:
    id = 0  # Index used to find stored values
    color = 0  # Uses color defines below
    x = 0  # Position on the game surface, 0 is left
    y = 0  # Position on the game surface, 0 is top
    travelDir = 0  # Uses directional defines below
    dotCount = 0  # For player tracks self.level completion
    # For enemy decides when to go inPlay
    speed = 0  # Countdown how freqeuntly to move
    speedMode = 0  # Index used to look up player speed
    inPlay = 0  # On the hunt = TRUE, in reserve = FALSE
    tarX = 0  # Target X coord. for enemy
    tarY = 0  # Target Y coord. for enemy
    dotLimit = 1  # How many dots before this enemy is inPlay
