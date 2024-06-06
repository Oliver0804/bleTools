import asyncio
from bleak import BleakScanner, BleakClient, BleakError
from colorama import init, Fore
from datetime import datetime
import os

# 初始化 colorama
init(autoreset=True)

TARGET_PREFIX = "Lapita_"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"  # 電池電量特徵 UUID
CURRENT_TIME_UUID = "00002a2b-0000-1000-8000-00805f9b34fb"  # 當前時間特徵 UUID
DEVICE_INFORMATION_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"  # 裝置資訊服務 UUID
MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"  # 型號編號特徵 UUID
FIRMWARE_VERSION_UUID = "00002a26-0000-1000-8000-00805f9b34fb"  # 韌體版本特徵 UUID
HARDWARE_VERSION_UUID = "00002a27-0000-1000-8000-00805f9b34fb"  # 硬體版本特徵 UUID
MANUFACTURER_NAME_UUID = "00002a29-0000-1000-8000-00805f9b34fb"  # 製造商名稱特徵 UUID
TX_POWER_UUID = "00002a07-0000-1000-8000-00805f9b34fb"  # 發射功率特徵 UUID
LED_SERVICE_UUID = "0000ffc0-0000-1000-8000-00805f9b34fb"  # LED服務 UUID
LED_MODE_CHAR_UUID = "0000ffc1-0000-1000-8000-00805f9b34fb"  # LED模式特徵 UUID
LED_SETTING_CHAR_UUID = "0000ffc2-0000-1000-8000-00805f9b34fb"  # LED設定特徵 UUID
BUTTON_CHAR_UUID = "0000ffc3-0000-1000-8000-00805f9b34fb"  # 按鈕特徵 UUID
MOTION_SERVICE_UUID = "00001600-0000-1000-8000-00805f9b34fb"  # Motion 服務 UUID
MOTION_MEASUREMENT_CHAR_UUID = "00001601-0000-1000-8000-00805f9b34fb"  # Motion measurement 特徵 UUID

MAC_FILE_PATH = "MacID.txt"
button_pushed = False
imu_data_received = False

async def scan_devices():
    print(Fore.CYAN + "Scanning for devices...")
    devices = await BleakScanner.discover()
    if not devices:
        print(Fore.RED + "No devices found.")
        return []
    
    target_devices = [device for device in devices if device.name and device.name.startswith(TARGET_PREFIX)]
    if not target_devices:
        print(Fore.RED + f"No devices found with name starting with {TARGET_PREFIX}.")
        return []

    print(Fore.GREEN + f"Found devices with name starting with {TARGET_PREFIX}:")
    for i, device in enumerate(target_devices):
        print(f"{Fore.YELLOW}{i}: {device.name} ({device.address})")
    return target_devices

def select_device(devices):
    while True:
        try:
            choice = int(input(Fore.CYAN + f"Enter the number of the device you want to connect to (0-{len(devices)-1}): "))
            if 0 <= choice < len(devices):
                return devices[choice]
            else:
                print(Fore.RED + f"Please enter a number between 0 and {len(devices)-1}.")
        except ValueError:
            print(Fore.RED + "Invalid input. Please enter a number.")

async def read_battery_level(client):
    print(Fore.CYAN + "Reading battery level...")
    try:
        battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
        print(Fore.GREEN + f"Battery Level: {int(battery_level[0])}%")
    except Exception as e:
        print(Fore.RED + f"Failed to read battery level: {e}")

