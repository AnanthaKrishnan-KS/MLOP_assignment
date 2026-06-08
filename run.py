import argparse
import json
import logging
import time
import sys

import numpy as np
import pandas as pd
import yaml


def setup_logging(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config(config_path: str) -> dict:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    required_keys = ["seed", "window", "version"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: '{key}'")

    if not isinstance(config["seed"], int):
        raise ValueError("Config 'seed' must be an integer")
    if not isinstance(config["window"], int) or config["window"] < 1:
        raise ValueError("Config 'window' must be a positive integer")
    if not isinstance(config["version"], str):
        raise ValueError("Config 'version' must be a string")

    return config


def load_dataset(input_path: str) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    if len(df.columns) == 1 and "," in df.columns[0]:
        df = pd.read_csv(input_path, sep=",", engine="python", quoting=3)

    if df.empty:
        raise ValueError("Input CSV is empty")

    df.columns = [c.strip() for c in df.columns]

    if "close" not in df.columns:
        raise ValueError("Required column 'close' not found in dataset")

    if df["close"].isnull().all():
        raise ValueError("Column 'close' contains no valid data")

    return df


def write_metrics(output_path: str, payload: dict):
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="MLOps batch signal job")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--config", required=True, help="Path to config YAML")
    parser.add_argument("--output", required=True, help="Path to output metrics JSON")
    parser.add_argument("--log-file", required=True, help="Path to log file")
    args = parser.parse_args()

    setup_logging(args.log_file)
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info("Job started")

    version = "unknown"

    try:
        config = load_config(args.config)
        version = config["version"]
        seed = config["seed"]
        window = config["window"]
        logger.info(f"Config loaded — version={version}, seed={seed}, window={window}")

        np.random.seed(seed)

        df = load_dataset(args.input)
        logger.info(f"Dataset loaded — {len(df)} rows, columns: {list(df.columns)}")


        df["rolling_mean"] = df["close"].rolling(window=window).mean()
        logger.info(f"Rolling mean computed with window={window}")

        valid = df["rolling_mean"].notna()
        df.loc[valid, "signal"] = (df.loc[valid, "close"] > df.loc[valid, "rolling_mean"]).astype(int)
        logger.info("Signal generated: 1 where close > rolling_mean, else 0")

        signal_series = df.loc[valid, "signal"]
        rows_processed = int(valid.sum())
        signal_rate = round(float(signal_series.mean()), 4)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Metrics — rows_processed={rows_processed}, signal_rate={signal_rate}, latency_ms={latency_ms}")

        metrics = {
            "version": version,
            "rows_processed": rows_processed,
            "metric": "signal_rate",
            "value": signal_rate,
            "latency_ms": latency_ms,
            "seed": seed,
            "status": "success",
        }

        write_metrics(args.output, metrics)
        logger.info(f"Metrics written to {args.output}")
        logger.info("Job completed successfully")

        print(json.dumps(metrics, indent=2))
        sys.exit(0)

    except FileNotFoundError as e:
        msg = f"File not found: {e}"
        logger.error(msg)
        error_payload = {"version": version, "status": "error", "error_message": msg}
        write_metrics(args.output, error_payload)
        print(json.dumps(error_payload, indent=2))
        sys.exit(1)

    except (ValueError, KeyError, pd.errors.ParserError) as e:
        msg = str(e)
        logger.error(f"Validation/processing error: {msg}")
        error_payload = {"version": version, "status": "error", "error_message": msg}
        write_metrics(args.output, error_payload)
        print(json.dumps(error_payload, indent=2))
        sys.exit(1)

    except Exception as e:
        msg = f"Unexpected error: {e}"
        logger.exception(msg)
        error_payload = {"version": version, "status": "error", "error_message": msg}
        write_metrics(args.output, error_payload)
        print(json.dumps(error_payload, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()