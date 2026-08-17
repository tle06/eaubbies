from crontab import CronTab
import logging
import uuid

logger = logging.getLogger(__name__)


def volume_converter(number, from_unit: str, to_unit: str):
    """
    Convert *number* between water volume units.

    Parameters:
        number (float): Quantity to convert.
        from_unit (str): Source unit, one of ``l, cl, dl, hl, m3``.
        to_unit (str): Target unit, one of ``l, cl, dl, hl, m3``.

    Returns:
        float: The converted quantity.

    Raises:
        ValueError: If either unit is not supported.
    """
    units = {"l": 1, "cl": 0.01, "dl": 0.1, "hl": 100, "m3": 1000}
    logger.debug(f"volume_converter: {number} {from_unit} -> {to_unit}")

    if from_unit not in units or to_unit not in units:
        raise ValueError("Invalid unit provided (l,cl,dl,hl,m3)")

    if from_unit == to_unit:
        return number

    base_number = number * units[from_unit]
    result = base_number / units[to_unit]

    return result


def time_to_cron(selected_time):
    """
    Convert a ``HH:MM`` time into a daily cron expression.

    A zero hour or minute is mapped to ``*`` (every hour / every minute) to
    preserve the existing scheduling behaviour.

    Parameters:
        selected_time (str): Time in ``HH:MM`` 24-hour format.

    Returns:
        str: A 5-field cron expression.
    """
    hours, minutes = map(int, selected_time.split(":"))
    if hours == 0:
        hours = "*"
    if minutes == 0:
        minutes = "*"
    return f"{minutes} {hours} * * *"


def register_cron_task(command, selected_time):
    """
    Create or update the user crontab entry for *command*.

    Parameters:
        command (str): The exact command line the cron job runs.
        selected_time (str): Schedule time in ``HH:MM`` format.
    """
    cron = CronTab(user=True)
    cron_expression = time_to_cron(selected_time)

    for job in cron:
        if job.command == command:
            job.setall(cron_expression)
            cron.write()
            logger.info("Cron job updated successfully.")
            return

    job = cron.new(command=command)
    job.setall(cron_expression)
    cron.write()
    logger.info("Cron job registered successfully.")


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
    """Return a short (8-char) unique identifier derived from a UUID4."""
    return str(uuid.uuid4()).split("-")[0]


def generate_result(raw_result: str):
    """
    Turn a raw OCR string into a structured meter reading.

    Splits the recognised digits into the integer and decimal portions (based
    either on an explicit dot, the configured integer digit count, or the
    active coordinate region), converts both to the main unit of measurement,
    and returns a rich payload used for MQTT publishing.

    When there is no dot, the first ``integer_digit`` characters form the
    integer part and the remaining trailing characters form the decimal part.

    Parameters:
        raw_result (str): The raw text produced by the OCR engine.

    Returns:
        dict: Parsed values including ``left_number``, ``right_number`` and
        ``total_liters``.

    Raises:
        ValueError: If a detected dotted value cannot be parsed to integers.
    """
    from utils.configuration import YamlConfigLoader

    logger.debug(f"generate_result raw input: '{raw_result}'")
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
    logger.debug(
        f"config: integer_digit={integer_digit} integer_uom={integer_uom} "
        f"decimal_digit={decimal_digit} decimal_uom={decimal_uom} main_uom={main_uom}"
    )
    raw_result_without_space = raw_result.replace(" ", "")
    logger.debug(f"raw_result_without_space: '{raw_result_without_space}'")
    right_number = 0
    left_number = 0

    if vision_all:
        if "." in raw_result_without_space:
            logger.debug("dot detected in OCR result")
            parts = raw_result.split(".")
            logger.debug(f"dotted parts: {parts}")
            try:
                left_number = int(parts[0])
                right_number = int(parts[1])
            except Exception as e:
                logger.warning(f"Failed to parse dotted parts {parts}: {e}")
                raise ValueError(f"Can't convert parts: {parts} to integers")
        else:
            try:
                logger.debug("no dot detected in OCR result")
                left_number = int(raw_result_without_space[:integer_digit])
                # The decimal portion is the trailing digits *after* the
                # integer portion. Its digit count is len - integer_digit;
                # slice from integer_digit (not from that count) so the
                # integer and decimal parts do not overlap.
                decimal_digit = len(raw_result_without_space) - integer_digit
                right_number = int(raw_result_without_space[integer_digit:] or 0)
            except Exception as e:
                logger.warning(
                    f"Digit-split failed for '{raw_result_without_space}': {e}"
                )
                left_number = int(raw_result_without_space)
                right_number = 0
    if vision_integer:
        left_number = int(raw_result_without_space)
    if vision_digit:
        right_number = 0

    logger.debug(f"parsed left_number={left_number} right_number={right_number}")
    left_number_to_liters = volume_converter(
        number=left_number, from_unit=integer_uom, to_unit=main_uom
    )
    logger.debug(f"left_number_to_liters={left_number_to_liters}")
    right_number_to_liters = volume_converter(
        number=right_number, from_unit=decimal_uom, to_unit=main_uom
    )
    logger.debug(f"right_number_to_liters={right_number_to_liters}")
    total_liters = left_number_to_liters + right_number_to_liters
    logger.debug(f"total_liters={total_liters}")
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