async def read_device_information(client):
    print(Fore.CYAN + "Reading device information...")
    try:
        manufacturer_name = await client.read_gatt_char(MANUFACTURER_NAME_UUID)
        print(Fore.GREEN + f"Manufacturer Name: {manufacturer_name.decode('utf-8')}")
    except Exception as e:
        print(Fore.RED + f"Failed to read manufacturer name: {e}")

    try:
        model_number = await client.read_gatt_char(MODEL_NUMBER_UUID)
        print(Fore.GREEN + f"Model Number: {model_number.decode('utf-8')}")
    except Exception as e:
        print(Fore.RED + f"Failed to read model number: {e}")

    try:
        firmware_version = await client.read_gatt_char(FIRMWARE_VERSION_UUID)
        print(Fore.GREEN + f"Firmware Version: {firmware_version.decode('utf-8')}")
    except Exception as e:
        print(Fore.RED + f"Failed to read firmware version: {e}")

    try:
        hardware_version = await client.read_gatt_char(HARDWARE_VERSION_UUID)
        print(Fore.GREEN + f"Hardware Version: {hardware_version.decode('utf-8')}")
    except Exception as e:
        print(Fore.RED + f"Failed to read hardware version: {e}")

async def read_tx_power(client):
    print(Fore.CYAN + "Reading TX power...")
    try:
        tx_power = await client.read_gatt_char(TX_POWER_UUID)
        print(Fore.GREEN + f"TX Power: {int(tx_power[0])} dBm")
    except Exception as e:
        print(Fore.RED + f"Failed to read TX power: {e}")

async def read_current_time(client):
    print(Fore.CYAN + "Reading current time...")
    try:
        current_time = await client.read_gatt_char(CURRENT_TIME_UUID)
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(Fore.GREEN + f"Current Time: {current_time_str}")
    except Exception as e:
        print(Fore.RED + f"Failed to read current time: {e}")

async def set_led_mode(client, mode):
    print(Fore.CYAN + f"Setting LED mode to {'ON' if mode == 0x01 else 'OFF'}...")
    try:
        await client.write_gatt_char(LED_MODE_CHAR_UUID, bytearray([mode]))
        print(Fore.GREEN + f"Set LED mode to {'ON' if mode == 0x01 else 'OFF'}")
    except Exception as e:
        print(Fore.RED + f"Failed to set LED mode: {e}")

async def set_led_setting(client, red, green, blue, blink_mode, blink_period):
    print(Fore.CYAN + f"Setting LED color to RGB({red}, {green}, {blue}), mode: {blink_mode}, period: {blink_period}...")
    try:
        command = bytearray([red, green, blue, blink_mode, blink_period])
        await client.write_gatt_char(LED_SETTING_CHAR_UUID, command)
        print(Fore.GREEN + f"Set LED color to RGB({red}, {green}, {blue}), mode: {blink_mode}, period: {blink_period}")
    except Exception as e:
        print(Fore.RED + f"Failed to set LED setting: {e}")

def button_callback(sender: int, data: bytearray):
    global button_pushed
    if data[0] == 0x01:
        print(Fore.GREEN + "BUTTON1 pushed")
        button_pushed = True
    elif data[0] == 0x10:
        print(Fore.GREEN + "BUTTON2 pushed")
        button_pushed = True
    elif data[0] == 0x11:
        print(Fore.GREEN + "Both BUTTON1 and BUTTON2 pushed")
        button_pushed = True

async def monitor_button(client):
    global button_pushed
    print(Fore.CYAN + "Press BUTTON1 or BUTTON2 within the next 5 seconds...")
    try:
        await client.start_notify(BUTTON_CHAR_UUID, button_callback)
        await asyncio.sleep(5)
        await client.stop_notify(BUTTON_CHAR_UUID)
        if not button_pushed:
            print(Fore.RED + "No button pushed within 5 seconds.")
    except Exception as e:
        print(Fore.RED + f"Failed to monitor button: {e}")

def parse_imu_data(data):
    ax = int.from_bytes(data[0:2], byteorder='little', signed=True)
    ay = int.from_bytes(data[2:4], byteorder='little', signed=True)
    az = int.from_bytes(data[4:6], byteorder='little', signed=True)
    gx = int.from_bytes(data[6:8], byteorder='little', signed=True)
    gy = int.from_bytes(data[8:10], byteorder='little', signed=True)
    gz = int.from_bytes(data[10:12], byteorder='little', signed=True)
    return ax, ay, az, gx, gy, gz

