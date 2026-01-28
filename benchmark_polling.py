"""
Benchmark script to test HTTP polling performance
Replicates the same pattern used in autobid.py
"""
import time
import httpx
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Test endpoints - using public endpoints that don't require auth
TEST_URLS = [
    "https://httpbin.org/get",  # For testing HTTP request latency
    "https://www.google.com/",
]

# Use the same httpx configuration as autobid.py
def create_optimized_client():
    """Create httpx client with same settings as autobid.py"""
    return httpx.Client(
        timeout=httpx.Timeout(5.0, connect=2.0, read=3.0),
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
            keepalive_expiry=30
        )
    )

def single_request(url: str, client: httpx.Client) -> float:
    """Single request latency test"""
    start = time.perf_counter()
    try:
        response = client.get(url)
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed if response.status_code == 200 else -1
    except Exception:
        return (time.perf_counter() - start) * 1000

def test_single_threaded_polling(num_requests: int = 100) -> dict:
    """Test single-threaded polling (baseline)"""
    print(f"\n[1] Single-threaded polling ({num_requests} requests)...")
    client = create_optimized_client()
    latencies = []

    start_total = time.perf_counter()
    for _ in range(num_requests):
        latency = single_request(TEST_URLS[0], client)
        if latency > 0:
            latencies.append(latency)
    total_time = (time.perf_counter() - start_total) * 1000

    client.close()

    return {
        "method": "single_threaded",
        "total_requests": num_requests,
        "total_time_ms": total_time,
        "requests_per_second": num_requests / (total_time / 1000),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
    }

def test_concurrent_polling(num_requests: int = 100, concurrency: int = 3) -> dict:
    """Test concurrent polling (like autobid.py uses)"""
    print(f"\n[2] Concurrent polling ({num_requests} requests, {concurrency} parallel)...")
    client = create_optimized_client()
    latencies = []

    start_total = time.perf_counter()

    def fetch():
        start = time.perf_counter()
        try:
            response = client.get(TEST_URLS[0])
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed if response.status_code == 200 else -1
        except:
            return (time.perf_counter() - start) * 1000

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fetch) for _ in range(num_requests)]
        for future in as_completed(futures):
            latency = future.result()
            if latency > 0:
                latencies.append(latency)

    total_time = (time.perf_counter() - start_total) * 1000
    client.close()

    return {
        "method": f"concurrent_{concurrency}",
        "total_requests": num_requests,
        "concurrency": concurrency,
        "total_time_ms": total_time,
        "requests_per_second": num_requests / (total_time / 1000),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
    }

def test_burst_polling(duration_seconds: int = 10, interval_ms: int = 50) -> dict:
    """Test burst polling at specific interval (like autobid.py poll_interval)"""
    print(f"\n[3] Burst polling for {duration_seconds}s at {interval_ms}ms interval...")
    client = create_optimized_client()
    latencies = []
    request_count = 0

    start_total = time.perf_counter()
    end_time = start_total + duration_seconds

    while time.perf_counter() < end_time:
        latency = single_request(TEST_URLS[0], client)
        if latency > 0:
            latencies.append(latency)
            request_count += 1
        time.sleep(interval_ms / 1000)

    total_time = (time.perf_counter() - start_total) * 1000
    client.close()

    return {
        "method": f"burst_{interval_ms}ms",
        "total_requests": request_count,
        "total_time_ms": total_time,
        "requests_per_second": request_count / (total_time / 1000),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
    }

def test_concurrent_burst(duration_seconds: int = 10, interval_ms: int = 50, concurrency: int = 3) -> dict:
    """Test concurrent burst polling (actual autobid.py pattern)"""
    print(f"\n[4] Concurrent burst polling ({concurrency} parallel, {interval_ms}ms interval)...")
    client = create_optimized_client()
    latencies = []
    request_count = 0

    start_total = time.perf_counter()
    end_time = start_total + duration_seconds

    def fetch():
        start = time.perf_counter()
        try:
            response = client.get(TEST_URLS[0])
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed if response.status_code == 200 else -1
        except:
            return (time.perf_counter() - start) * 1000

    while time.perf_counter() < end_time:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(fetch) for _ in range(concurrency)]

            for future in as_completed(futures):
                latency = future.result()
                if latency > 0:
                    latencies.append(latency)
                    request_count += 1

        time.sleep(interval_ms / 1000)

    total_time = (time.perf_counter() - start_total) * 1000
    client.close()

    return {
        "method": f"concurrent_burst_{concurrency}_{interval_ms}ms",
        "total_requests": request_count,
        "concurrency": concurrency,
        "total_time_ms": total_time,
        "requests_per_second": request_count / (total_time / 1000),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
    }

