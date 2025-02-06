local data = require('data')
local sprite = require('sprite')

-- Phone to Frame flags
-- TODO sample messages only
USER_SPRITE = 0x20

-- register the message parsers so they are automatically called when matching data comes in
data.parsers[USER_SPRITE] = sprite.parse_sprite


-- Main app loop
function app_loop()
	print("Main App Running")
	frame.display.text("Main App Running", 1, 1)
	frame.display.show()

	while true do
        rc, err = pcall(
            function()
				-- process any raw data items, if ready
				local items_ready = data.process_raw_items()

				-- one or more full messages received
				if items_ready > 0 then
					print("Items Ready: " .. items_ready)

					if (data.app_data[USER_SPRITE] ~= nil) then
						-- show the sprite
						local spr = data.app_data[USER_SPRITE]
						frame.display.bitmap(1, 1, spr.width, 2^spr.bpp, 0, spr.pixel_data)
						frame.display.show()

						data.app_data[USER_SPRITE] = nil
					end

				end

				-- can't sleep for long, might be lots of incoming bluetooth data to process
				frame.sleep(0.001)
			end
		)
		-- Catch the break signal here and clean up the display
		if rc == false then
			-- send the error back on the stdout stream
			print(err)
			frame.display.text(" ", 1, 1)
			frame.display.show()
			frame.sleep(0.04)
			break
		end
	end
end

-- run the main app loop
app_loop()