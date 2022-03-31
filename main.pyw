import pygame
from enum import Enum, auto
import random
import time
import copy
pygame.init()


class State(Enum):
    EMPTY = auto()
    APPLE = auto()
    SNAKE = auto()


class Pathfinding(Enum):
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class Events():
    SNAKE_DIE = pygame.USEREVENT + 1
    APPLE_DIE = pygame.USEREVENT + 2


class Fonts():
    TITLE = pygame.font.SysFont("comicsansms", 40)
    GAME_OVER = pygame.font.SysFont("comicsansms", 50, bold=True)
    SCORE = pygame.font.SysFont("comicsansms", 30)
    BUTTON = pygame.font.SysFont("comicsansms", 20)


class Colors():
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (127, 163, 108)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 128, 0)
    PURPLE = (255, 0, 255)
    GREY = (128, 128, 128)
    LIGHT_GREY = (192, 192, 192)


class BoardPosition:
    def __init__(self, x, y, state=State.EMPTY):
        self.x = x
        self.y = y
        self.state = state

        # The path taken from the snakes head to the point
        # Used in snake hard ai
        self.g_cost = None
        self.parent = None

    def __repr__(self):
        return f"(Board({self.x}, {self.y}: {self.state}, parent: {self.parent})"

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


class Board:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

        self.board = [[BoardPosition(x, y) for x in range(width)]
                      for y in range(height)]

    def __getitem__(self, i):
        return self.board[i]

    def __setitem__(self, i, value):
        self.board[i] = value

    def draw(self, window: pygame.Surface):
        width, height = window.get_size()

        rect_h = height // self.height
        rect_w = width // self.width

        for row in self.board:
            for pos in row:
                if pos.state == State.APPLE:
                    pygame.draw.rect(window, (255, 0, 0),
                                     (pos.x * rect_w, pos.y * rect_h, rect_w, rect_h))
                elif pos.state == State.SNAKE:
                    pygame.draw.rect(window, (0, 255, 0),
                                     (pos.x * rect_w, pos.y * rect_h, rect_w, rect_h))
                elif pos.state == State.EMPTY:
                    pygame.draw.rect(window, (0, 0, 0),
                                     pygame.Rect(pos.x * rect_w, pos.y * rect_h, rect_w, rect_h))

                pygame.draw.rect(window, (124, 124, 124),
                                 pygame.Rect(pos.x * rect_w, pos.y * rect_h, rect_w, rect_h), 2)


class Apple:
    def __init__(self, start_pos: tuple):
        self.x, self.y = start_pos
        self.old_x, self.old_y = start_pos

        self.last_move = 0

    def update_pos(self, board: Board):
        board[self.old_y][self.old_x].state = State.EMPTY
        self.old_x, self.old_y = self.x, self.y

        board[self.y][self.x].state = State.APPLE

    def place(self, board: Board):
        board[self.y][self.x].state = State.APPLE


