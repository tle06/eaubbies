from crontab import CronTab
import uuid


def volume_converter(number, from_unit: str, to_unit: str):
    units = {"l": 1, "cl": 0.01, "dl": 0.1, "hl": 100, "m3": 1000}
    print(number, from_unit, to_unit)

    if from_unit not in units or to_unit not in units:
        raise ValueError("Invalid unit provided (l,cl,dl,hl,m3)")

    if from_unit == to_unit:
        return number

    base_number = number * units[from_unit]
    result = base_number / units[to_unit]

    return result


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

    for job in cron:
        if job.command == command:
            job.setall(cron_expression)
            cron.write()
            print("Cron job updated successfully.")
            return

    job = cron.new(command=command)
    job.setall(cron_expression)
    cron.write()
    print("Cron job registered successfully.")


def get_cron_status(command: str) -> dict:
    """
    Inspect the current user crontab for *command*.

    Returns a dict:
        {
            "found":    bool,   # job exists in crontab
            "enabled":  bool,   # job is not commented-out
            "schedule": str,    # cron expression string, or empty
            "render":   str,    # human-readable schedule, or empty
        }
    """
    try:
        cron = CronTab(user=True)
        for job in cron:
            if job.command == command:
                enabled = job.is_enabled()
                schedule = str(job.slices)  # e.g. "0 1 * * *"
                try:
                    render = str(job.description(use_24hour_time=True))
                except Exception:
                    render = schedule
                return {
                    "found": True,
                    "enabled": enabled,
                    "schedule": schedule,
                    "render": render,
                }
        return {"found": False, "enabled": False, "schedule": "", "render": ""}
    except Exception as e:
        return {
            "found": False,
            "enabled": False,
            "schedule": "",
            "render": "",
            "error": str(e),
        }


def generate_unique_id():
    return str(uuid.uuid4()).split("-")[0]


def generate_result(raw_result: str):
    from utils.configuration import YamlConfigLoader

    print(raw_result)
    configuration = YamlConfigLoader()

    integer_digit = int(configuration.get_param("vision", "integer", "digit"))
    integer_uom = configuration.get_param(
        "vision", "integer", "unit_of_measurement"
    ).lower()
    decimal_digit = int(configuration.get_param("vision", "decimal", "digit"))
    decimal_uom = configuration.get_param(
        "vision", "decimal", "unit_of_measurement"
    ).lower()

    try:
        vision_integer = configuration.get_param(
            "vision", "coordinates", "integer"
        ).get("active", False)
        vision_digit = configuration.get_param("vision", "coordinates", "digit").get(
            "active", False
        )
        vision_all = configuration.get_param("vision", "coordinates", "all").get(
            "active", False
        )
    except Exception:
        try:
            coords_dict = configuration.get_param("vision", "coordinates")
            vision_integer = bool(
                coords_dict.get("integer") and coords_dict["integer"].get("active")
            )
            vision_digit = bool(
                coords_dict.get("digit") and coords_dict["digit"].get("active")
            )
            vision_all = bool(
                coords_dict.get("all") and coords_dict["all"].get("active")
            )
        except Exception:
            vision_integer = False
            vision_digit = False
            vision_all = True

    main_uom = configuration.get_param(
        "mqtt", "sensors", "water", "unit_of_measurement"
    ).lower()

    rotate = configuration.get_param("vision", "rotate")
    print(integer_digit, integer_uom, decimal_digit, decimal_uom, main_uom)
    raw_result_without_space = raw_result.replace(" ", "")
    print(raw_result_without_space)
    right_number = 0
    left_number = 0

    if vision_all:
        if "." in raw_result_without_space:
            print("dot detected")
            parts = raw_result.split(".")
            print(parts)
            try:
                left_number = int(parts[0])
                right_number = int(parts[1])
            except Exception as e:
                print(e)
                raise ValueError(f"Can't convert parts: {parts} to integers")
        else:
            try:
                print("no dot detected")
                left_number = int(raw_result_without_space[:integer_digit])
                print(len(raw_result_without_space))
                decimal_digit = len(raw_result_without_space) - integer_digit
                right_number = int(raw_result_without_space[decimal_digit:])
            except Exception as e:
                print(e)
                left_number = int(raw_result_without_space)
                right_number = 0
    if vision_integer:
        left_number = int(raw_result_without_space)
    if vision_digit:
        right_number = 0

    print(left_number, right_number)
    left_number_to_liters = volume_converter(
        number=left_number, from_unit=integer_uom, to_unit=main_uom
    )
    print(left_number_to_liters)
    right_number_to_liters = volume_converter(
        number=right_number, from_unit=decimal_uom, to_unit=main_uom
    )
    print(right_number_to_liters)
    total_liters = left_number_to_liters + right_number_to_liters
    print(total_liters)
    data = {
        "raw_result": raw_result,
        "raw_result_without_space": raw_result_without_space,
        "left_number": left_number,
        "integer_digit": integer_digit,
        "integer_uom": integer_uom,
        "left_number_to_liters": left_number_to_liters,
        "right_number": right_number,
        "decimal_digit": decimal_digit,
        "decimal_uom": decimal_uom,
        "right_number_to_liters": right_number_to_liters,
        "main_uom": main_uom,
        "total_liters": total_liters,
        "rotate": rotate,
    }
    return data
