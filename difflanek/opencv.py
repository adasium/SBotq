from __future__ import annotations

import colorsys
import string
from collections import Counter
from collections import defaultdict
from typing import NamedTuple
from typing import Sequence

import cv2
import numpy as np
import pytesseract

PL_UPPERCASE = 'ĄĆĘŁÓŃŚŹŻ'
ALL_UPPERCASE = f'{string.ascii_uppercase}{PL_UPPERCASE}'

Image = cv2.typing.MatLike
SimpleRGB = tuple[int, int, int]
ImagePoints = Sequence[cv2.typing.MatLike]


class DifflanekException(Exception):
    pass


class NoGreenRectangleFound(DifflanekException):
    pass


class TolerantDefaultDict(defaultdict):
    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        for tolerance_key in (key - 1, key + 1):
            if tolerance_key in self:
                return super().__getitem__(tolerance_key)
        return super().__getitem__(key)


class Colour:
    class RGB(NamedTuple):
        r: int
        g: int
        b: int

        @property
        def hex(self) -> str:
            return f'#{self.r:02x}{self.g:02x}{self.b:02x}'

        def __str__(self) -> str:
            return self.hex

        def __repr__(self) -> str:
            return self.hex


    def __init__(self, hex: str) -> None:
        hex = hex.lstrip('#')
        if not len(hex) == 6:
            raise ValueError(hex)

        self.colour = Colour.RGB(
            r=int(hex[0:2], 16),
            b=int(hex[4:6], 16),
            g=int(hex[2:4], 16),
        )

    @property
    def hsv(self) -> tuple[int, int, int]:
        return colorsys.rgb_to_hsv(
            self.rgb.r / 255.0,
            self.rgb.g / 255.0,
            self.rgb.b / 255.0,
        )

    @property
    def rgb(self) -> Colour.RGB:
        return self.colour

    @classmethod
    def from_rgb(cls, rgb) -> Colour:
        return cls(
            f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}',
        )

    def __str__(self) -> str:
        return str(self.rgb)

    def __repr__(self) -> str:
        return str(self.rgb)

    def __eq__(self, other) -> bool:
        if isinstance(other, Colour):
            return self.rgb.hex == other.rgb.hex
        else:
            return NotImplemented


GREEN = Colour('#4FB061')
YELLOW = Colour('#B29446')
GREY = Colour('#414141')

BACKGROUND = Colour('#222222')

COLOUR_TO_NAME = {
    str(GREEN): 'green',
    str(YELLOW): 'yellow',
    str(GREY): 'grey',
}


class BoundingRect:
    X = 0
    Y = 1
    WIDTH = 2
    HEIGHT = 3

    def __init__(self, contour: Image) -> None:
        self.contour = contour

    @property
    def x(self) -> int:
        return self.contour[self.X]

    @property
    def y(self) -> int:
        return self.contour[self.Y]

    @property
    def width(self) -> int:
        return self.contour[self.WIDTH]

    @property
    def height(self) -> int:
        return self.contour[self.HEIGHT]

    @classmethod
    def from_contours(cls, contours) -> list[BoundingRect]:
        return [cls(contour) for contour in contours]


