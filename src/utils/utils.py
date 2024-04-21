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
    # Split the selected time into hours and minutes
    hours, minutes = map(int, selected_time.split(":"))

    # Create the cron expression
    cron_expression = f"{minutes} {hours} * * *"

    return cron_expression