class Snake:
    def __init__(self, start_pos: tuple, apple: Apple, board: Board, pathfinding: Pathfinding):
        self.x, self.y = start_pos

        self.pathfinding_options = {Pathfinding.EASY: self.easy,
                                    Pathfinding.MEDIUM: self.medium, Pathfinding.HARD: self.hard}
        self.pathfinding = pathfinding

        self.body = [BoardPosition(self.x, self.y, State.SNAKE), BoardPosition(
            self.x - 1, self.y, State.SNAKE), BoardPosition(self.x - 2, self.y, State.SNAKE)]

        self.board = board

        for pos in self.body:
            self.board[pos.y][pos.x].state = pos.state

        self.apple = apple

        self.last_move = 0
        self.last_grow = 0

        self.direction = Direction.RIGHT
        self.old_direction = self.direction

    def easy(self, board: Board, apple: Apple):
        # Snake moves forward 70% of the time
        # Left or right 30% of the time

        choice = random.randint(0, 10)

        if choice <= 7:
            self.direction = self.old_direction

        if choice > 7:
            if self.direction in {Direction.UP, Direction.DOWN}:
                self.direction = random.choice(
                    [Direction.LEFT, Direction.RIGHT])

            elif self.direction in {Direction.LEFT, Direction.RIGHT}:
                self.direction = random.choice(
                    [Direction.UP, Direction.DOWN])

        self.old_direction = self.direction

    def medium(self, baord: Board, apple: Apple):
        # Finds x and y distance to apple
        # Moves the larger distance first
        # If the distance is the same, move on the x axis first

        x_dist = abs(self.x - apple.x)
        y_dist = abs(self.y - apple.y)

        if x_dist >= y_dist:
            if self.x > apple.x:
                self.direction = Direction.LEFT

            elif self.x < apple.x:
                self.direction = Direction.RIGHT

        else:
            if self.y > apple.y:
                self.direction = Direction.UP

            elif self.y < apple.y:
                self.direction = Direction.DOWN

        # if the direction is opposite of the old direction then turn right
        if self.direction == Direction.LEFT and self.old_direction == Direction.RIGHT:
            self.direction = Direction.DOWN
        elif self.direction == Direction.RIGHT and self.old_direction == Direction.LEFT:
            self.direction = Direction.UP
        elif self.direction == Direction.UP and self.old_direction == Direction.DOWN:
            self.direction = Direction.RIGHT
        elif self.direction == Direction.DOWN and self.old_direction == Direction.UP:
            self.direction = Direction.LEFT

        self.old_direction = self.direction

    def hard(self, board: Board, apple: Apple):
        # Uses A* to find the shortest path to the apple and considers the snake's body as obstacles
        # Moves in the direction of the path

        for row in board:
            for pos in row:
                pos.g_cost = None
                pos.parent = None

        marked = []
        evaluated = []

        marked.append(self.body[0])
        marked[0].g_cost = 0

        while True:
            current_pos = sorted(
                marked, key=lambda x: self._f_cost(x, apple))[0]
            marked.remove(current_pos)
            evaluated.append(current_pos)

            if current_pos == apple:
                # Find direction

                while True:
                    if current_pos.parent != self.body[0]:
                        current_pos = current_pos.parent

                    else:
                        break

                if current_pos.x > self.x:
                    self.direction = Direction.RIGHT

                elif current_pos.x < self.x:
                    self.direction = Direction.LEFT

                elif current_pos.y > self.y:
                    self.direction = Direction.DOWN

                elif current_pos.y < self.y:
                    self.direction = Direction.UP

                self.old_direction = self.direction

                break

            for pos in self._pos_neighbors(board, current_pos):
                if pos.state == State.SNAKE or pos in evaluated:
                    continue

                if pos not in marked:
                    marked.append(pos)

            if len(marked) == 0:
                self.direction = self.old_direction
                break

    def _h_cost(self, point: BoardPosition, apple: Apple):
        # Find shortest distance to apple

        x_dist = abs(point.x - apple.x)
        y_dist = abs(point.y - apple.y)

        return x_dist + y_dist

    def _g_cost(self, point: BoardPosition):
        return point.g_cost

    def _f_cost(self, point: BoardPosition, apple: Apple):
        return self._g_cost(point) + self._h_cost(point, apple)

    def _pos_neighbors(self, board: Board, pos: BoardPosition):
        # Returns all neighbors of a position
        # Do not include the edge of the board

        neighbors = []

        if pos.x > 0:
            neighbor = board[pos.y][pos.x - 1]
            if neighbor.g_cost == None or neighbor.g_cost > pos.g_cost + 1:
                neighbor.g_cost = pos.g_cost + 1
                neighbor.parent = pos
            neighbors.append(neighbor)

        if pos.x < board.width - 1:
            neighbor = board[pos.y][pos.x + 1]
            if neighbor.g_cost == None or neighbor.g_cost > pos.g_cost + 1:
                neighbor.g_cost = pos.g_cost + 1
                neighbor.parent = pos
            neighbors.append(neighbor)

        if pos.y > 0:
            neighbor = board[pos.y - 1][pos.x]
            if neighbor.g_cost == None or neighbor.g_cost > pos.g_cost + 1:
                neighbor.g_cost = pos.g_cost + 1
                neighbor.parent = pos
            neighbors.append(neighbor)

        if pos.y < board.height - 1:
            neighbor = board[pos.y + 1][pos.x]
            if neighbor.g_cost == None or neighbor.g_cost > pos.g_cost + 1:
                neighbor.g_cost = pos.g_cost + 1
                neighbor.parent = pos
            neighbors.append(neighbor)

        return neighbors

    def move(self, board, game_speed):
        if time.time() - self.last_move < 1 / game_speed:
            return

        self.pathfinding_options[self.pathfinding](board,
                                                   self.apple)

        if self.direction == Direction.UP:
            self.y -= 1
            self.body.insert(0, BoardPosition(self.x, self.y, State.SNAKE))
        elif self.direction == Direction.DOWN:
            self.y += 1
            self.body.insert(0, BoardPosition(self.x, self.y, State.SNAKE))
        elif self.direction == Direction.LEFT:
            self.x -= 1
            self.body.insert(0, BoardPosition(self.x, self.y, State.SNAKE))
        elif self.direction == Direction.RIGHT:
            self.x += 1
            self.body.insert(0, BoardPosition(self.x, self.y, State.SNAKE))

        if time.time() - self.last_grow > 1 / game_speed * 30:
            self.last_grow = time.time()
        else:
            last = self.body.pop()
            board[last.y][last.x].state = State.EMPTY

        self.last_move = time.time()

        # Checks
        if self.x < 0 or self.x >= board.width or self.y < 0 or self.y >= board.height:
            pygame.event.post(pygame.event.Event(Events.SNAKE_DIE))
            return

        if len(set(self.body)) != len(self.body):
            pygame.event.post(pygame.event.Event(Events.SNAKE_DIE))
            return

        if self.x == self.apple.x and self.y == self.apple.y:
            pygame.event.post(pygame.event.Event(Events.APPLE_DIE))

        for pos in self.body:
            board[pos.y][pos.x].state = pos.state


