print("Loading battery.lua...")  -- Debugging message

-- Module handling periodic battery level reports on a standard message code
local _M = {}

-- Frame to phone flags
local BATTERY_MSG = 0x0c

function _M.send_batt_if_elapsed(prev, interval)
    local t = frame.time.utc()

    -- if prev is not defined set it to 0
    if prev == nil then
        prev = 0
    end

    if ((prev == 0) or ((t - prev) > interval)) then
        pcall(frame.bluetooth.send, string.char(BATTERY_MSG) .. string.char(math.floor(frame.battery_level())))
        return t
    else
        return prev
    end
end

print("Loaded battery.lua")  -- Debugging message

return _M