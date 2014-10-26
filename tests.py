import json
from time import sleep
import unittest
from gomoku import Game
import os
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase, gen_test
from ws4py.client.tornadoclient import TornadoWebSocketClient
from tornado import ioloop, websocket

__author__ = 'serdiuk'


class TestClient(AsyncHTTPTestCase):
    """Tests sql requests"""

    @classmethod
    def setUpClass(cls):
        os.environ['ASYNC_TEST_TIMEOUT'] = '60'

    def get_app(self):
        return Game(test=True)

    def get_protocol(self):
        return 'ws'

    def read(self, response):
        if response:
            response = json.loads(response)
            if response['event'] == 'error':
                print response['info']
            return response

    @gen_test
    def test_game(self):
        """first test function"""
        connection1 = yield websocket.websocket_connect(
            self.get_url('/game'), io_loop=self.io_loop
        )

        connection2 = yield websocket.websocket_connect(
            self.get_url('/game'), io_loop=self.io_loop
        )

        # create game
        msg = {'command': 'create', 'name':  'test1', 'color': 1}
        connection1.write_message(json.dumps(msg))

        response = yield connection1.read_message()
        response = self.read(response)
        self.assertEqual(response['event'], 'created')

        # join game
        msg = {'command': 'join', 'name': 'test2'}
        connection2.write_message(json.dumps(msg))

        # game started 1st player
        response = yield connection2.read_message()
        response = self.read(response)
        self.assertEqual(response['event'], 'start_game')
        self.assertEqual(response['info'], 'move')

        # game started 2nd player
        response = yield connection1.read_message()
        response = self.read(response)
        self.assertEqual(response['event'], 'start_game')
        self.assertEqual(response['info'], 'wait')

        # Moves
        for i in range(5):
            msg = {'command': 'move', 'cell': 0+i}
            connection2.write_message(json.dumps(msg))
            response = yield connection2.read_message()
            response = self.read(response)
            self.assertEqual(response['event'], 'move')
            response = yield connection1.read_message()
            response = self.read(response)
            self.assertEqual(response['event'], 'move')

            if i == 4:
                # After 5 moves of first player it wins game
                response = yield connection2.read_message()
                response = self.read(response)
                self.assertEqual(response['event'], 'end_game')
                self.assertEqual(response['info'], 'win')

                response = yield connection1.read_message()
                response = self.read(response)
                self.assertEqual(response['event'], 'end_game')
                self.assertEqual(response['info'], 'loss')
                break

            msg = {'command': 'move', 'cell': 19+i}
            connection1.write_message(json.dumps(msg))
            response = yield connection1.read_message()
            response = self.read(response)
            self.assertEqual(response['event'], 'move')

            response = yield connection2.read_message()
            response = self.read(response)
            self.assertEqual(response['event'], 'move')

if __name__ == '__main__':

    unittest.main()
