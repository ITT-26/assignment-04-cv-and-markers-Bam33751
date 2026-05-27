import cv2
import cv2.aruco as aruco
import numpy as np
import pyglet
from PIL import Image
import sys

TIMER = 25
MAX_MISSED_FRAMES = 45
CONTOUR_AREA_THRESHOLD = 300


class BoardDectector:
    def __init__(self, dector, width, height):
        self.detector = dector
        self.width = width
        self.height = height
        self.matrix = None
        self.missed_frames = 0
        self.max_missed_frames = MAX_MISSED_FRAMES

    def detect_markers(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        return corners, ids

    def perspective_transform(self, corners, ids, frame, mat=None):
        # Marker with id 0 is top left, id 1 is top right, id 2 is bottom right, id 3 is bottom left
        if mat is None:
            for i in range(len(ids)):
                id = ids[i][0]
                if id == 0:
                    top_left = corners[i][0][2]
                elif id == 1:
                    top_right = corners[i][0][3]
                elif id == 2:
                    bottom_right = corners[i][0][0]
                elif id == 3:
                    bottom_left = corners[i][0][1]

            points = np.float32(np.array([
                top_left,
                top_right,
                bottom_right,
                bottom_left
            ]))
        destination = np.float32(np.array([
            [0, 0],
            [self.width, 0],
            [self.width, self.height],
            [0, self.height]
        ]))

        if mat is None:
            mat = cv2.getPerspectiveTransform(points, destination)
        img_transformed = cv2.warpPerspective(
            frame, mat, (int(self.width), int(self.height)), flags=cv2.INTER_LINEAR)
        return img_transformed, mat

    def get_board_frame(self, frame):
        corners, ids = self.detect_markers(frame)
        if ids is not None and len(ids) == 4:
            board_frame, matrix = self.perspective_transform(
                corners, ids, frame)
            self.matrix = matrix
            self.missed_frames = 0

            return board_frame, corners, ids
        if self.matrix is not None:
            if self.missed_frames < self.max_missed_frames:
                board_frame, _ = self.perspective_transform(
                    corners, ids, frame, self.matrix)
                self.missed_frames += 1
                return board_frame, corners, ids
        return None, corners, ids


class Game:
    """"Class to handle game logic and state

    Used ChatGPt for labels and relative positioning of elements and restart/gameover logic"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.score = 0
        self.highscore = 0
        self.started = False
        self.game_over = False

        self.finger_position = None
        self.sprite = pyglet.sprite.Sprite(
            pyglet.image.load('ar_game/ant.png'))
        self.sprite.scale = 0.2
        self.sprite.x = np.random.randint(0, self.width - self.sprite.width)
        self.sprite.y = np.random.randint(0, self.height - self.sprite.height)

        self.timer = TIMER

        self.font_size = int(self.height * 0.04)
        self.score_label = pyglet.text.Label(
            f'Score: {self.score}',
            font_size=self.font_size,
            x=self.width - 20,
            y=self.height - 20,
            anchor_x='right',
            anchor_y='top',
            color=(2, 38, 92, 255)
        )

        self.timer_label = pyglet.text.Label(
            f'Time: {self.timer}',
            font_size=self.font_size,
            x=20,
            y=self.height - 20,
            anchor_x='left',
            anchor_y='top',
            color=(2, 38, 92, 255)
        )
        self.label_middel = pyglet.text.Label(
            'Ant Alert! Find and touch the ant! Press Space to start.',
            font_size=self.font_size,
            x=self.width / 2,
            y=self.height / 2,
            anchor_x='center',
            anchor_y='center',
            color=(2, 38, 92, 255)
        )
        self.label_highscore = pyglet.text.Label(
            '',
            font_size=self.font_size,
            x=self.width / 2,
            y=self.height - 20,
            anchor_x='center',
            anchor_y='top',
            color=(2, 38, 92, 255)
        )

    def check_collision(self):
        if self.finger_position is None:
            return False
        x, y = self.finger_position

        # Mirror sprite y
        sprite_y = self.height - self.sprite.y - self.sprite.height

        # Apply factor for hitbox
        # Multipling real scale factor 0.4 is too difficult to hit
        sprite_width = self.sprite.width * 0.6
        sprite_height = self.sprite.height * 0.6

        if (self.sprite.x <= x <= self.sprite.x + sprite_width) and (sprite_y <= y <= sprite_y + sprite_height):
            self.score += 1
            self.score_label.text = f'Score: {self.score}'
            return True
        return False

    def update(self, board_frame):
        if not self.started:
            self.label_middel.text = 'Ant Alert! Find and touch the ant! Press Space to start.'
            return
        if self.game_over:
            self.label_middel.text = f'Game Over! Final Score: {self.score}. Press R to restart.'
            if self.score > self.highscore:
                self.highscore = self.score
            self.label_highscore.text = f'Highscore: {self.highscore}'
            return

        self.finger_position = self.detect_finger(board_frame)
        # Debug showing finger tip
        #if self.finger_position is not None:
        #    cv2.circle(board_frame, self.finger_position, 20, (0, 255, 0), 3)

        if self.check_collision():
            self.sprite.x = np.random.randint(
                0, self.width - self.sprite.width)
            self.sprite.y = np.random.randint(
                0, self.height - self.sprite.height)

    def update_timer(self):
        if not self.started or self.game_over:
            return

        self.timer -= 1
        self.timer_label.text = f'Seconds remaining: {self.timer}'

        if self.timer <= 0:
            self.game_over = True

    def detect_finger(self, board_frame):
        hsv = cv2.cvtColor(board_frame, cv2.COLOR_BGR2HSV)
        darker_skin = np.array([5, 40, 82])
        lighter_skin = np.array([20, 210, 247])
        mask = cv2.inRange(hsv, darker_skin, lighter_skin)
        # debug showing mask
        # cv2.imshow("Mask", mask)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        contour = max(contours, key=cv2.contourArea)
        # debug = board_frame.copy()
        # cv2.drawContours(debug, [contour], -1, (0, 255, 0), 3)
        # cv2.imshow("Contour", debug)

        if cv2.contourArea(contour) < CONTOUR_AREA_THRESHOLD:
            return None

        # The tip of the finger is the point with the smallest y-coordinate
        # Used ChatGPT for this line
        tip = contour[contour[:, :, 1].argmin()][0]

        return tuple(tip)

    def draw(self, board_frame):
        self.sprite.draw()
        self.score_label.draw()
        self.timer_label.draw()
        self.label_middel.draw()
        self.label_highscore.draw()

    def start(self):
        self.started = True
        self.game_over = False
        self.label_middel.text = ''

    def reset(self):
        self.score = 0
        self.timer = 25
        self.started = False
        self.game_over = False
        self.sprite.x = np.random.randint(0, self.width - self.sprite.width)
        self.sprite.y = np.random.randint(0, self.height - self.sprite.height)
        self.score_label.text = f'Score: {self.score}'
        self.timer_label.text = f'Time: {self.timer}'
        self.label_middel.text = 'Ant Alert! Find and touch the ant! Press Space to start.'


video_id = 0

if len(sys.argv) > 1:
    video_id = int(sys.argv[1])

aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
aruco_params = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, aruco_params)

# converts OpenCV image to PIL image and then to pyglet texture
# https://gist.github.com/nkymut/1cb40ea6ae4de0cf9ded7332f1ca0d55


def cv2glet(img, fmt):
    '''Assumes image is in BGR color space. Returns a pyimg object'''
    if fmt == 'GRAY':
        rows, cols = img.shape
        channels = 1
    else:
        rows, cols, channels = img.shape

    raw_img = Image.fromarray(img).tobytes()

    top_to_bottom_flag = -1
    bytes_per_row = channels*cols
    pyimg = pyglet.image.ImageData(width=cols,
                                   height=rows,
                                   fmt=fmt,
                                   data=raw_img,
                                   pitch=top_to_bottom_flag*bytes_per_row)
    return pyimg


def main():
    # Create a video capture object for the webcam
    cap = cv2.VideoCapture(video_id)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    width_mac = width / 2
    height_mac = height / 2
    board_detector = BoardDectector(detector, width, height)
    game = Game(width, height)

    # Need to use half of the width and height because of mac scaling
    # window = pyglet.window.Window(width_mac, height_mac)

    # Use this for windows instead (i hope it works on windows like i think :/ )
    window = pyglet.window.Window(width, height)

    @window.event
    def on_draw():
        window.clear()
        ret, frame = cap.read()
        board_frame, corners, ids = board_detector.get_board_frame(frame)
        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners)
        if board_frame is not None:
            board_frame = cv2.flip(board_frame, 1)
            game.update(board_frame)
            img = cv2glet(board_frame, 'BGR')
            img.blit(0, 0, 0)
            game.draw(board_frame)
        else:
            img = cv2glet(frame, 'BGR')
            img.blit(0, 0, 0)

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.SPACE:
            if not game.started and not game.game_over:
                game.start()
        elif symbol == pyglet.window.key.R:
            if game.game_over:
                game.reset()
        elif symbol == pyglet.window.key.ESCAPE:
            cap.release()
            pyglet.app.exit()

    pyglet.clock.schedule_interval(lambda dt: game.update_timer(), 1.0)
    pyglet.app.run()


if __name__ == "__main__":
    main()
