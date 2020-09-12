import network

# Connect to Wi-Fi
sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    print('connecting to network...')
    sta_if.active(True)
    sta_if.connect('<ssid here>', '<password here>')
    while not sta_if.isconnected():
        pass
print('network config:', sta_if.ifconfig())

# Disable MicroPython access point
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

