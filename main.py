import dearpygui.dearpygui as dpg
import time
import json
import wmi
import pythoncom

COLOR_BLUE = [0, 150, 255]
COLOR_LIGHT_BLUE = [0, 200, 255]
COLOR_YELLOW = [200, 200, 0]
COLOR_RED = [200, 10, 10]
COLOR_GREEN = [10, 255, 10]
COLOR_ORANGE = [255, 140, 0]

sensors_map = {}

def read_config():
    with open("config.json", "r", encoding="UTF8") as file:
        return json.load(file)


def get_theme(color_arr):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvThemeCat_Core):
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (color_arr[0], color_arr[1], color_arr[2]), category=dpg.mvThemeCat_Core)
    return theme


def update_sensors(cfg):

    pythoncom.CoInitialize()
    _wmi = wmi.WMI(namespace=cfg['WMI_NAMESPACE'])

    wmi_sensors = _wmi.Sensor()

    if len(wmi_sensors) == 0:
        print("unable to connect to the wmi service")
        print(cfg)
        time.sleep(2)
        return

    sensors = {}
    for sensor in wmi_sensors:
        # print(sensor.SensorType, '\t\t', sensor.Name, '\t\t', sensor.Value)
        if not sensor.SensorType in sensors:
            sensors[sensor.SensorType] = {}
        sensors[sensor.SensorType][sensor.Name] = sensor.Value

    sensors_map["GPU_TEMP"] = sensors["Temperature"]["GPU Core"]
    sensors_map["CPU_TEMP"] = sensors["Temperature"]["Core (Tctl/Tdie)"]

    sensors_map["GPU_TDP"] = sensors["Power"]["GPU Package"]
    sensors_map["CPU_TDP"] = sensors["Power"]["Package"]

    sensors_map["GPU_VRAM"] = sensors["SmallData"]["GPU Memory Used"]
    sensors_map["GPU_VRAM_LIMIT"] = sensors["SmallData"]["GPU Memory Total"]
    sensors_map["RAM_USAGE"] = sensors["Data"]["Memory Used"] * 1024
    sensors_map["RAM_FREE"] = sensors["Data"]["Memory Available"] * 1024
    sensors_map["PAGE_USAGE"] = sensors["Data"]["Virtual Memory Used"] * 1024
    sensors_map["PAGE_FREE"] = sensors["Data"]["Virtual Memory Available"] * 1024

    sensors_map["GPU_USAGE"] = sensors["Load"]["GPU Core"]
    sensors_map["CPU_USAGE"] = sensors["Load"]["CPU Total"]

    sensors_map["GPU_CLOCK_CORE"] = sensors["Clock"]["GPU Core"]
    sensors_map["GPU_CLOCK_VRAM"] = sensors["Clock"]["GPU Memory"]

    for _n in range(0, cfg['CPU_THREADS']):
        n = str(_n + 1)
        sensors_map["CPU_USAGE_THREAD_{n}".format(n=n)] = sensors["Load"]["CPU Core #{n}".format(n=n)]
        if _n < cfg['CPU_CORES']:
            sensors_map["CPU_CLOCK_CORE_{n}".format(n=n)] = sensors["Clock"]["Core #{n}".format(n=n)]

    print(sensors_map)


def dpg_add_bar(text, tag, color):
    with dpg.group(horizontal=True):
        dpg.add_text(text)
        bar = dpg.add_progress_bar(default_value=0.0, tag=tag, width=-1, overlay="?")
        dpg.bind_item_theme(bar, get_theme(color))


def init_gpu():
    with dpg.collapsing_header(label="GPU monitoring", default_open=True):
        dpg.add_text("GPU", color=COLOR_GREEN)
        dpg.add_text("GPU clock:", tag="GPU_CLOCK", color=COLOR_BLUE)

        dpg_add_bar("USAGE", "GPU_USAGE", COLOR_LIGHT_BLUE)
        dpg_add_bar("TDP  ", "GPU_TDP", COLOR_ORANGE)
        dpg_add_bar("TEMP ", "GPU_TEMP", COLOR_GREEN)
        dpg_add_bar("VRAM ", "GPU_VRAM", COLOR_YELLOW)


