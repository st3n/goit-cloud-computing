#!/usr/bin/env python3
"""Async load test (stdlib only) used to trigger ECS Auto Scaling.

Hits the CPU-bound endpoint /api/cpu (plus a few light endpoints) with N
concurrent workers for a given duration and prints latency / error stats.

Usage:
    python3 tests/load_test.py http://<alb-dns> --concurrency 60 --duration 300
"""
import argparse
import asyncio
import statistics
import time
import urllib.error
import urllib.request


def fetch(url: str, timeout: float) -> tuple[int, float]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            resp.read()
            code = resp.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    except Exception:
        code = 0  # connection error / timeout
    return code, time.perf_counter() - start


async def worker(urls, stop_at, timeout, results, idx):
    i = idx
    while time.monotonic() < stop_at:
        url = urls[i % len(urls)]
        i += 1
        results.append(await asyncio.to_thread(fetch, url, timeout))


async def reporter(stop_at, results):
    last = 0
    while time.monotonic() < stop_at:
        await asyncio.sleep(10)
        recent = results[last:]
        last = len(results)
        errs = sum(1 for c, _ in recent if c == 0 or c >= 500)
        print(f"[{time.strftime('%H:%M:%S')}] +{len(recent)} req/10s, errors={errs}", flush=True)


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("base_url")
    p.add_argument("--concurrency", type=int, default=60)
    p.add_argument("--duration", type=int, default=300, help="seconds")
    p.add_argument("--cpu-ms", type=int, default=200, help="CPU time burned per /api/cpu call")
    p.add_argument("--timeout", type=float, default=15)
    a = p.parse_args()

    base = a.base_url.rstrip("/")
    urls = [f"{base}/api/cpu?ms={a.cpu_ms}"] * 4 + [f"{base}/health", f"{base}/api/tasks"]
    results: list[tuple[int, float]] = []
    stop_at = time.monotonic() + a.duration

    print(f"Load test: {a.concurrency} workers for {a.duration}s against {base}")
    t0 = time.monotonic()
    await asyncio.gather(
        reporter(stop_at, results),
        *(worker(urls, stop_at, a.timeout, results, i) for i in range(a.concurrency)),
    )
    elapsed = time.monotonic() - t0

    lat = sorted(t for _, t in results)
    ok = sum(1 for c, _ in results if 200 <= c < 400)
    total = len(results)
    if not total:
        print("No requests completed")
        return
    pct = lambda q: lat[min(int(len(lat) * q), len(lat) - 1)]
    print("\n===== RESULTS =====")
    print(f"Total requests : {total}")
    print(f"Success        : {ok} ({ok / total:.1%})")
    print(f"Throughput     : {total / elapsed:.1f} req/s")
    print(f"Latency avg    : {statistics.mean(lat) * 1000:.0f} ms")
    print(f"Latency p50/p95/p99: {pct(.5) * 1000:.0f} / {pct(.95) * 1000:.0f} / {pct(.99) * 1000:.0f} ms")
    codes: dict[int, int] = {}
    for c, _ in results:
        codes[c] = codes.get(c, 0) + 1
    print(f"Status codes   : {dict(sorted(codes.items()))}  (0 = connection error/timeout)")


if __name__ == "__main__":
    asyncio.run(main())
