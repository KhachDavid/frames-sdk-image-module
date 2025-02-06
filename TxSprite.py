from PIL import Image
import numpy as np
import struct

class TxSprite:
    def __init__(self, msg_code, image_path, num_colors=16):
        self.msg_code = msg_code
        self.num_colors = num_colors  # Number of palette colors

        self.image = Image.open(image_path).convert("RGB")
        # Convert to indexed image with the specified number of colors
        self.image = self.image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)

        # Extract palette and image details
        self.palette = self.image.getpalette()[: self.num_colors * 3]  # RGB Palette
        self.pixel_data = list(self.image.getdata())
        self.width, self.height = self.image.size
        self.bpp = self.calculate_bpp()  # Bits per pixel based on num_colors

    def calculate_bpp(self):
        """Determine bits per pixel based on the number of colors."""
        if self.num_colors <= 16:  # 16 colors max -> 4 bits
            return 4
        elif self.num_colors <= 64:  # 64 colors max -> 6 bits
            return 6
        elif self.num_colors <= 256:  # 256 colors max -> 8 bits
            return 8
        raise ValueError("Frame supports a maximum of 256 colors.")

    def pack(self):
        """Pack the sprite into a binary format for Frame."""
        width_msb = self.width >> 8
        width_lsb = self.width & 0xFF
        height_msb = self.height >> 8
        height_lsb = self.height & 0xFF

        packed_pixels = self.pack_pixels_by_bpp(self.pixel_data, self.bpp)

        # Format: Width, Height, BPP, #Colors, Palette, Pixels
        payload = bytearray([width_msb, width_lsb, height_msb, height_lsb, self.bpp, self.num_colors])
        payload.extend(self.palette)  # Palette is RGB triplets
        payload.extend(packed_pixels)  # Add packed pixel data

        return payload

    def pack_pixels_by_bpp(self, pixel_data, bpp):
        """Pack pixel data based on bit depth."""
        if bpp == 4:  # 4 bits per pixel (16 colors)
            return self.pack_4bit(pixel_data)
        elif bpp == 6:  # 6 bits per pixel (64 colors)
            return self.pack_6bit(pixel_data)
        elif bpp == 8:  # 8 bits per pixel (256 colors)
            return bytearray(pixel_data)  # No packing needed
        else:
            raise ValueError("Unsupported bits per pixel.")

    @staticmethod
    def pack_4bit(pixel_data):
        """Pack 4-bit pixel data into bytes."""
        packed = bytearray()
        for i in range(0, len(pixel_data), 2):
            if i + 1 < len(pixel_data):
                packed.append((pixel_data[i] << 4) | (pixel_data[i + 1] & 0x0F))
            else:
                packed.append(pixel_data[i] << 4)
        return packed

    @staticmethod
    def pack_6bit(pixel_data):
        """Pack 6-bit pixel data into bytes."""
        packed = bytearray()

        for i in range(0, len(pixel_data), 4):
            # Ensure all pixel values are within 6 bits (0-63)
            p0 = pixel_data[i] & 0x3F
            p1 = pixel_data[i + 1] & 0x3F if i + 1 < len(pixel_data) else 0
            p2 = pixel_data[i + 2] & 0x3F if i + 2 < len(pixel_data) else 0
            p3 = pixel_data[i + 3] & 0x3F if i + 3 < len(pixel_data) else 0

            # First and second pixels (6 bits each -> 12 bits, split across 2 bytes)
            packed.append((p0 << 2) | (p1 >> 4))

            # Second and third pixels (remaining bits of p1 + 6 bits of p2, max 255)
            packed.append(((p1 & 0x0F) << 4) | (p2 >> 2))

            # Third and fourth pixels (remaining bits of p2 + 6 bits of p3, max 255)
            packed.append(((p2 & 0x03) << 6) | p3)

        return packed


