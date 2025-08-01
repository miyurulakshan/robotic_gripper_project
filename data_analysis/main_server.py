import asyncio
import websockets

# Import our custom modules
from data_analysis.plotter import create_comparison_plot
from data_analysis.kalman_filter import KalmanFilter

# --- Configuration ---
SAMPLE_BATCH_SIZE = 1000
collected_raw_data = []
collected_filtered_data = []

# Initialize the Kalman Filter
kf = KalmanFilter()

async def handler(websocket):
    """
    Handles connections, collects data, applies the filter, and triggers plotting.
    """
    global collected_raw_data, collected_filtered_data, kf
    print(f"Client connected from {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
                raw_data_point = int(message)
                filtered_data_point = kf.update(raw_data_point)
                
                print(f"Raw: {raw_data_point:<4} -> Filtered: {filtered_data_point:.2f}")

                collected_raw_data.append(raw_data_point)
                collected_filtered_data.append(filtered_data_point)

                # Check if we have reached the limit
                if len(collected_raw_data) >= SAMPLE_BATCH_SIZE:
                    print(f"Collected {SAMPLE_BATCH_SIZE} data points. Generating plot...")
                    
                    # Call the plotting function directly.
                    # This will PAUSE the server until the plot window is closed.
                    create_comparison_plot(collected_raw_data, collected_filtered_data)
                    
                    # Clear the lists to start collecting the next batch
                    print("Ready for next batch.")
                    collected_raw_data.clear()
                    collected_filtered_data.clear()

            except ValueError:
                print(f"Warning: Could not parse '{message}' as an integer.")

    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred in handler: {e}")

async def main():
    """Starts the WebSocket server."""
    print(f"Starting WebSocket server. Will plot after every {SAMPLE_BATCH_SIZE} readings.")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
