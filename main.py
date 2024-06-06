import asyncio
import threading
import queue
from bleak import BleakScanner, BleakClient
from colorama import init, Fore
from datetime import datetime
import os
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
CTS_SERVICE_UUID = "00001805-0000-1000-8000-00805f9b34fb"  # Current Time Service UUID
CTS_CHARACTERISTIC_UUID = "00002a2b-0000-1000-8000-00805f9b34fb"  # Current Time Characteristic UUID

MAC_FILE_PATH = "MacID.txt"
button_pushed_count = 0
imu_data_received = False
recording = False
imu_log_file = None
stop_monitoring = False
connected_device = None

# 初始化 IMU 數據存儲
imu_data = {
    "timestamps": [],
    "ax": [],
    "ay": [],
    "az": [],
    "gx": [],
    "gy": [],
    "gz": []
}

# 創建隊列用於從回調中傳遞IMU數據
imu_queue = queue.Queue()

async def scan_devices():
    print_to_terminal("Scanning for devices...", Fore.CYAN)
    devices = await BleakScanner.discover()
    if not devices:
        print_to_terminal("No devices found.", Fore.RED)
        return []
    
    target_devices = [device for device in devices if device.name and device.name.startswith(TARGET_PREFIX)]
    if not target_devices:
        print_to_terminal(f"No devices found with name starting with {TARGET_PREFIX}.", Fore.RED)
        return []

    print_to_terminal(f"Found devices with name starting with {TARGET_PREFIX}:", Fore.GREEN)
    for i, device in enumerate(target_devices):
        print_to_terminal(f"{i}: {device.name} ({device.address})", Fore.YELLOW)
    return target_devices

def print_to_terminal(message, color=Fore.WHITE):
    terminal_text.config(state=tk.NORMAL)
    terminal_text.insert(tk.END, message + "\n", color)
    terminal_text.config(state=tk.DISABLED)
    terminal_text.see(tk.END)