class Game:
    def __init__(self, width: int, height: int, game_speed: int):
        self.WIN = pygame.display.set_mode((width, height))

        self.width = width
        self.height = height

        self.game_speed = game_speed
        self.clock = pygame.time.Clock()

    def main(self):
        self.board = Board(self.width // 30, self.height // 30)
        self.apple = Apple(
            (self.board.width // 2 + self.board.width // 4, self.board.height // 2))
        self.snake = Snake(
            (self.board.width // 4, self.board.height // 2), self.apple, self.board, Pathfinding.HARD)

        self.apple.place(self.board)

        # MAIN MENU
        title = Fonts.TITLE.render("SNAKE", True, Colors.WHITE)

        easy_button = pygame.Rect(self.width // 2 - 100, 200, 200, 50)
        medium_button = pygame.Rect(self.width // 2 - 100, 260, 200, 50)
        hard_button = pygame.Rect(self.width // 2 - 100, 320, 200, 50)

        easy_text = Fonts.BUTTON.render("EASY", True, Colors.BLACK)
        medium_text = Fonts.BUTTON.render("MEDIUM", True, Colors.BLACK)
        hard_text = Fonts.BUTTON.render("HARD", True, Colors.BLACK)

        main_menu = True
        while main_menu:
            self.WIN.fill(Colors.BLACK)

            self.WIN.blit(title, (self.width // 2 - title.get_width() //
                          2, 50))

            pygame.draw.rect(self.WIN, Colors.WHITE, easy_button)
            pygame.draw.rect(self.WIN, Colors.WHITE, medium_button)
            pygame.draw.rect(self.WIN, Colors.WHITE, hard_button)

            self.WIN.blit(easy_text, (self.width // 2 - easy_text.get_width() // 2,
                          easy_button.y + easy_button.height // 2 - easy_text.get_height() // 2))
            self.WIN.blit(medium_text, (self.width // 2 - medium_text.get_width() // 2,
                          medium_button.y + medium_button.height // 2 - medium_text.get_height() // 2))
            self.WIN.blit(hard_text, (self.width // 2 - hard_text.get_width() // 2,
                          hard_button.y + hard_button.height // 2 - hard_text.get_height() // 2))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if easy_button.collidepoint(event.pos):
                        self.snake.pathfinding = Pathfinding.EASY
                        main_menu = False

                    elif medium_button.collidepoint(event.pos):
                        self.snake.pathfinding = Pathfinding.MEDIUM
                        main_menu = False

                    elif hard_button.collidepoint(event.pos):
                        self.snake.pathfinding = Pathfinding.HARD
                        main_menu = False

            pygame.display.update()
            self.clock.tick(60)

        self.draw()

        wait_for_input = True
        while wait_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                if event.type == pygame.KEYDOWN:
                    self.start_time = time.time()
                    wait_for_input = False

        while True:
            self.handle_movement(self.apple, self.board)
            self.apple.update_pos(self.board)

            self.snake.move(self.board, self.game_speed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                elif event.type == Events.SNAKE_DIE:
                    score = int(1 / (time.time() - self.start_time) * 10000)

                    winner = Fonts.GAME_OVER.render(
                        "YOU WIN!", True, Colors.GREEN)
                    score = Fonts.SCORE.render(
                        f"SCORE: {score}", True, Colors.WHITE)

                    self.WIN.blit(winner, (self.width // 2 -
                                           winner.get_width() // 2, 100))
                    self.WIN.blit(score, (self.width // 2 -
                                          score.get_width() // 2 - 10, 115 + winner.get_height()))

                    win_time = time.time()

                    while time.time() - win_time < 3:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                pygame.quit()
                                exit()

                        pygame.display.update()
                        self.clock.tick(60)

                    return

                elif event.type == Events.APPLE_DIE:
                    self.draw()

                    loser = Fonts.GAME_OVER.render(
                        "GAME OVER", True, Colors.RED)

                    self.WIN.blit(loser, (self.width // 2 -
                                          loser.get_width() // 2, self.height // 2 - loser.get_height() // 2))

                    pygame.display.update()

                    win_time = time.time()

                    while time.time() - win_time < 3:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                pygame.quit()
                                exit()

                        pygame.display.update()
                        self.clock.tick(60)
                    return

            self.draw()

            self.clock.tick(60)

    def draw(self):
        self.WIN.fill((0, 0, 0))

        self.board.draw(self.WIN)

        pygame.display.update()

    def handle_movement(self, apple: Apple, board: Board):
        keys = pygame.key.get_pressed()

        if time.time() - apple.last_move < 1 / self.game_speed:
            return

        if keys[pygame.K_UP]:
            if apple.y - 1 < 0:
                if self.board[board.height - 1][apple.x].state != State.SNAKE:
                    apple.y = board.height - 1
            else:
                if self.board[apple.y - 1][apple.x].state != State.SNAKE:
                    apple.y -= 1

            apple.last_move = time.time()

        if keys[pygame.K_DOWN]:
            if apple.y + 1 >= board.height:
                if self.board[0][apple.x].state != State.SNAKE:
                    apple.y = 0
            else:
                if self.board[apple.y + 1][apple.x].state != State.SNAKE:
                    apple.y += 1

            apple.last_move = time.time()

        if keys[pygame.K_LEFT]:
            if apple.x - 1 < 0:
                if self.board[apple.y][board.width - 1].state != State.SNAKE:
                    apple.x = board.width - 1
            else:
                if self.board[apple.y][apple.x - 1].state != State.SNAKE:
                    apple.x -= 1

            apple.last_move = time.time()

        if keys[pygame.K_RIGHT]:
            if apple.x + 1 >= board.width:
                if self.board[apple.y][0].state != State.SNAKE:
                    apple.x = 0
            else:
                if self.board[apple.y][apple.x + 1].state != State.SNAKE:
                    apple.x += 1

            apple.last_move = time.time()


if __name__ == "__main__":
    game = Game(421, 421, 7)
    while True:
        game.main()
