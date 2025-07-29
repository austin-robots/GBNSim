import threading
import time
from queue import Queue


# CONFIGURATION


CONFIG = {
    "sender_window_size": 4,
    "sequence_number_space": 8,  # K
    "data": list("ABCDEF"),
    "packet_loss": [2],
    "ack_loss": [],
    "propagation_delay": 0.5,
    "corrupted_packets": []
}


# PACKET CLASS


class Packet:
    def __init__(self, seq_num, data='', is_ack=False):
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack

    def __str__(self):
        return f"{'ACK' if self.is_ack else 'DATA'}(seq={self.seq_num}, data={self.data})"


# NETWORK CHANNEL


class NetworkChannel:
    def __init__(self, config):
        self.packet_loss = set(config["packet_loss"])
        self.ack_loss = set(config["ack_loss"])
        self.propagation_delay = config["propagation_delay"]

        self.sender_to_receiver = Queue()
        self.receiver_to_sender = Queue()

    def send(self, packet):
        def delayed():
            time.sleep(self.propagation_delay)
            if not packet.is_ack and packet.seq_num in self.packet_loss:
                print(f"[Channel] Packet {packet.seq_num} dropped.")
                self.packet_loss.remove(packet.seq_num)
                return
            if packet.is_ack and packet.seq_num in self.ack_loss:
                print(f"[Channel] ACK {packet.seq_num} dropped.")
                self.ack_loss.remove(packet.seq_num)
                return
            target = self.receiver_to_sender if packet.is_ack else self.sender_to_receiver
            target.put(packet)
        threading.Thread(target=delayed, daemon=True).start()


# RECEIVER


class Receiver:
    def __init__(self, config, channel):
        self.expected_seq = 0
        self.K = config["sequence_number_space"]
        self.channel = channel
        self.received_data = []
        self.done = False

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            packet = self.channel.sender_to_receiver.get()
            print(f"[Receiver] Received: {packet}")
            if packet.seq_num == self.expected_seq:
                self.received_data.append(packet.data)
                print(f"[Receiver] Accepted: {packet.data}")
                self.expected_seq = (self.expected_seq + 1) % self.K

                if packet.seq_num == len(CONFIG["data"]) - 1:
                    self.done = True
            else:
                print(f"[Receiver] Out-of-order. Expected {self.expected_seq}, got {packet.seq_num}.")
            ack = Packet(seq_num=(self.expected_seq - 1) % self.K, is_ack=True)
            self.channel.send(ack)


# SENDER


class Sender:
    def __init__(self, config, channel):
        self.data = config["data"]
        self.N = config["sender_window_size"]
        self.K = config["sequence_number_space"]
        self.channel = channel

        self.send_base = 0
        self.next_seq = 0
        self.timer = None
        self.lock = threading.Lock()
        self.unacked = {}
        self.done = False
        self.final_ack_received = False

    def start(self):
        print(f"[SENDER] Will attempt to send: {''.join(self.data)}")
        threading.Thread(target=self.receive_acks, daemon=True).start()

        while self.send_base < len(self.data):
            with self.lock:
                if (self.next_seq - self.send_base) % self.K < self.N and self.next_seq < len(self.data):
                    pkt = Packet(seq_num=self.next_seq % self.K, data=self.data[self.next_seq])
                    self.unacked[self.next_seq % self.K] = pkt
                    self.channel.send(pkt)
                    print(f"[Sender] Sent: {pkt}")
                    if self.send_base == self.next_seq:
                        self.start_timer()
                    self.next_seq += 1
                else:
                    time.sleep(0.05)

            time.sleep(0.01)

        while not self.final_ack_received:
            time.sleep(0.1)
        print("[Sender] All data acknowledged.")
        self.done = True

    def receive_acks(self):
        while True:
            ack = self.channel.receiver_to_sender.get()
            print(f"[Sender] Received: {ack}")
            with self.lock:
                if (ack.seq_num + 1) % self.K > self.send_base % self.K:
                    self.send_base = self.send_base + ((ack.seq_num + 1 - (self.send_base % self.K)) % self.K)
                    self.stop_timer()
                    if self.send_base < self.next_seq:
                        self.start_timer()

                if ack.seq_num == (len(self.data) - 1) % self.K:
                    self.final_ack_received = True
                    break

    def timeout(self):
        with self.lock:
            print(f"[Sender] Timeout. Resending from {self.send_base % self.K}.")
            for i in range(self.send_base, self.next_seq):
                pkt = self.unacked.get(i % self.K)
                if pkt:
                    print(f"[Sender] Retransmitting: {pkt}")
                    self.channel.send(pkt)
            self.start_timer()

    def start_timer(self):
        self.stop_timer()
        self.timer = threading.Timer(2.0, self.timeout)
        self.timer.start()

    def stop_timer(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None


# MAIN


def main():
    channel = NetworkChannel(CONFIG)
    receiver = Receiver(CONFIG, channel)
    sender = Sender(CONFIG, channel)

    receiver.start()
    
    sender_thread = threading.Thread(target=sender.start)
    sender_thread.start()

    sender_thread.join()

    while not (sender.done and receiver.done):
        time.sleep(0.1)

    print("\n=== Simulation Complete ===")
    print("Data delivered:", ''.join(receiver.received_data))

if __name__ == '__main__':
    main()
