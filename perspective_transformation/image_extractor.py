import cv2
import numpy as np


class ImageExtractor:
    def __init__(self, source_path=None, destination_path=None, width=None, height=None):
        self.img = None
        self.original_img = None
        self.transformed_img = None
        self.WINDOW_NAME = 'Preview Window'
        self.source_path = source_path
        self.destination_path = destination_path
        self.width = width
        self.height = height
        self.points = []
        self.load_image()
        self.show_base_img()

    def load_image(self):
        if self.source_path:
            while True:
                self.original_img = cv2.imread(self.source_path)
                if self.original_img is not None:
                    self.img = self.original_img.copy()
                    break
                print(
                    "Error: Could not load image. Please check the path and try again.")
                self.source_path = get_source_path()

    def show_base_img(self):
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.imshow(self.WINDOW_NAME, self.img)
        cv2.setMouseCallback(self.WINDOW_NAME, self.mouse_callback)
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                self.points.clear()
                self.img = self.original_img.copy()
                self.transformed_img = None
                cv2.imshow(self.WINDOW_NAME, self.img)
            if key == ord('q'):
                cv2.destroyAllWindows()
                break
            if key == ord('s') and len(self.points) == 4:
                self.save_image(self.transformed_img)
                print(f"Image saved to {self.destination_path}")

    def handle_perspective_transformation(self):
        img_transformed = self.get_perspective_transformed_img()
        self.transformed_img = img_transformed
        cv2.imshow(self.WINDOW_NAME, img_transformed)

    def mouse_callback(self, event, x, y, flags, param):
        if len(self.points) < 4:
            if event == cv2.EVENT_LBUTTONDOWN:
                count = len(self.points) + 1
                self.img = cv2.circle(self.img, (x, y), 5, (255, 0, 0), -1)
                self.img = cv2.putText(
                    self.img, f'{count}', (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                cv2.imshow(self.WINDOW_NAME, self.img)
                self.points.append((x, y))
            if len(self.points) == 4:
                self.handle_perspective_transformation()

    def save_image(self, img):
        cv2.imwrite(self.destination_path, img)

    def sort_points(self):
        # Used ChatGPT here to find a solution for sorting the points in the correct order
        sorted_points_comb = sorted(self.points, key=lambda p: p[0] + p[1])
        top_left = sorted_points_comb[0]
        bottom_right = sorted_points_comb[-1]
        sorted_points_diff = sorted(self.points, key=lambda p: p[0] - p[1])
        bottom_left = sorted_points_diff[0]
        top_right = sorted_points_diff[-1]

        return [top_left, top_right, bottom_right, bottom_left]

    def get_perspective_transformed_img(self):
        sorted_points = self.sort_points()
        points = np.float32(sorted_points)
        destination = np.float32(np.array([
            [0, 0],
            [self.width, 0],
            [self.width, self.height],
            [0, self.height]
        ]))
        mat = cv2.getPerspectiveTransform(points, destination)
        img_transformed = cv2.warpPerspective(
            self.original_img, mat, (self.width, self.height), flags=cv2.INTER_LINEAR)
        return img_transformed


def get_source_path():
    path = input("Enter the path to the source image: ")
    return path


def get_destination_path():
    destination_path = input(
        "Enter the path to save the extracted image (e.g., output.jpg dont forget filename and extension): ")
    if not destination_path.endswith(('.jpg', '.png', '.jpeg')):
        print("Error: Destination path must end with .jpg, .png, or .jpeg")
        return get_destination_path()
    filename = destination_path.split("/")[-1]
    if filename in ['.jpg', '.png', '.jpeg']:
        print("Error: Destination path must include a filename.")
        return get_destination_path()
    return destination_path


def get_resolution():
    width = int(input("Enter the width of the output image: "))
    height = int(input("Enter the height of the output image: "))
    return (width, height)


def main():
    source_path = get_source_path()
    destination_path = get_destination_path()
    width, height = get_resolution()
    extractor = ImageExtractor(
        source_path=source_path,
        destination_path=destination_path,
        width=width,
        height=height
    )


if __name__ == "__main__":
    main()