def init_cpu(cfg):
    with dpg.collapsing_header(label="CPU monitoring", default_open=True):
        dpg.add_text("CPU", color=COLOR_RED)
        dpg.add_text("CPU clock:",  tag="CPU_CLOCK", color=COLOR_BLUE)

        dpg_add_bar("USAGE", "CPU_USAGE", COLOR_LIGHT_BLUE)
        dpg_add_bar("TDP  ", "CPU_TDP", COLOR_ORANGE)
        dpg_add_bar("TEMP ", "CPU_TEMP", COLOR_RED)
        dpg_add_bar("RAM  ", "RAM_USAGE", COLOR_YELLOW)
        dpg_add_bar("PAGE ", "PAGE_USAGE", COLOR_YELLOW)

        dpg.add_text("CPU cores usage", color=COLOR_BLUE)
        for _n in range(0, cfg['CPU_THREADS']):
            n = str(_n + 1)
            with dpg.group(horizontal=True):
                # dpg.add_text("CORE " + n)
                dpg.add_progress_bar(default_value=0.0, tag="CPU_USAGE_THREAD_{n}".format(n=n), height=14, width=-1, overlay="?")


def daemon():
    while True:
        update(read_config())
        time.sleep(2)


def update_value(tag, limit, postfix):
    try:
        dpg.set_value(tag, sensors_map[tag] / limit)
        dpg.configure_item(tag, overlay=str(int(sensors_map[tag])) + postfix)
    except (KeyError, ZeroDivisionError):
        print("Error", tag, limit, postfix)
        return


def update(cfg):
    update_sensors(cfg)

    cores_clock_summ = 0.0
    for n in range(0, cfg['CPU_THREADS']):
        update_value("CPU_USAGE_THREAD_{n}".format(n=str(n + 1)), 100, "%")
        if n < cfg['CPU_CORES']:
            cores_clock_summ += sensors_map.get("CPU_CLOCK_CORE_{n}".format(n=str(n + 1)), 0)
    cores_clock = str(int(cores_clock_summ / cfg['CPU_CORES'])) if cores_clock_summ > 0 else "?"

    gpu_clock_core = int(sensors_map["GPU_CLOCK_CORE"]) if "GPU_CLOCK_CORE" in sensors_map else "?"
    gpu_clock_vram = int(sensors_map["GPU_CLOCK_VRAM"]) if "GPU_CLOCK_VRAM" in sensors_map else "?"
    dpg.set_value("GPU_CLOCK", f"GPU clock: {gpu_clock_core} / {gpu_clock_vram}")
    dpg.set_value("CPU_CLOCK", "CPU clock: " + cores_clock)

    update_value("GPU_USAGE", 100, "%")
    update_value("GPU_TDP", cfg["GPU_TDP_LIMIT"], " W")
    update_value("GPU_TEMP", 100, "°C")
    update_value("GPU_VRAM", sensors_map.get("GPU_VRAM_LIMIT", "?"), " MB")

    update_value("CPU_USAGE", 100, "%")
    update_value("CPU_TDP", cfg["CPU_TDP_LIMIT"], " W")
    update_value("CPU_TEMP", 100, "°C")
    update_value("RAM_USAGE", sensors_map.get("RAM_USAGE", 0) + sensors_map.get("RAM_FREE", 0), " MB")
    update_value("PAGE_USAGE", sensors_map.get("PAGE_USAGE", 0) + sensors_map.get("PAGE_FREE", 0), " MB")


if __name__ == "__main__":
    cfg = read_config()

    # sensors_map = {
    #     "GPU_CLOCK_CORE": 0.0,
    #     "GPU_CLOCK_VRAM": 0.0,
    #     "GPU_USAGE": 0.0,
    #     "GPU_TDP": 0.0,
    #     "GPU_TEMP": 0.0,
    #     "GPU_VRAM": 0.0,
    #     "GPU_VRAM_LIMIT": 0.0,
    #
    #     "CPU_CLOCK": 0.0,
    #     "CPU_USAGE": 0.0,
    #     "CPU_TDP": 0.0,
    #     "CPU_TEMP": 0.0,
    #     "RAM_USAGE": 0.0,
    #     "RAM_FREE": 0.0,
    #     "PAGE_USAGE": 0.0,
    #     "PAGE_FREE": 0.0
    # }
    # for n in range(0, cfg['CPU_CORES']):
    #     sensors_map["CPU{n} usage".format(n=str(n + 1))] = 0.0

    dpg.create_context()
    dpg.create_viewport(title="Monitoring", width=cfg["WINDOW_WIDTH"], height=cfg["WINDOW_HEIGHT"])
    dpg.setup_dearpygui()

    with dpg.window(tag="main"):
        init_gpu()
        init_cpu(cfg)

    dpg.set_primary_window("main", True)
    dpg.set_frame_callback(1, callback=daemon)

    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
