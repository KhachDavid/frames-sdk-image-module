import asyncio
from pathlib import Path
from frame_sdk import Frame
from TxSprite import TxSprite
from PIL import Image

async def send_in_chunks(f, msg_code, payload):
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

        print(f"Sending chunk: {len(chunk)} bytes (offset: {sent_bytes}/{total_size})")

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
    """Load a pre-existing image, process it to black & white, and send it to Frame in chunks."""

    print(f"Loading image: {image_path}")

    # Load image and convert to black & white (1-bit mode: only black and white pixels)
    img = Image.open(image_path).convert("L")  # Convert to grayscale
    img = img.point(lambda x: 0 if x < 128 else 255, "1")  # Convert to pure black & white
    img = img.resize((200, 200))  # Resize for Frame compatibility

    # Save the processed image as PNG (for debugging)
    processed_image_path = "processed_sprite_bw.png"
    img.save(processed_image_path)
    print(f"Black & white image saved as: {processed_image_path}")

    # Pack the image into a TxSprite object
    sprite = TxSprite(msg_code=0x20, image_path=processed_image_path, num_colors=2)  # Only 2 colors (B/W)
    packed_data = sprite.pack()

    # Check the size of the packed payload
    print(f"Packed sprite payload size: {len(packed_data)} bytes")

    # Send the packed data to Frame in BLE-compatible chunks
    try:
        print("Sending black & white image data in BLE-compatible chunks...")
        await send_in_chunks(f, sprite.msg_code, packed_data)
        print("Black & white image successfully sent!")
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
    await f.files.write_file("data.lua", Path("lua/data.lua").read_bytes())
    await f.files.write_file("sprite.lua", Path("lua/sprite.lua").read_bytes())
    # send the main lua file to Frame that will run the app to display the sprite when the message arrives
    await f.files.write_file("frame_app.lua", Path("lua/frame_app.lua").read_bytes())

    # "require" the main lua file to run it
    await f.run_lua("require('frame_app')print('done')", await_print=True)

    temp_file = "test_photo_0.jpg"
    await process_and_send_image(f, temp_file)

    await asyncio.sleep(1.0)

    # clean disconnection
    await f.bluetooth.disconnect()

if __name__ == "__main__":
    asyncio.run(main())