from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from lick_analysis import load_lickometer_data


# Point this directly to the lickometer CSV to analyze.

# p = r"C:\Users\daswyga\Desktop\modular_lick_data\2026_10_28\test_2026_10_28_110203.csv"
p = r"C:\Users\daswyga\Desktop\modular_lick_data\2026_10_28\test_2026_10_28_112928.csv"
p = r"C:\Users\daswyga\Desktop\modular_lick_data\2026_10_28\test_2026_10_28_114554.csv"
LICKOMETER_CSV = Path(p)

CAP_DIVISOR = 1000
def main() -> None:
    data = load_lickometer_data(LICKOMETER_CSV)
    data['left'] = data['left']/CAP_DIVISOR
    data['right'] = data['right']/CAP_DIVISOR
    elapsed_values_ms = data["elapsed_us"].to_numpy(dtype=np.float64) / 1_000
    elapsed_ms = np.sort(elapsed_values_ms)
    cumulative_probability = np.arange(1, len(elapsed_ms) + 1) / len(elapsed_ms)
    threshold_ms = 30
    excess_time_ms = np.maximum(elapsed_values_ms - threshold_ms, 0).sum()
    recording_time_ms = elapsed_values_ms.sum()
    excess_time_proportion = excess_time_ms / recording_time_ms

    figure, axes = plt.subplots(2, 1, figsize=(12, 7), constrained_layout=True)
    figure.suptitle(LICKOMETER_CSV.name)

    axes[0].plot(data["time_s"], data["left"], linewidth=0.8)
    axes[0].plot(
        data["time_s"], data["right"], linewidth=0.8, color="tab:orange"
    )
    axes[0].set(
        xlabel="Time (s)",
        ylabel=f"Capacitance (counts x {CAP_DIVISOR})",
    )
    axes[0].legend(("Left", "Right"))
    axes[0].grid(alpha=0.25)
    left_mean = data["left"].mean()
    left_std = data["left"].std()
    right_mean = data["right"].mean()
    right_std = data["right"].std()
    axes[0].text(
        0.99,
        0.98,
        f"Left: {left_mean:.0f} ± {left_std:.2f}\n"
        f"Right: {right_mean:.0f} ± {right_std:.2f}",
        transform=axes[0].transAxes,
        ha="right",
        va="top",
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
    )

    axes[1].plot(elapsed_ms, cumulative_probability, linewidth=1.2)
    axes[1].set(
        xlabel="Loop interval (ms)",
        ylabel="Cumulative probability",
        ylim=(0, 1),
    )
    axes[1].set_xscale("log")
    axes[1].grid(alpha=0.25)
    axes[1].text(
        0.97,
        0.05,
        f"t>{threshold_ms}ms: {excess_time_proportion:.2%}\n"
        f"Mean: {np.mean(elapsed_ms):.1f} ms",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "0.8"},
    )
    plt.show()
    


if __name__ == "__main__":
    main()
