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
    exist_cron = None
    for job in cron:
        # Check if the job matches your criteria, for example, if you want to update a specific command
        if job.command == command:
            # Modify the job as needed
            job.setall(
                cron_expression
            )  # Example: change the schedule to every 5 minutes

            # Write changes to crontab
            cron.write()
            print("Cron job updated successfully.")
            break  # Stop iteration if the job is found and updated
    else:

        job = cron.new(command=command)
        job.setall(cron_expression)
        cron.write()


def generate_unique_id():
    return str(uuid.uuid4()).split("-")[0]


def generate_result(raw_result: str):
    from utils.configuration import YamlConfigLoader

    print(raw_result)
    configuration = YamlConfigLoader()

    integer_digit = configuration.get_param("vision", "integer", "digit")
    integer_uom = configuration.get_param(
        "vision", "integer", "unit_of_measurement"
    ).lower()
    decimal_digit = configuration.get_param("vision", "decimal", "digit")
    decimal_uom = configuration.get_param(
        "vision", "decimal", "unit_of_measurement"
    ).lower()

    vision_integer = configuration.get_param("vision", "coordinates", "integer")
    vision_digit = configuration.get_param("vision", "coordinates", "digit")
    vision_all = configuration.get_param("vision", "coordinates", "digit")

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

        if "." in raw_result_without_space:  # review the logix to get both numbers
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
        left_number = int(
            raw_result_without_space
        )  # review the logic to get the left number

    if vision_digit:
        right_number = 0  # implement the logic to get the right number

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
