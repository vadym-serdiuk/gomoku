import calendar
import json
from operator import itemgetter
import datetime
import random
import uuid
import sys
from bson import ObjectId
import os
from pymongo import MongoClient
import re
from tornado import web, websocket
import tornado
from tornado.escape import xhtml_escape
from tornado.web import asynchronous

__author__ = 'serdiuk'

WHITE = 1
BLACK = 2
EMPTY = 0
COLORS = (WHITE, BLACK)

REASON_PLAYER_LEFT_THE_BOARD = 1
REASON_PLAYER_WIN = 2
REASON_DRAW = 3

class Board(object):
    board_size = 19

    def __init__(self, player):
        self.players = [player]
        self.board = [EMPTY for i in range(self.board_size * self.board_size)]
        self.next_step = None
        self.white_moves = []
        self.black_moves = []

    def join(self, player):
        if self._player_at_board(player) or not self.is_available:
            return EMPTY

        color = self._get_free_color()
        self.players.append(player)
        return color

    @property
    def is_available(self):
        return len(self.players) < 2

    @property
    def is_empty(self):
        return self.players == []

    def leave(self, player):
        try:
            ind = self.players.index(player)
        except:
            return

        self._end_game(REASON_PLAYER_LEFT_THE_BOARD, player)
        del self.players[ind]

    def move(self, player, cell):
        player_color = player.color
        if player_color != self.next_step:
            msg = {'event': 'error',
                   'info': 'Incorrect order of steps'}
            self._send_message(player, msg)

        if self.board[cell] == EMPTY:
            self.board[cell] = player_color
            if player_color == WHITE:
                self.white_moves.append(cell)
            else:
                self.black_moves.append(cell)
        else:
            msg = {'event': 'error',
                   'info': 'This cell is not empty'}
            self._send_message(player, msg)

        # Redraw board
        for pl in self.players:
            status = 'wait' if pl == player else 'move'
            msg = {'event': 'move', 'cell': cell,
                   'color': player_color, 'status': status}
            self._send_message(pl, msg)

        # Check if player collected series
        moves = self.white_moves if player_color == WHITE \
                    else self.black_moves
        if self._is_five_collected(moves, cell):
            self._end_game(REASON_PLAYER_WIN, player)

        # Check if board is full
        if len(self.white_moves) + len( self.black_moves) == \
                self.board_size * self.board_size:
            self._end_game(REASON_DRAW, player)

        self.next_step = BLACK if self.next_step == WHITE else WHITE

    def start_game(self):
        for cell in self.board:
            cell = EMPTY
        self.white_moves = []
        self.black_moves = []
        self.next_step = BLACK
        for player in self.players:
            if player.color == self.next_step:
                msg = {'event': 'start_game', 'info': 'move'}
            else:
                msg = {'event': 'start_game', 'info': 'wait'}
            player.send_message(msg)

    def _end_game(self, reason, player=None):
        if reason == REASON_PLAYER_WIN:
            player.save_result('win')
            msg = {'event': 'end_game', 'info': 'win'}
            player.send_message(msg)

            another_player = self._get_another_player(player)
            another_player.save_result('loss')
            msg = {'event': 'end_game', 'info': 'loss'}
            self._send_message(another_player, msg)

        elif reason == REASON_PLAYER_LEFT_THE_BOARD:
            player.save_result('loss')

            another_player = self._get_another_player(player)
            another_player.save_result('win')
            msg = {'event': 'end_game', 'info': 'win'}
            self._send_message(another_player, msg)
        elif reason == REASON_DRAW:
            player.save_result('draw')
            msg = {'event': 'end_game', 'info': 'draw'}
            self._send_message(player, msg)

            another_player = self._get_another_player(player)
            another_player.save_result('draw')
            msg = {'event': 'end_game', 'info': 'draw'}
            self._send_message(another_player, msg)

    def _is_five_collected(self, player_moves, cell):
        direction_pairs = ((1, -1), (1, 0), (1,1), (0,1))
        for dir in direction_pairs:
            cur_cell = cell
            count = 1
            while True:
                cur_cell += dir[0]*self.board_size + dir[1]
                if cur_cell in player_moves:
                    count += 1
                else:
                    break
            dir = map(lambda x: -x, dir)
            cur_cell = cell
            while True:
                cur_cell += dir[0]*self.board_size + dir[1]
                if cur_cell in player_moves:
                    count += 1
                else:
                    break
            if count == 5:
                return True
        return False

    def _player_at_board(self, player):
        """
        If player is already at the board, return False else True
        """
        try:
            self.players.index(player)
            return True
        except:
            return False

    def _get_another_player(self, player):
        if len(self.players) == 2:
            try:
                ind = self.players.index(player)
                ind = 0 if ind == 1 else 1
                return self.players[ind]
            except:
                return None

    def _get_free_color(self):
        if len(self.players) > 1:
            raise Exception('This board is not free')
        if len(self.players) == 1:
            if self.players[0].color == BLACK:
                return WHITE
        return BLACK

    def _send_message(self, player, msg):
        if player:
            player.send_message(msg)


