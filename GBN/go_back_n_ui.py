import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
from go_back_n_protocol import CONFIG, Sender, Receiver, NetworkChannel


# Redirect print to Tkinter Text

class RedirectText:
    def __init__(self, text_widget):
        self.output = text_widget

    def write(self, string):
        self.output.configure(state='normal')
        self.output.insert('end', string)
        self.output.see('end')
        self.output.configure(state='disabled')

    def flush(self):
        pass

# Callback to start simulation
def start_simulation():
    def run():
        try:
            log_output.configure(state='normal')
            log_output.delete("1.0", tk.END)
            log_output.configure(state='disabled')

            config = {
                "sender_window_size": int(sender_window.get()),
                "sequence_number_space": 8,
                "data": list(data_entry.get().strip()),
                "packet_loss": list(map(int, packet_loss_entry.get().strip().split(","))) if packet_loss_entry.get().strip() else [],
                "ack_loss": list(map(int, ack_loss_entry.get().strip().split(","))) if ack_loss_entry.get().strip() else [],
                "propagation_delay": float(delay_entry.get().strip()),
                "corrupted_packets": []
            }

            channel = NetworkChannel(config)
            receiver = Receiver(config, channel)
            sender = Sender(config, channel)

            receiver.start()
            sender_thread = threading.Thread(target=sender.start)
            sender_thread.start()
            sender_thread.join()

            print("\n=== Simulation Complete ===")
            print("Data delivered:", ''.join(receiver.received_data))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    threading.Thread(target=run).start()

# Build GUI
root = tk.Tk()
root.title("Go-Back-N Protocol Simulator")

# Configuration Frame
frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0, sticky="nsew")

fields = [
    ("Sender Window Size", "4"),
    ("Data to Send", "ABCDEF"),
    ("Packet Loss (seq #s comma-separated)", "2"),
    ("ACK Loss (ack #s comma-separated)", ""),
    ("Propagation Delay (seconds)", "0.5"),
]

entries = []
for i, (label, default) in enumerate(fields):
    ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w")
    entry = ttk.Entry(frame, width=25)
    entry.insert(0, default)
    entry.grid(row=i, column=1, sticky="w")
    entries.append(entry)

sender_window, data_entry, packet_loss_entry, ack_loss_entry, delay_entry = entries

# Run Button
run_button = ttk.Button(frame, text="Run Simulation", command=start_simulation, width=60)
run_button.grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=10)

# Log Output
log_output = tk.Text(root, height=20, width=80, wrap="word", state='disabled')
log_output.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

# Enable adaptive resizing
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)
frame.grid_columnconfigure(1, weight=1)

# Redirect print to log_output
sys.stdout = RedirectText(log_output)
sys.stderr = RedirectText(log_output)

root.mainloop()