def imu_callback(sender: int, data: bytearray):
    global imu_data_received
    imu_data_received = True
    ax, ay, az, gx, gy, gz = parse_imu_data(data)
    print(Fore.CYAN + f"IMU data: AX={ax}, AY={ay}, AZ={az}, GX={gx}, GY={gy}, GZ={gz}")

async def monitor_imu(client):
    global imu_data_received
    imu_data_received = False
    print(Fore.CYAN + "Monitoring IMU data...")
    try:
        await client.start_notify(MOTION_MEASUREMENT_CHAR_UUID, imu_callback)
        await asyncio.sleep(5)
        await client.stop_notify(MOTION_MEASUREMENT_CHAR_UUID)
        if not imu_data_received:
            print(Fore.RED + "No IMU data received within 5 seconds.")
    except Exception as e:
        print(Fore.RED + f"Failed to monitor IMU data: {e}")

def log_mac_address(address):
    if os.path.exists(MAC_FILE_PATH):
        with open(MAC_FILE_PATH, 'r') as f:
            mac_addresses = f.read().splitlines()
        if address in mac_addresses:
            print(Fore.YELLOW + f"Device {address} has already been tested.")
            return
    else:
        mac_addresses = []

    with open(MAC_FILE_PATH, 'a') as f:
        f.write(address + '\n')
    print(Fore.GREEN + f"MAC address {address} logged.")

async def run():
    devices = await scan_devices()
    if not devices:
        return

    target_device = select_device(devices)
    print(Fore.CYAN + f"Connecting to device {target_device.name} ({target_device.address})")

    try:
        async with BleakClient(target_device.address) as client:
            print(Fore.GREEN + f"Connected: {client.is_connected}")

            try:
                await read_battery_level(client)
            except Exception as e:
                print(Fore.RED + f"Error in read_battery_level: {e}")

            try:
                await read_device_information(client)
            except Exception as e:
                print(Fore.RED + f"Error in read_device_information: {e}")

            try:
                await read_tx_power(client)
            except Exception as e:
                print(Fore.RED + f"Error in read_tx_power: {e}")

            try:
                await read_current_time(client)
            except Exception as e:
                print(Fore.RED + f"Error in read_current_time: {e}")

            try:
                # 啟用 LED
                await set_led_mode(client, 0x01)
            except Exception as e:
                print(Fore.RED + f"Error in set_led_mode(ON): {e}")

            try:
                # 設置 LED 顏色和模式
                await set_led_setting(client, 0xFF, 0x00, 0x00, 0x02, 0x00)  # 紅色
                await asyncio.sleep(1)
                await set_led_setting(client, 0x00, 0xFF, 0x00, 0x02, 0x00)  # 綠色
                await asyncio.sleep(1)
                await set_led_setting(client, 0x00, 0x00, 0xFF, 0x02, 0x00)  # 藍色
                await asyncio.sleep(1)
            except Exception as e:
                print(Fore.RED + f"Error in set_led_setting: {e}")

            try:
                # 停用 LED
                await set_led_mode(client, 0x00)
            except Exception as e:
                print(Fore.RED + f"Error in set_led_mode(OFF): {e}")

            try:
                # 監視按鈕狀態
                await monitor_button(client)
            except Exception as e:
                print(Fore.RED + f"Error in monitor_button: {e}")

            try:
                # 監視 IMU 數據
                await monitor_imu(client)
            except Exception as e:
                print(Fore.RED + f"Error in monitor_imu: {e}")

            # 記錄MAC地址
            log_mac_address(target_device.address)

    except Exception as e:
        print(Fore.RED + f"Failed to connect to the device: {e}")

if __name__ == "__main__":
    asyncio.run(run())
