import matplotlib.pyplot as plt
import numpy as np # Import numpy

def calculate_and_print_stats(raw_data, filtered_data):
    """Calculates and prints key performance metrics for the filter."""
    
    # --- 1. Standard Deviation for Noise Measurement ---
    raw_std = np.std(raw_data)
    filtered_std = np.std(filtered_data)
    
    # --- 2. Root Mean Squared Error for Tracking ---
    # Ensure lists are the same size, which they should be
    raw_array = np.array(raw_data)
    filtered_array = np.array(filtered_data)
    rmse = np.sqrt(np.mean((filtered_array - raw_array)**2))
    
    print("\n--- Filter Performance Analysis ---")
    print(f"Standard Deviation (Raw):      {raw_std:.4f}  (Higher = Noisier)")
    print(f"Standard Deviation (Filtered): {filtered_std:.4f}  (Lower = Smoother)")
    print(f"RMSE between signals:        {rmse:.4f}  (Measures overall difference)")
    print("-----------------------------------\n")

def create_comparison_plot(raw_data, filtered_data):
    """
    Generates and displays a static plot comparing raw and filtered data.
    """
    if not raw_data or not filtered_data:
        print("[Plotter] Warning: No data points to plot.")
        return

    # --- NEW: Calculate and print stats before plotting ---
    calculate_and_print_stats(raw_data, filtered_data)

    print(f"[Plotter] Creating comparison plot for {len(raw_data)} data points...")
    
    sample_axis = range(len(raw_data))

    fig, ax = plt.subplots(figsize=(12, 7))
    
    ax.plot(sample_axis, raw_data, 'b-', alpha=0.5, label=f"Raw Data (Std Dev: {np.std(raw_data):.2f})")
    ax.plot(sample_axis, filtered_data, 'r-', linewidth=2, label=f"Kalman Filtered (Std Dev: {np.std(filtered_data):.2f})")

    ax.set_title("Raw vs. Kalman Filtered FSR Data", fontsize=16, weight='bold')
    ax.set_xlabel("Sample Number", fontsize=12)
    ax.set_ylabel("FSR Reading (ADC Value)", fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    y_min = min(raw_data)
    y_max = max(raw_data)
    ax.set_ylim(y_min - 50, y_max + 50)
    ax.set_xlim(0, len(raw_data))
    
    ax.legend()
    plt.tight_layout(pad=1.5)
    
    plt.show()
    print("[Plotter] Plot window closed.")
