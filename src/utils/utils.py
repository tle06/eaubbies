from crontab import CronTab
import uuid


def volume_converter(number, from_unit: str, to_unit: str):
    units = {"l": 1, "cl": 0.01, "dl": 0.1, "hl": 100, "m3": 1000}

    if from_unit not in units or to_unit not in units:
        return "Invalid unit provided"

    if from_unit == to_unit:
        return number

    if from_unit == "l":
        return number * units[to_unit]
    elif to_unit == "l":
        return number / units[from_unit]
    else:
        liters = number / units[from_unit]
        return liters * units[to_unit]


def time_to_cron(selected_time):
    hours, minutes = map(int, selected_time.split(":"))
    if hours == 0:
        hours = "*"
    if minutes == 0:
        minutes = "*"
    return f"{minutes} {hours} * * *"


def register_cron_task(command, selected_time):
    cron = CronTab(user=True)
    cron_expression = time_to_cron(selected_time)
    job = cron.new(command=command)
    job.setall(cron_expression)
    cron.write()


def generate_unique_id():
    return str(uuid.uuid4()).split("-")[0]