class Img:

    def __init__(
        self,
        *,
        image: Image | None = None,
        path: str | None = None,
    ) -> None:
        assert image is not None or path is not None
        if image is not None:
            self.image = image

        elif path is not None:
            self.image = cv2.imread(path)
        else:
            ValueError('unreachable')

    @property
    def rgb(self) -> Image:
        return cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)

    @property
    def hsv(self) -> Image:
        return cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)

    @property
    def grayscale(self) -> Image:
        return cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

    def find_contours(
        self,
        colour: Colour | None = None,
    ) -> Contours:
        if colour is not None:
            mask = cv2.inRange(self.rgb, colour.rgb, colour.rgb)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return Contours(contours)
        else:
            assert False
            _, thresh = cv2.threshold(self.grayscale, 127, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return Contours(contours)


    def get_subimage(self, points: Image) -> Img:
        x, y, w, h = cv2.boundingRect(points)
        subimage = self.image[y:y+h, x:x+w]
        return Img(image=subimage)

    def get_mask(self, colour: Colour | list[Colour], negate: bool = False) -> Img:
        def colour_range(colour: Colour | tuple[Colour, Colour]) -> tuple[SimpleRGB, SimpleRGB]:
            if isinstance(colour, Colour):
                return colour.rgb, colour.rgb
            else:
                return colour[0].rgb, colour[1].rgb
        first, *rest = colour if isinstance(colour, list) else [colour]
        first_mask = cv2.inRange(self.rgb, *colour_range(first))
        for colour in rest:
            mask = cv2.inRange(self.rgb, *colour_range(colour))
            first_mask = cv2.bitwise_or(first_mask, mask)
        if negate:
            first_mask = cv2.bitwise_not(first_mask)
        # preview_image(first_mask)
        return Img(image=first_mask)

    def detect_text(self, *, restrict_characters: str = '') -> str:
        """
        tesseract --help-psm

        Page segmentation modes:
        0    Orientation and script detection (OSD) only.
        1    Automatic page segmentation with OSD.
        2    Automatic page segmentation, but no OSD, or OCR. (not implemented)
        3    Fully automatic page segmentation, but no OSD. (Default)
        4    Assume a single column of text of variable sizes.
        5    Assume a single uniform block of vertically aligned text.
        6    Assume a single uniform block of text.
        7    Treat the image as a single text line.
        8    Treat the image as a single word.
        9    Treat the image as a single word in a circle.
        10    Treat the image as a single character.
        11    Sparse text. Find as much text as possible in no particular order.
        12    Sparse text with OSD.
        13    Raw line. Treat the image as a single text line,
            bypassing hacks that are Tesseract-specific.
        """
        config = '--psm 7'
        if restrict_characters:
            config = f'{config} -c tessedit_char_whitelist="{restrict_characters}"'
        detected_text = pytesseract.image_to_string(
            self.image,
            config=config,
            lang='pol',
        )
        return detected_text

    def most_common_colour(self) -> Colour:
        pixels = self.image.reshape(-1, 3)
        pixels = [tuple(p) for p in pixels]
        counter = Counter(pixels)
        most_common_color = counter.most_common(1)[0][0]
        hex_colour = '#{:02x}{:02x}{:02x}'.format(most_common_color[2], most_common_color[1], most_common_color[0])
        return Colour(hex_colour)

    def get_pixel_colour(self, y, x) -> Colour:
        pixel = self.rgb[y, x]
        hex_colour = '#{:02x}{:02x}{:02x}'.format(pixel[0], pixel[1], pixel[2])
        return Colour(pixel)

class Contours:
    def __init__(self, contours: ImagePoints) -> None:
        self.contours = contours

    def rectangles(self) -> Contours:
        def approximate_polygon(contour: Image) -> Image:
            return cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        rectangles = [
            polygon
            for polygon in map(approximate_polygon, self.contours)
            if len(polygon) == 4
        ]
        return Contours(rectangles)

    @classmethod
    def from_image(cls, image: Image) -> Contours:
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return cls(contours)

    def sorted(self, by = None) -> Contours:
        rects = BoundingRect.from_contours(self.contours)
        rects = sorted(rects, key=lambda r: r.y)
        return Contours(list(map(lambda x: x.contour, rects)))

    def as_bounding(self) -> list[BoundingRect]:
        return BoundingRect.from_contours(self.contours)


def is_polish(image: Img) -> bool | None:
    detected_text = Img(image=image.image[0:50, 0:600]).detect_text()
    return {
        'Hasło zawiera chociaż jeden polski znak.': True,
    }.get(detected_text)


def preview_image(image: Image, title: str = '') -> None:
    # Display the extracted region and the OCR result
    plt.figure()
    plt.imshow(image)
    plt.title(title)
    plt.axis('off')
    plt.show()


def get_biggest_rectangle(image: Img) -> Image | None:
    green_mask = cv2.inRange(image.rgb, GREEN.rgb, GREEN.rgb)
    rectangles = Contours.from_image(green_mask).contours
    if not rectangles:
        return None
    biggest_rectangle = sorted(rectangles, key=lambda x: cv2.contourArea(x), reverse=True)[0]
    return biggest_rectangle


def draw_contours(image, contours):
    """Draw bounding boxes around contours on the image."""
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)


def text_to_difflanek(text: str, colour: str, left_closed: bool, right_closed: bool) -> str:
    if colour == GREY:
        return text.lower()
    if colour == YELLOW:
        return text.upper()
    left_bracket = '[' if left_closed else '('
    right_bracket = ']' if right_closed else ')'
    return f'{left_bracket}{text}{right_bracket}'