def select_device(devices):
    while True:
        try:
            choice = int(input(f"Enter the number of the device you want to connect to (0-{len(devices)-1}): "))
            if 0 <= choice < len(devices):
                return devices[choice]
            else:
                print(f"Please enter a number between 0 and {len(devices)-1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

async def read_battery_level(client):
    print_to_terminal("Reading battery level...", Fore.CYAN)
    try:
        battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
        print_to_terminal(f"Battery Level: {int(battery_level[0])}%", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read battery level: {e}", Fore.RED)

async def read_device_information(client):
    print_to_terminal("Reading device information...", Fore.CYAN)
    try:
        manufacturer_name = await client.read_gatt_char(MANUFACTURER_NAME_UUID)
        print_to_terminal(f"Manufacturer Name: {manufacturer_name.decode('utf-8')}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read manufacturer name: {e}", Fore.RED)

    try:
        model_number = await client.read_gatt_char(MODEL_NUMBER_UUID)
        print_to_terminal(f"Model Number: {model_number.decode('utf-8')}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read model number: {e}", Fore.RED)

    try:
        firmware_version = await client.read_gatt_char(FIRMWARE_VERSION_UUID)
        print_to_terminal(f"Firmware Version: {firmware_version.decode('utf-8')}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read firmware version: {e}", Fore.RED)

    try:
        hardware_version = await client.read_gatt_char(HARDWARE_VERSION_UUID)
        print_to_terminal(f"Hardware Version: {hardware_version.decode('utf-8')}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read hardware version: {e}", Fore.RED)

async def read_tx_power(client):
    print_to_terminal("Reading TX power...", Fore.CYAN)
    try:
        tx_power = await client.read_gatt_char(TX_POWER_UUID)
        print_to_terminal(f"TX Power: {int(tx_power[0])} dBm", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read TX power: {e}", Fore.RED)

async def write_current_time(client):
    now = datetime.now()
    year = now.year.to_bytes(2, byteorder='little')
    data = bytearray([
        year[0], year[1],
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second
    ])
    print_to_terminal(f"Writing current time: {data.hex()}", Fore.CYAN)
    try:
        await client.write_gatt_char(CTS_CHARACTERISTIC_UUID, data)
        print_to_terminal("Current time written successfully.", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to write current time: {e}", Fore.RED)

async def read_current_time(client):
    print_to_terminal("Reading current time...", Fore.CYAN)
    try:
        current_time = await client.read_gatt_char(CTS_CHARACTERISTIC_UUID)
        year = int.from_bytes(current_time[0:2], byteorder='little')
        month = current_time[2]
        day = current_time[3]
        hour = current_time[4]
        minute = current_time[5]
        second = current_time[6]
        print_to_terminal(f"Current Time: {year}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to read current time: {e}", Fore.RED)

async def set_led_mode(client, mode):
    print_to_terminal(f"Setting LED mode to {'ON' if mode == 0x01 else 'OFF'}...", Fore.CYAN)
    try:
        await client.write_gatt_char(LED_MODE_CHAR_UUID, bytearray([mode]))
        print_to_terminal(f"Set LED mode to {'ON' if mode == 0x01 else 'OFF'}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to set LED mode: {e}", Fore.RED)

async def set_led_setting(client, red, green, blue, blink_mode, blink_period):
    print_to_terminal(f"Setting LED color to RGB({red}, {green}, {blue}), mode: {blink_mode}, period: {blink_period}...", Fore.CYAN)
    try:
        command = bytearray([red, green, blue, blink_mode, blink_period])
        await client.write_gatt_char(LED_SETTING_CHAR_UUID, command)
        print_to_terminal(f"Set LED color to RGB({red}, {green}, {blue}), mode: {blink_mode}, period: {blink_period}", Fore.GREEN)
    except Exception as e:
        print_to_terminal(f"Failed to set LED setting: {e}", Fore.RED)

def button_callback(sender: int, data: bytearray):
    global button_pushed_count
    if data[0] in [0x01, 0x10, 0x11]:
        button_pushed_count += 1
        print_to_terminal(f"Button pressed {button_pushed_count} times", Fore.GREEN)

async def monitor_button(client):
    global button_pushed_count
    button_pushed_count = 0
    print_to_terminal("Press any button twice to continue...", Fore.CYAN)
    try:
        await client.start_notify(BUTTON_CHAR_UUID, button_callback)
        while button_pushed_count < 2:
            await asyncio.sleep(0.1)
        await client.stop_notify(BUTTON_CHAR_UUID)
    except Exception as e:
        print_to_terminal(f"Failed to monitor button: {e}", Fore.RED)

def parse_imu_data(data):
    ax = int.from_bytes(data[0:2], byteorder='little', signed=True)
    ay = int.from_bytes(data[2:4], byteorder='little', signed=True)
    az = int.from_bytes(data[4:6], byteorder='little', signed=True)
    gx = int.from_bytes(data[6:8], byteorder='little', signed=True)
    gy = int.from_bytes(data[8:10], byteorder='little', signed=True)
    gz = int.from_bytes(data[10:12], byteorder='little', signed=True)
    return ax, ay, az, gx, gy, gz

def imu_callback(sender: int, data: bytearray):
    global imu_data_received, imu_log_file, recording
    imu_data_received = True
    ax, ay, az, gx, gy, gz = parse_imu_data(data)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    imu_data["timestamps"].append(timestamp)
    imu_data["ax"].append(ax)
    imu_data["ay"].append(ay)
    imu_data["az"].append(az)
    imu_data["gx"].append(gx)
    imu_data["gy"].append(gy)
    imu_data["gz"].append(gz)
    if recording and imu_log_file:
        imu_log_file.write(f"{timestamp},{ax},{ay},{az},{gx},{gy},{gz}\n")
    print_to_terminal(f"IMU data: {timestamp} AX={ax}, AY={ay}, AZ={az}, GX={gx}, GY={gy}, GZ={gz}", Fore.CYAN)
    imu_queue.put((timestamp, ax, ay, az, gx, gy, gz))  # 將數據放入隊列中

async def monitor_imu(client):
    global imu_data_received, imu_log_file, recording, stop_monitoring
    imu_data_received = False
    recording = True
    stop_monitoring = False
    imu_log_file = open(f"IMU_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w")
    print_to_terminal("Monitoring IMU data... Press 'Stop' to end.", Fore.CYAN)
    try:
        await client.start_notify(MOTION_MEASUREMENT_CHAR_UUID, imu_callback)
        while not stop_monitoring:
            await asyncio.sleep(0.1)
            if not client.is_connected:
                await client.connect()
        await client.stop_notify(MOTION_MEASUREMENT_CHAR_UUID)
    except Exception as e:
        print_to_terminal(f"Failed to monitor IMU data: {e}", Fore.RED)
    finally:
        if imu_log_file:
            imu_log_file.close()
        recording = False

def log_mac_address(address):
    if os.path.exists(MAC_FILE_PATH):
        with open(MAC_FILE_PATH, 'r') as f:
            mac_addresses = f.read().splitlines()
        if address in mac_addresses:
            print_to_terminal(f"Device {address} has already been tested.", Fore.YELLOW)
            return True
    else:
        mac_addresses = []

    with open(MAC_FILE_PATH, 'a') as f:
        f.write(address + '\n')
    print_to_terminal(f"MAC address {address} logged.", Fore.GREEN)
    return False

async def run_ble_operations():
    devices = await scan_devices()
    if not devices:
        return
    return devices

def run_event_loop(callback):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    devices = loop.run_until_complete(run_ble_operations())
    callback(devices)

class BLEMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BLE Monitor")
        
        self.setup_gui()
        self.ble_thread = None
        self.loop = asyncio.new_event_loop()

    def setup_gui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame for Matplotlib plot
        plot_frame = tk.Frame(main_frame)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right frame for TextBox and ListBox
        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)

        self.ax1.set_ylim(-32768, 32767)
        self.ax2.set_ylim(-32768, 32767)
        self.ax1.legend(['AX', 'AY', 'AZ'])
        self.ax2.legend(['GX', 'GY', 'GZ'])

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

        self.update_plot()

        # Terminal text box
        global terminal_text
        terminal_text = tk.Text(control_frame, wrap=tk.WORD, height=10)
        terminal_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        terminal_text.config(state=tk.DISABLED)
        terminal_text.tag_config(Fore.CYAN, foreground="cyan")
        terminal_text.tag_config(Fore.RED, foreground="red")
        terminal_text.tag_config(Fore.GREEN, foreground="green")
        terminal_text.tag_config(Fore.YELLOW, foreground="yellow")

        # Scan result ListBox
        self.scan_listbox = tk.Listbox(control_frame)
        self.scan_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.scan_listbox.bind('<<ListboxSelect>>', self.on_scan_select)

        # MAC address ListBox
        self.mac_listbox = tk.Listbox(control_frame)
        self.mac_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(control_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Scan button
        self.scan_button = ttk.Button(button_frame, text="Scan", command=self.scan_for_devices)
        self.scan_button.pack(side=tk.LEFT)

        # Stop button
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_monitoring)
        self.stop_button.pack(side=tk.LEFT)

        # Save button
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_data)
        self.save_button.pack(side=tk.LEFT)

        # Clear button
        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_plot)
        self.clear_button.pack(side=tk.LEFT)

        # Disconnect button
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_device)
        self.disconnect_button.pack(side=tk.LEFT)

        # Quit button
        self.quit_button = ttk.Button(button_frame, text="Quit", command=self.quit_app)
        self.quit_button.pack(side=tk.LEFT)

        self.update_mac_list()

    def update_plot(self):
        if not imu_queue.empty():
            while not imu_queue.empty():
                timestamp, ax, ay, az, gx, gy, gz = imu_queue.get()
                imu_data["timestamps"].append(timestamp)
                imu_data["ax"].append(ax)
                imu_data["ay"].append(ay)
                imu_data["az"].append(az)
                imu_data["gx"].append(gx)
                imu_data["gy"].append(gy)
                imu_data["gz"].append(gz)

            self.ax1.clear()
            self.ax2.clear()
            self.ax1.plot(imu_data["ax"], label='AX')
            self.ax1.plot(imu_data["ay"], label='AY')
            self.ax1.plot(imu_data["az"], label='AZ')
            self.ax2.plot(imu_data["gx"], label='GX')
            self.ax2.plot(imu_data["gy"], label='GY')
            self.ax2.plot(imu_data["gz"], label='GZ')

            self.ax1.legend()
            self.ax2.legend()
            self.canvas.draw()

        self.root.after(100, self.update_plot)

    def scan_for_devices(self):
        if self.ble_thread and self.ble_thread.is_alive():
            return

        self.scan_listbox.delete(0, tk.END)
        self.ble_thread = threading.Thread(target=run_event_loop, args=(self.update_scan_list,))
        self.ble_thread.start()

    def update_scan_list(self, devices):
        if devices:
            for device in devices:
                self.scan_listbox.insert(tk.END, f"{device.name} ({device.address})")

    def update_mac_list(self):
        self.mac_listbox.delete(0, tk.END)
        if os.path.exists(MAC_FILE_PATH):
            with open(MAC_FILE_PATH, 'r') as f:
                mac_addresses = f.read().splitlines()
            for address in mac_addresses:
                self.mac_listbox.insert(tk.END, address)

    def on_scan_select(self, event):
        selected_index = self.scan_listbox.curselection()
        if selected_index:
            selected_device_info = self.scan_listbox.get(selected_index)
            address = selected_device_info.split('(')[-1].strip(')')
            print_to_terminal(f"Selected device: {selected_device_info}", Fore.CYAN)
            self.connect_to_device(address)

    def on_mac_select(self, event):
        selected_index = self.mac_listbox.curselection()
        if selected_index:
            selected_mac = self.mac_listbox.get(selected_index)
            print_to_terminal(f"Selected MAC address: {selected_mac}", Fore.CYAN)

    def connect_to_device(self, address):
        async def connect():
            global connected_device
            try:
                connected_device = BleakClient(address)
                async with connected_device:
                    print_to_terminal(f"Connected to {address}", Fore.GREEN)
                    await read_battery_level(connected_device)
                    await read_device_information(connected_device)
                    await read_tx_power(connected_device)
                    await write_current_time(connected_device)
                    await read_current_time(connected_device)
                    await set_led_mode(connected_device, 0x01)
                    await set_led_setting(connected_device, 0xFF, 0x00, 0x00, 0x02, 0x00)  # 紅色
                    await asyncio.sleep(1)
                    await set_led_setting(connected_device, 0x00, 0xFF, 0x00, 0x02, 0x00)  # 綠色
                    await asyncio.sleep(1)
                    await set_led_setting(connected_device, 0x00, 0x00, 0xFF, 0x02, 0x00)  # 藍色
                    await asyncio.sleep(1)
                    await set_led_mode(connected_device, 0x00)
                    await monitor_button(connected_device)
                    await monitor_imu(connected_device)
            except Exception as e:
                print_to_terminal(f"Failed to connect to the device: {e}", Fore.RED)

        self.ble_thread = threading.Thread(target=lambda: asyncio.run(connect()))
        self.ble_thread.start()

    def stop_monitoring(self):
        global stop_monitoring
        stop_monitoring = True

    def save_data(self):
        if not imu_data["timestamps"]:
            print_to_terminal("No data to save.", Fore.YELLOW)
            return

        # 儲存數據到文件中
        save_thread = threading.Thread(target=self._save_data_to_file)
        save_thread.start()

    def _save_data_to_file(self):
        with open(f"IMU_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w') as f:
            for i in range(len(imu_data["timestamps"])):
                f.write(f"{imu_data['timestamps'][i]},{imu_data['ax'][i]},{imu_data['ay'][i]},{imu_data['az'][i]},{imu_data['gx'][i]},{imu_data['gy'][i]},{imu_data['gz'][i]}\n")
        print_to_terminal("IMU data saved to file.", Fore.GREEN)

        # 如果有連接的設備，將 MAC 地址記錄到文件中並更新列表
        if connected_device:
            address = connected_device.address
            log_mac_address(address)
            self.update_mac_list()

    def clear_plot(self):
        imu_data["timestamps"].clear()
        imu_data["ax"].clear()
        imu_data["ay"].clear()
        imu_data["az"].clear()
        imu_data["gx"].clear()
        imu_data["gy"].clear()
        imu_data["gz"].clear()
        self.ax1.clear()
        self.ax2.clear()
        self.canvas.draw()
        print_to_terminal("Plot cleared.", Fore.CYAN)

    def disconnect_device(self):
        global connected_device
        if connected_device:
            try:
                self.loop.run_until_complete(connected_device.disconnect())
                connected_device = None
                print_to_terminal("Disconnected from device.", Fore.CYAN)
            except Exception as e:
                print_to_terminal(f"Failed to disconnect from the device: {e}", Fore.RED)

    def quit_app(self):
        global stop_monitoring
        stop_monitoring = True
        if self.ble_thread:
            self.ble_thread.join()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = BLEMonitorApp(root)
    root.mainloop()
