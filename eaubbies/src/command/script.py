#!/usr/bin/env python
# eaubbies/eaubbies/src/script.py
"""
Troubleshooting and CLI test script for Eaubbies service process.
Executes image capture/load, processing, cropping, image enhancements, and OCR,
saving intermediate output frames to a dedicated troubleshooting folder.
"""

import os
import argparse
import logging
from service import service_process
from utils.configuration import YamlConfigLoader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("troubleshoot")


def main():
    parser = argparse.ArgumentParser(
        description="Troubleshoot Eaubbies Image Improvements and OCR."
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to an image file to process (defaults to RTSP feed if not specified)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="data/troubleshoot",
        help="Folder where troubleshooting images will be saved",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["azure", "tesseract","paddle"],
        default="azure",
        help="Override OCR Engine selection",
    )
    parser.add_argument("--rotate", type=float, help="Override image rotation angle")
    parser.add_argument(
        "--tesseract-config", type=str, help="Override Tesseract config string"
    )

    args = parser.parse_args()
    config_loader = YamlConfigLoader()

    # 1. Apply overrides to runtime config
    if args.engine:
        logger.info(f"Overriding OCR Engine to: {args.engine}")
        config_loader.set_param("vision", "engine", value=args.engine)
    if args.rotate is not None:
        logger.info(f"Overriding rotate angle to: {args.rotate}")
        config_loader.set_param("vision", "rotate", value=args.rotate)
    if args.tesseract_config:
        logger.info(f"Overriding Tesseract config to: {args.tesseract_config}")
        config_loader.set_param(
            "vision", "tesseract_config", value=args.tesseract_config
        )

    # Backup current frame storage path to redirect outputs
    original_storage = config_loader.get_param("frame", "storage_path")
    os.makedirs(args.out_dir, exist_ok=True)
    config_loader.set_param("frame", "storage_path", value=args.out_dir)

    try:
        logger.info("Starting Service Process Execution...")

        # Determine if we are loading from a file or streaming
        use_file = False
        file_obj = None
        if args.file:
            if not os.path.exists(args.file):
                raise FileNotFoundError(f"Input file not found: {args.file}")
            logger.info(f"Loading input file from path: {args.file}")
            use_file = True

            # Mimic Flask file wrapper object
            class MockFile:
                def __init__(self, path):
                    self.filename = os.path.basename(path)
                    self._path = path

                def read(self):
                    with open(self._path, "rb") as f:
                        return f.read()

            file_obj = MockFile(args.file)

        # Run process
        result = service_process(
            increase_cron_count=False, use_file=use_file, file=file_obj
        )

        if isinstance(result, ValueError) or (
            isinstance(result, dict) and "error" in result
        ):
            logger.error(f"Process ended with error: {result}")
        else:
            logger.info("Process completed successfully!")
            import json

            logger.info(
                f"OCR Outputs:\n{json.dumps(result.get('result', {}), indent=2)}"
            )
            logger.info(f"Troubleshooting images saved in folder: {args.out_dir}/")
            logger.info("Generated frames:")
            for f in os.listdir(args.out_dir):
                if f.endswith(".jpg"):
                    logger.info(f" - {args.out_dir}/{f}")

    finally:
        # Revert runtime configuration storage path back to original
        config_loader.set_param("frame", "storage_path", value=original_storage)


if __name__ == "__main__":
    main()
