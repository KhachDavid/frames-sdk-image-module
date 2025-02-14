import time
import asyncio
from pathlib import Path
from frame_sdk import Frame
from TxSprite import TxSprite
from PIL import Image, ImageOps
from frame_sdk.camera import AutofocusType, Quality

async def send_in_chunks(f: Frame, msg_code, payload):
    """Send a large payload in BLE-compatible chunks."""
    max_chunk_size = f.bluetooth.max_data_payload() - 5  # Maximum BLE payload size is 240
    print(f"Max BLE payload size: {max_chunk_size}")

    total_size = len(payload)  # Total size of the payload
    sent_bytes = 0  # Tracks how many bytes have been sent so far

    while sent_bytes < total_size:
        remaining_bytes = total_size - sent_bytes  # Remaining data to send
        chunk_size = min(max_chunk_size, remaining_bytes)  # Ensure ≤ max_chunk_size

        # Extract the next chunk
        chunk = payload[sent_bytes : sent_bytes + chunk_size]

        # Add the msg_code (as the first byte of the packet) to the chunk
        if sent_bytes == 0:
            # first packet also has total payload length
            chunk_with_msg_code = bytearray([msg_code, total_size >> 8, total_size & 0xFF]) + chunk
        else:
            chunk_with_msg_code = bytearray([msg_code]) + chunk

        # Send the chunk
        await f.bluetooth.send_data(chunk_with_msg_code)
        sent_bytes += chunk_size

        # Optional: Small delay to avoid overwhelming BLE
        await asyncio.sleep(0.01)

    print("All chunks sent successfully!")

async def process_and_send_image(f: Frame, image_path: str):
    """Load a pre-existing image, process it, and send it to Frame in chunks."""

    print(f"Loading preloaded image: {image_path}")

    #  Load image and convert to indexed color mode (Palette Mode)
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)  # Automatically correct rotation based on EXIF metadata
    img = img.convert("RGB")  # Convert to RGB Mode

    # Resize the image to fit the Frame's display
    target_size = (320, 200)
    img.thumbnail(target_size, Image.LANCZOS)  # Resize while keeping aspect ratio

    # Create a blank image (padded background) in the target size
    padded_img = Image.new("RGB", target_size, (0, 0, 0))  # Black background
    x_offset = (target_size[0] - img.width) // 2  # Center horizontally
    y_offset = (target_size[1] - img.height) // 2  # Center vertically
    padded_img.paste(img, (x_offset, y_offset))  # Paste resized img onto background

    # Convert to indexed color (16-color palette mode)
    padded_img = padded_img.convert("P", palette=Image.ADAPTIVE, colors=16)

    # Save processed image for debugging/testing
    processed_image_path = "processed_sprite.png"
    padded_img.save(processed_image_path)
    print(f"Image processed and saved as: {processed_image_path}")

    # Pack the image into a TxSprite object
    sprite = TxSprite(msg_code=0x20, image_path=processed_image_path)
    packed_data = sprite.pack()

    # Check the size of the packed payload
    print(f"Packed sprite payload size: {len(packed_data)} bytes")

    # Send the packed data to Frame in chunks
    try:
        print("Sending image data in BLE-compatible chunks...")
        await send_in_chunks(f, sprite.msg_code, packed_data)
        print("Image successfully sent!")
    except Exception as e:
        print(f"Failed to send image: {e}")

async def main():
    #await check_camera_feed()
    f = Frame()
    try:
        await f.ensure_connected()
    except Exception as e:
        print(f"An error occurred while connecting to the Frame: {e}")
        await f.ensure_connected()

    print(f"Connected: {f.bluetooth.is_connected()}")

    # Send a break signal to Frame in case it has a loop running
    # and give it a moment
    await f.bluetooth.send_break_signal()
    await asyncio.sleep(0.1)

    f.bluetooth.print_response_handler = print

    # send the std lua files to Frame that handle data accumulation and sprite parsing
    await f.display.show_text("Loading...")
    # send the main lua file to Frame that will run the app to display the sprite when the message arrives
    await f.files.write_file("data.lua", Path("lua/data.lua").read_bytes())
    await f.files.write_file("battery.lua", Path("lua/battery.lua").read_bytes())
    await f.files.write_file("camera.lua", Path("lua/camera.lua").read_bytes())
    await f.files.write_file("code.lua", Path("lua/code.lua").read_bytes())
    await f.files.write_file("plain_text.lua", Path("lua/plain_text.lua").read_bytes())
    await f.files.write_file("sprite.lua", Path("lua/sprite.lua").read_bytes())
    await f.files.write_file("frame_app.lua", Path("lua/frame_app.lua").read_bytes())

    # "require" the main lua file to run it
    await f.run_lua("require('frame_app')", await_print=False)
    time.sleep(10)
    temp_file = "test_photo_0.jpg"
    print("Sending image to Frame...")
    await process_and_send_image(f, temp_file)

    time.sleep(5)

    resolution = 320
    pan = 0
    resolution_half = resolution // 2   # Lua expects half-resolution
    pan_shifted = pan + 140             # Reverse shift calculation
    raw = 0                             # Do not send raw image data

    # Save the photo to a file
    # await f.camera.save_photo("test_photo_1.jpg", autofocus_seconds=3, quality=Quality.MEDIUM, autofocus_type=AutofocusType.CENTER_WEIGHTED)
    lua_command = f"camera.capture_and_send({Quality.MEDIUM}, {resolution_half}, {pan_shifted}, {int(raw)})"

    await f.bluetooth.send_lua(lua_command)
    image_buffer = await f.bluetooth.wait_for_data()

    if image_buffer is None or len(image_buffer) == 0:
        raise Exception("Failed to get photo")

    # Handle possible unwanted tap data
    while image_buffer[0] == 0x04 and len(image_buffer) < 5:
        print("Ignoring tap data while waiting for photo")
        image_buffer = await f.bluetooth.wait_for_data()

        if image_buffer is None or len(image_buffer) == 0:
            raise Exception("Failed to get photo")

    # clean disconnection
    await f.bluetooth.disconnect()

if __name__ == "__main__":
    asyncio.run(main())