class Game(web.Application):

    def __init__(self, test=False):

        mongo_url = os.environ.get('MONGOHQ_URL', 'localhost')
        print mongo_url
        client = MongoClient(mongo_url)
        if test:
            self.db = client['test_gomoku']
        else:
            try:
                self.db = client.get_default_database()
            except:
                self.db = client['gomoku']

        # try:
        #     self.db = client.get_default_database()
        # except:
        #     self.db = client.db

        self.sockets = []
        self.boards = []
        self.free_boards = []

        handlers = [
            (r'^/$', MainHandler),
            (r'^/stats$', StatisticHandler),
            (r'^/static/(.*)', web.StaticFileHandler,
                {'path': 'static/'}),
            (r'^/game$', WebSocketHandler),
        ]

        settings = {
            'autoreload': True,
            'cookie_secret': "asdfasdfasgdfg2rqwtqe4f34fw34r43",
            'Debug': True
        }

        super(Game, self).__init__(handlers=handlers, **settings)

class MainHandler(web.RequestHandler):
    def get(self, *args, **kwargs):
        return self.render('templates/main.html', **{})


class StatisticHandler(web.RequestHandler):
    """
    Client send by method POST authentication data
    If user is found, then it needs to start session
    """
    def get(self, *args, **kwargs):
        param_user = self.get_argument('username', '')
        users = self.application.db.users.find().sort('wins', -1)
        table = []
        for i, user in enumerate(users):
            if i < 10 or user['username'] == param_user:
                user.update({'position': i+1})
                del user['_id']
                table.append(user)

        self.finish(json.dumps(table))


COMMANDS = (
    ('join', '_join_board'),
    ('create', '_create_board'),
    ('leave', '_leave_board'),
    ('ping', '_custom_ping'),
    ('move', '_move'),
)

class WebSocketHandler(websocket.WebSocketHandler):
    username = None
    board = None
    color = None

    def _create_board(self, message):
        """
        Creates the new board
        :param message:
        :return:
        """

        if self.board:
            self.board.leave(self)

        self.username = message.get('name')
        if not self.username:
            self.send_message({'event': 'error',
                               'info': 'Please provide your name'})
            return
        if self.application.db.users.find({'username': self.username})\
                .count() == 0:
            self.application.db.users.insert({'username': self.username,
                                              'games': 0,
                                              'wins': 0,
                                              'losses': 0,
                                              'draws': 0})

        self.color = message.get('color')
        if not self.color in COLORS:
            self.send_message({'event': 'error',
                               'info': 'Please select color'})
            return

        self.board = Board(self)
        self.application.free_boards.append(self.board)
        msg = {'event': 'created', 'color': self.color}
        self.write_message(msg)

    def _join_board(self, message):
        """
        Join the free board for recieving messages from this room
        :param room:
        :return:
        """

        self.username = message.get('name')
        if not self.username:
            self.send_message({'event': 'error',
                               'info': 'Please provide your name'})
            return
        if self.application.db.users.find({'username': self.username})\
                .count() == 0:
            self.application.db.users.insert({'username': self.username,
                                              'games': 0,
                                              'wins': 0,
                                              'losses': 0,
                                              'draws': 0})

        if self.application.free_boards == []:
            msg = {'event': 'error',
                   'info': 'There are no free boards. Create one.'}
            self.send_message(msg)
            return

        free_board_index = random.randint(0, len(self.application.free_boards)-1)
        free_board = self.application.free_boards[free_board_index]
        del self.application.free_boards[free_board_index]

        self.color = free_board.join(self)
        if self.color in COLORS:
            self.board = free_board
            self.board.start_game()

    def _leave_board(self, message):
        """
        Leaves the room
        :param message:
        :return:
        """
        self.board.leave(self)
        self.board = None

    def _move(self, message):
        cell = message.get('cell')
        if type(cell) == type(0):
            self.board.move(self, cell)
        else:
            msg = {'event': 'error', 'info': 'Invalid parameter "cell"'}
            self.write_message(msg)

    def _custom_ping(self, message):
        return

    def _select_command(self, msg):
        """
        If message contains command then process command and return True
        else return False
        :param message:
        :return:
        """
        message = json.loads(msg)
        if 'command' in message:
            command = message['command']
            for item in COMMANDS:
                if item[0] == command:
                    handler = getattr(self, item[1])
                    handler(message)
                    return True
        return False

    def save_result(self, result):
        db = self.application.db
        user = db.users.find_one({'username': self.username})
        if 'games' in user:
            user['games'] += 1
        else:
            user['games'] = 1

        if result == 'win':
            if 'wins' in user:
                user['wins'] += 1
            else:
                user['wins'] = 1

        if result == 'loss':
            if 'losss' in user:
                user['losses'] += 1
            else:
                user['losses'] = 1

        if result == 'draw':
            if 'draws' in user:
                user['draws'] += 1
            else:
                user['draws'] = 1

        db.users.save(user)

    def send_message(self, message):
        """
        Sends message to client
        :param message:
        :return:
        """
        self.ws_connection.write_message(
                            json.dumps(message))

    def open(self):
        """
        Trying to open connection
        Check user authorization
        :return:
        """
        self.application.sockets.append(self)

    def on_message(self, message):
        """
        when a message is recieved, then process command or
        send message to everybody
        :param message:
        :return:
        """
        message = message.strip()
        self._select_command(message)

    def on_close(self, message=None):
        """
        If connection closed by client then it needs to leave all rooms
        and delete socket from array
        :param message:
        :return:
        """
        if self.board:
            self.board.leave(self)

if __name__ == '__main__':

    io_loop = tornado.ioloop.IOLoop.instance()
    application = Game()
    port = os.environ.get('PORT', 5000)
    application.listen(port)
    print("Started at port %s" % port)
    try:
        io_loop.start()
    except:
        io_loop.stop()
