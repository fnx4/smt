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
        exit(-1)

    sensors = {}
    for sensor in wmi_sensors:
        # print(sensor.SensorType, '\t\t', sensor.Name, '\t\t', sensor.Value)
        if not sensor.SensorType in sensors:
            sensors[sensor.SensorType] = {}
        sensors[sensor.SensorType][sensor.Name] = sensor.Value

    sensors_map["GPU_TEMP"] = sensors["Temperature"]["GPU Core"]
    sensors_map["CPU_TEMP"] = sensors["Temperature"]["CPU Package"]

    sensors_map["GPU_TDP"] = sensors["Power"]["GPU Power"]
    sensors_map["CPU_TDP"] = sensors["Power"]["CPU Package"]

    sensors_map["GPU_VRAM"] = sensors["SmallData"]["GPU Memory Used"]
    sensors_map["RAM_USAGE"] = sensors["Data"]["Used Memory"] * 1024

    sensors_map["GPU_USAGE"] = sensors["Load"]["GPU Core"]
    sensors_map["CPU_USAGE"] = sensors["Load"]["CPU Total"]

    sensors_map["GPU_CLOCK_CORE"] = sensors["Clock"]["GPU Core"]
    sensors_map["GPU_CLOCK_VRAM"] = sensors["Clock"]["GPU Memory"]

    for _n in range(0, cfg['CPU_CORES']):
        n = str(_n + 1)
        sensors_map["CPU_USAGE_CORE_{n}".format(n=n)] = sensors["Load"]["CPU Core #{n}".format(n=n)]
        sensors_map["CPU_CLOCK_CORE_{n}".format(n=n)] = sensors["Clock"]["CPU Core #{n}".format(n=n)]

    print(sensors_map)


def init_gpu():
    with dpg.collapsing_header(label="GPU monitoring", default_open=True):
        dpg.add_text("GPU", color=COLOR_GREEN)
        dpg.add_text("GPU clock:", tag="GPU_CLOCK", color=COLOR_BLUE)

        with dpg.group(horizontal=True):
            dpg.add_text("USAGE")
            bar = dpg.add_progress_bar(default_value=0.0, tag="GPU_USAGE", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_LIGHT_BLUE))

        with dpg.group(horizontal=True):
            dpg.add_text("TDP  ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="GPU_TDP", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_ORANGE))

        with dpg.group(horizontal=True):
            dpg.add_text("TEMP ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="GPU_TEMP", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_GREEN))

        with dpg.group(horizontal=True):
            dpg.add_text("VRAM ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="GPU_VRAM", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_YELLOW))


def init_cpu(cfg):
    with dpg.collapsing_header(label="CPU monitoring", default_open=True):
        dpg.add_text("CPU", color=COLOR_RED)
        dpg.add_text("CPU clock:",  tag="CPU_CLOCK", color=COLOR_BLUE)

        with dpg.group(horizontal=True):
            dpg.add_text("USAGE")
            bar = dpg.add_progress_bar(default_value=0.0, tag="CPU_USAGE", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_LIGHT_BLUE))

        with dpg.group(horizontal=True):
            dpg.add_text("TDP  ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="CPU_TDP", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_ORANGE))

        with dpg.group(horizontal=True):
            dpg.add_text("TEMP ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="CPU_TEMP", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_RED))

        with dpg.group(horizontal=True):
            dpg.add_text("RAM  ")
            bar = dpg.add_progress_bar(default_value=0.0, tag="RAM_USAGE", width=-1, overlay="?")
            dpg.bind_item_theme(bar, get_theme(COLOR_YELLOW))

        # with dpg.group(horizontal=True):
        #     dpg.add_text("PAGE ")
        #     bar = dpg.add_progress_bar(default_value=0.0, tag="RAM_PAGE", width=-1, overlay="?")
        #     dpg.bind_item_theme(bar, get_theme(COLOR_YELLOW))

        dpg.add_text("CPU cores usage", color=COLOR_BLUE)
        for _n in range(0, cfg['CPU_CORES']):
            # n = str(_n).zfill(2)
            n = str(_n + 1)
            with dpg.group(horizontal=True):
                # dpg.add_text("CORE " + n)
                dpg.add_progress_bar(default_value=0.0, tag="CPU_USAGE_CORE_{n}".format(n=n), height=14, width=-1, overlay="?")


def daemon():
    while True:
        update(read_config())
        time.sleep(2)


def update_value(tag, limit, postfix):
    dpg.set_value(tag, sensors_map[tag] / limit)
    dpg.configure_item(tag, overlay=str(int(sensors_map[tag])) + postfix)


def update(cfg):
    update_sensors(cfg)

    cores_clock_summ = 0.0
    for n in range(0, cfg['CPU_CORES']):
        update_value("CPU_USAGE_CORE_{n}".format(n=str(n + 1)), 100, "%")
        cores_clock_summ += sensors_map["CPU_CLOCK_CORE_{n}".format(n=str(n + 1))]

    dpg.set_value("GPU_CLOCK", f"GPU clock: {int(sensors_map['GPU_CLOCK_CORE'])} / {int(sensors_map['GPU_CLOCK_VRAM'])}")
    dpg.set_value("CPU_CLOCK", "CPU clock: " + str(int(cores_clock_summ / cfg['CPU_CORES'])))

    update_value("GPU_USAGE", 100, "%")
    update_value("GPU_TDP", cfg["GPU_TDP_LIMIT"], " W")
    update_value("GPU_TEMP", 100, "°C")
    update_value("GPU_VRAM", cfg["GPU_VRAM_LIMIT_GB"] * 1024, " MB")

    update_value("CPU_USAGE", 100, "%")
    update_value("CPU_TDP", cfg["CPU_TDP_LIMIT"], " W")
    update_value("CPU_TEMP", 100, "°C")
    update_value("RAM_USAGE", cfg["RAM_USAGE_LIMIT_GB"] * 1024, " MB")
    # update_value("RAM_PAGE", math.pow(2, 17), " MB")


if __name__ == "__main__":
    cfg = read_config()

    sensors_map = {
        "GPU_CLOCK_CORE": 0.0,
        "GPU_CLOCK_VRAM": 0.0,
        "GPU_USAGE": 0.0,
        "GPU_TDP": 0.0,
        "GPU_TEMP": 0.0,
        "GPU_VRAM": 0.0,

        "CPU_CLOCK": 0.0,
        "CPU_USAGE": 0.0,
        "CPU_TDP": 0.0,
        "CPU_TEMP": 0.0,
        "RAM_USAGE": 0.0,
        # "RAM_PAGE": 0.0,
    }
    for n in range(0, cfg['CPU_CORES']):
        sensors_map["CPU{n} usage".format(n=str(n + 1))] = 0.0

    dpg.create_context()
    dpg.create_viewport(title="Monitoring", width=400, height=950)
    dpg.setup_dearpygui()

    with dpg.window(tag="main"):
        init_gpu()
        init_cpu(cfg)

    dpg.set_primary_window("main", True)
    dpg.set_frame_callback(1, callback=daemon)

    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