def test_high_concurrency(num_requests: int = 500, concurrency: int = 50) -> dict:
    """Test high concurrency scenario (where Python might struggle)"""
    print(f"\n[5] High concurrency test ({num_requests} requests, {concurrency} parallel)...")
    client = create_optimized_client()
    latencies = []

    start_total = time.perf_counter()

    def fetch():
        start = time.perf_counter()
        try:
            response = client.get(TEST_URLS[0])
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed if response.status_code == 200 else -1
        except:
            return (time.perf_counter() - start) * 1000

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(fetch) for _ in range(num_requests)]
        for future in as_completed(futures):
            latency = future.result()
            if latency > 0:
                latencies.append(latency)

    total_time = (time.perf_counter() - start_total) * 1000
    client.close()

    return {
        "method": f"high_concurrency_{concurrency}",
        "total_requests": num_requests,
        "concurrency": concurrency,
        "total_time_ms": total_time,
        "requests_per_second": num_requests / (total_time / 1000),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0] if latencies else 0,
        "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
    }

def print_results(results: list[dict]):
    """Print benchmark results in a table"""
    print("\n" + "="*100)
    print("BENCHMARK RESULTS")
    print("="*100)
    print(f"{'Method':<30} {'RPS':>10} {'Avg':>10} {'P50':>10} {'P95':>10} {'P99':>10} {'Jitter':>10}")
    print("-"*100)

    for r in results:
        print(f"{r['method']:<30} "
              f"{r['requests_per_second']:>10.1f} "
              f"{r['avg_latency_ms']:>10.1f} "
              f"{r['p50_latency_ms']:>10.1f} "
              f"{r['p95_latency_ms']:>10.1f} "
              f"{r['p99_latency_ms']:>10.1f} "
              f"{r['jitter_ms']:>10.1f}")

    print("="*100)

def main():
    print("="*100)
    print("HTTP POLLING BENCHMARK - Python (httpx)")
    print("="*100)
    print(f"Test URL: {TEST_URLS[0]}")
    print(f"Started at: {datetime.now()}")
    print(f"Python httpx.Client with connection pooling")
    print("="*100)

    results = []

    # Test 1: Single-threaded baseline
    results.append(test_single_threaded_polling(100))

    # Test 2: Concurrent polling (current autobid.py setting)
    results.append(test_concurrent_polling(100, 3))

    # Test 3: Burst polling at 50ms interval
    results.append(test_burst_polling(10, 50))

    # Test 4: Concurrent burst (actual autobid.py pattern)
    results.append(test_concurrent_burst(10, 50, 3))

    # Test 5: Higher concurrency
    results.append(test_concurrent_polling(100, 10))

    # Test 6: Even higher concurrency (stress test)
    results.append(test_high_concurrency(500, 50))

    print_results(results)

    # Analysis
    print("\nKEY FINDINGS:")
    print("-"*100)
    baseline = results[0]
    burst = results[3]
    high_conc = results[-1]

    print(f"1. Baseline (single-threaded): {baseline['requests_per_second']:.1f} RPS, {baseline['p95_latency_ms']:.1f}ms P95")
    print(f"2. Your current setup (3 concurrent, 50ms interval): {burst['requests_per_second']:.1f} RPS, {burst['p95_latency_ms']:.1f}ms P95")
    print(f"3. High concurrency (50 parallel): {high_conc['requests_per_second']:.1f} RPS, {high_conc['p95_latency_ms']:.1f}ms P95")
    print(f"\nJitter (consistency): {burst['jitter_ms']:.1f}ms std dev")
    print(f"Latency spread: P99 ({burst['p99_latency_ms']:.1f}ms) - P50 ({burst['p50_latency_ms']:.1f}ms) = {burst['p99_latency_ms'] - burst['p50_latency_ms']:.1f}ms")

    print("\nINTERPRETATION:")
    print("-"*100)
    if burst['p95_latency_ms'] < 500:
        print("[OK] P95 latency under 500ms - Good for auction bidding")
    else:
        print("[!] P95 latency over 500ms - May miss fast bids")

    if burst['jitter_ms'] < 50:
        print("[OK] Low jitter - Consistent response times")
    else:
        print("[!] High jitter - Inconsistent response times")

    if high_conc['requests_per_second'] > burst['requests_per_second'] * 5:
        print("[OK] Python scales well with concurrency for I/O-bound workloads")
    else:
        print("[!] Diminishing returns with high concurrency")

if __name__ == "__main__":
    main()
