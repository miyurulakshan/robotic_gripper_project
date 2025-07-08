import matplotlib.pyplot as plt

def create_comparison_plot(raw_data, filtered_data):
    """
    Generates and displays a static plot comparing raw and filtered data.
    This function is 'blocking' and should be run in a separate thread.
    """
    if not raw_data or not filtered_data:
        print("[Plotter] Warning: Data lists are empty, cannot plot.")
        return

    print(f"[Plotter] Creating comparison plot for {len(raw_data)} data points...")
    
    sample_axis = range(len(raw_data))

    # --- Scientific Plot Setup ---
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot both data streams
    ax.plot(sample_axis, raw_data, 'b-', alpha=0.5, label="Raw Sensor Data")
    ax.plot(sample_axis, filtered_data, 'r-', linewidth=2, label="Kalman Filtered Data")

    # Configure aesthetics
    ax.set_title("Raw vs. Kalman Filtered FSR Data", fontsize=16, weight='bold')
    ax.set_xlabel("Sample Number", fontsize=12)
    ax.set_ylabel("FSR Reading (ADC Value)", fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Set axis limits automatically with a buffer
    y_min = min(raw_data)
    y_max = max(raw_data)
    ax.set_ylim(y_min - 50, y_max + 50)
    ax.set_xlim(0, len(raw_data))
    
    ax.legend()
    plt.tight_layout(pad=1.5)
    
    plt.show()
    print("[Plotter] Plot window closed.")