def get_difflanek(image: Img | bytes, *, debug: bool = False) -> list[str]:
    if isinstance(image, bytes):
        nparr = np.fromstring(image, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        image = Img(image=img)
    ret = []
    rectangle = get_biggest_rectangle(image)
    if rectangle is None:
        raise NoGreenRectangleFound
    biggest_rectangle = image.get_subimage(points=rectangle)

    green_contours = image.find_contours(colour=GREEN)
    yellow_contours = image.find_contours(colour=YELLOW)
    grey_contours = image.find_contours(colour=GREY)

    def filter_contour_by_min_area(contours, min_area: int = 300):
        return [
            contour for contour in contours.contours
            if cv2.contourArea(contour) > min_area
        ]

    def filter_success_badge(contours, biggest_rectangle):
        return [
            contour for contour in contours
            if cv2.boundingRect(contour)[BoundingRect.Y] <= cv2.boundingRect(biggest_rectangle)[BoundingRect.Y]
        ]

    green_contours = filter_contour_by_min_area(green_contours)
    green_contours = filter_success_badge(green_contours, rectangle)

    yellow_contours = filter_contour_by_min_area(yellow_contours)
    grey_contours = filter_contour_by_min_area(grey_contours)

    def group_shapes_by_y(contours) -> defaultdict[list]:
        groups = defaultdict(list)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            groups[y].append(contour)
        return groups

    green_groups = group_shapes_by_y(green_contours)
    yellow_groups = group_shapes_by_y(yellow_contours)
    grey_groups = group_shapes_by_y(grey_contours)
    groups = TolerantDefaultDict(list)
    for group in [green_groups, yellow_groups, grey_groups]:
        for y, contours in group.items():
            groups[y].extend(contours)

    i = image.image

    colours_ignore = [
        (Colour('#000000'), GREEN),
        (Colour('#000000'), YELLOW),
        (Colour('#000000'), GREY),
    ]

    colours_get = [
        # idk tbf
        (Colour('#B5F4FD'), Colour('#FFFFFF')),
        (Colour('#FDF6C0'), Colour('#FFFFFF')),

        # grey on grey
        (Colour('#4D5964'), Colour('#6D6D6D')),
        (Colour('#4B4341'), Colour('#6D6D6D')),

        # white on green
        (Colour('#F4FAF5'), Colour('#FFFFFF')),
        (Colour('#BBE0C2'), Colour('#FFFFFF')),

        # white on yellow
        (Colour('#CFCBB9'), Colour('#FFFFFF')),
        (Colour('#D5A448'), Colour('#FFFFFF')),

    ]

    groups = sorted(groups.items(), key=lambda x: x[0])
    # groups = groups[0:][:1]
    ret = []
    for y, group in groups:
        difflanek = ''
        for chunk in sorted(group, key=lambda x: cv2.boundingRect(x)[BoundingRect.X]):
            d = cv2.boundingRect(chunk)
            chunk_image = image.get_subimage(chunk)
            # preview_image(chunk_image.rgb)

            _i = image.get_subimage(chunk)
            text = image.get_subimage(chunk).get_mask(colour=colours_get, negate=False).detect_text(restrict_characters=ALL_UPPERCASE).strip()

            mc = image.get_subimage(chunk).most_common_colour()
            # mc = COLOUR_TO_NAME.get(str(mc))

            # top_left = Colour.from_rgb(image.rgb[d[BoundingRect.X], d[BoundingRect.Y]])
            # top_right = Colour.from_rgb(image.rgb[d[BoundingRect.X] + d[BoundingRect.WIDTH], d[BoundingRect.Y]])

            top_left = Colour.from_rgb(chunk_image.rgb[0, 0])
            top_right = Colour.from_rgb(chunk_image.rgb[0, -1])
            # print(BACKGROUND, top_left, top_right)
            _difflanek_tmp = text_to_difflanek(text, mc, left_closed=top_left != BACKGROUND, right_closed=top_right != BACKGROUND)
            difflanek += _difflanek_tmp

            # print(f'> {d} > {mc} > ', text)
        # print(f'> {difflanek} > ')
        ret.append(difflanek)

        draw_contours(i, group)

    if debug:
        cv2.imshow('Contours with same row height', i)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return ret
