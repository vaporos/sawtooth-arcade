# Copyright 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import logging
import random
import string
import hashlib

from enum import Enum

from sawtooth_battleship.battleship_exceptions import BoardLayoutException


LOGGER = logging.getLogger(__name__)


class ShipOrientation(Enum):
    horizontal = 1
    vertical = 2


class BoardLayout(object):
    def __init__(self, size):
        self.ship_positions = []
        self.size = size

    def append(self, ship_position):
        """Attempts to append the ship at the specified position.

        Attributes:
            ship_position (ShipPosition): The ship to append to the layout.

        Raises:
            BoardLayoutException: If the position is already occupied or is
                otherwise invalid.
        """

        self.ship_positions.append(ship_position)

        # Check validity by rendering the board into a string
        try:
            self.render()
        except BoardLayoutException, e:
            self.ship_positions = self.ship_positions[:-1]
            raise e

    def render(self):
        """Returns a game board layout as a list of strings.

        Raises:
            BoardLayoutException: If the position is already occupied or is
                otherwise invalid.
        """

        board = [['-'] * self.size for i in range(self.size)]

        for position in self.ship_positions:
            orientation = position.orientation
            row = position.row
            col = position.column
            text = position.text

            if orientation == ShipOrientation.horizontal:
                for i in xrange(0, len(text)):
                    if board[row][col + i] != '-':
                        raise BoardLayoutException(
                            "can not place ship at {}{}, space "
                            "is occupied with {}".format(
                                'ABCDEFGHIJ'[col],
                                row,
                                board[row][col]))
                    board[row][col + i] = text[i]
            elif orientation == ShipOrientation.vertical:
                for i in xrange(0, len(text)):
                    if board[row + i][col] != '-':
                        raise BoardLayoutException(
                            "can not place ship at {}{}, space "
                            "is occupied with {}".format(
                                'ABCDEFGHIJ'[col],
                                row,
                                board[row][col]))
                    board[row + i][col] = text[i]
            else:
                assert False, "invalid orientation: {}".format(orientation)

        return board

    def render_hashed(self, nonces):
        hashed_board = [[None] * self.size for _ in range(self.size)]
        clear_board = self.render()

        for row in xrange(0, self.size):
            for col in xrange(0, self.size):
                hashed_board[row][col] = hash_space(
                    clear_board[row][col], nonces[row][col])

        return hashed_board

    def serialize(self):
        data = {}
        data['size'] = self.size
        data['positions'] = []
        for position in self.ship_positions:
            data['positions'].append(position.serialize())
        return data

    @staticmethod
    def deserialize(data):
        layout = BoardLayout(data['size'])
        for position in data['positions']:
            layout.append(ShipPosition.deserialize(position))
        return layout

    @staticmethod
    def generate(size=10, ships=None, max_placement_attempts=100):
        if ships is None:
            ships = ["AAAAA", "BBBB", "CCC", "DD", "DD", "SSS", "SSS"]

        remaining = list(ships)
        layout = BoardLayout(size)

        while len(remaining) > 0:
            ship = remaining[0]
            remaining.remove(ship)

            success = False
            attempts = 0
            while not success:
                attempts += 1

                orientation = random.choice(
                    [ShipOrientation.horizontal,
                     ShipOrientation.vertical])
                if orientation == ShipOrientation.horizontal:
                    row = random.randrange(0, size)
                    col = random.randrange(0, size - len(ship) + 1)
                else:
                    row = random.randrange(0, size - len(ship) + 1)
                    col = random.randrange(0, size)

                position = ShipPosition(
                    text=ship, row=row, column=col, orientation=orientation)

                try:
                    layout.append(position)
                    success = True
                except BoardLayoutException:
                    if attempts > max_placement_attempts:
                        LOGGER.debug("exceeded attempts, resetting...")
                        layout = BoardLayout(size)
                        remaining = list(ships)
                        break

        return layout


class ShipPosition(object):
    """Represents a ship and it's placement on the board.

    Attributes:
        text (str): Ship's textual representation (example: AAAAA, BBBB)
        row (int): First row on which the ship appears (starts at 0)
        column (int): First column on which the ship appears (starts at 0)
        orientation (ShipOrientation): Whether placed horizontal or vertical
    """
    def __init__(self, text, row, column, orientation):
        self.text = text
        self.row = row
        self.column = column
        self.orientation = orientation

    def serialize(self):
        data = {}
        data['text'] = self.text
        data['row'] = self.row
        data['column'] = self.column
        data['orientation'] = self.orientation
        return data

    @staticmethod
    def deserialize(data):
        text = data['text']
        row = data['row']
        column = data['column']
        orientation = data['orientation']

        return ShipPosition(text, row, column, orientation)


def create_nonces(board_size):
    nonces = [[None] * board_size for _ in range(board_size)]
    for row in xrange(0, board_size):
        for col in xrange(0, board_size):
            nonces[row][col] = ''.join(
                [random.choice(string.ascii_letters) for _ in xrange(0, 10)])
    return nonces


def hash_space(space, nonce):
    m = hashlib.md5()
    m.update(space)
    m.update(nonce)
    return m.hexdigest()
