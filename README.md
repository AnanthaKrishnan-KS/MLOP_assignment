
## Local Run

### Prerequisites
- Python 3.9+
- pip

### Setup
```bash
pip install -r requirements.txt
```

### Run
```bash
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

## Docker Build & Run

```bash
docker build -t mlops-task .
docker run --rm mlops-task
```

To retrieve output files from the container:
```bash
docker run --rm -v ${PWD}/output:/app/output mlops-task python run.py --input data.csv --config config.yaml --output /app/output/metrics.json --log-file /app/output/run.log
```

## Example metrics.json

```json
{
  "version": "v1",
  "rows_processed": 9996,
  "metric": "signal_rate",
  "value": 0.499,
  "latency_ms": 134,
  "seed": 42,
  "status": "success"
}
```

## Notes

- First `window - 1` rows are excluded from signal computation (rolling mean is NaN there)
- `signal = 1` if `close > rolling_mean`, else `0`
- All paths are CLI args — no hardcoded paths anywhere
- Exit code `0` on success, non-zero on any failure
- `metrics.json` is always written, even on error
