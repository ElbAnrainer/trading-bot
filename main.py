import time

from cli import (
    ask_period,
    parse_args,
    choose_interval,
    normalize_period_input,
)
from analysis_engine import (
    run_analysis,
    get_signal_from_df,
    build_future_candidates,
)
from output import print_runtime


def run(period, top_n, min_volume, long_mode):
    return run_analysis(
        period=period,
        top_n=top_n,
        min_volume=min_volume,
        long_mode=long_mode,
    )


if __name__ == "__main__":
    long_mode, top_n, min_volume, period_override = parse_args()
    period = period_override or ask_period()

    start_time = time.perf_counter()
    run(
        period=period,
        top_n=top_n,
        min_volume=min_volume,
        long_mode=long_mode,
    )
    elapsed = time.perf_counter() - start_time
    print_runtime(elapsed)
