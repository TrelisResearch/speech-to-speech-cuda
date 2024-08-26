#   python listen_and_play.py --host <server_ip> --port 12345 --sample_rate 16000
import socket
import threading
from queue import Queue
from dataclasses import dataclass, field
import sounddevice as sd
import numpy as np
from transformers import HfArgumentParser

@dataclass
class ListenAndPlayArguments:
    sample_rate: int = field(default=16000, metadata={"help": "In Hz. Default is 16000."})
    chunk_size: int = field(
        default=1024,
        metadata={"help": "The size of data chunks (in bytes). Default is 1024."},
    )
    host: str = field(
        default="localhost",
        metadata={
            "help": "The hostname or IP address for listening and playing. Default is 'localhost'."
        },
    )
    port: int = field(
        default=12345,
        metadata={"help": "The network port for UDP communication. Default is 12345."},
    )

def listen_and_play(
    sample_rate=16000,
    chunk_size=1024,
    host="localhost",
    port=12345,
):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('0.0.0.0', 0))  # Bind to any available port

    print(f"Connecting to {host}:{port}")
    udp_socket.connect((host, port))

    print("Recording and streaming...")

    stop_event = threading.Event()
    recv_queue = Queue()
    send_queue = Queue()

    def callback(indata, outdata, frames, time, status):
        if status:
            print(status)
        
        # Handle sending
        send_queue.put(bytes(indata))
        
        # Handle receiving
        if not recv_queue.empty():
            data = recv_queue.get()
            outdata[:] = np.frombuffer(data, dtype=np.int16).reshape(-1, 1)
        else:
            outdata[:] = 0

    def send(stop_event, send_queue):
        while not stop_event.is_set():
            try:
                data = send_queue.get(timeout=1)
                udp_socket.send(data)
            except Queue.Empty:
                continue

    def recv(stop_event, recv_queue):
        while not stop_event.is_set():
            try:
                data, _ = udp_socket.recvfrom(chunk_size * 2)
                recv_queue.put(data)
            except socket.error:
                continue

    try:
        stream = sd.Stream(
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            blocksize=chunk_size,
            callback=callback
        )

        send_thread = threading.Thread(target=send, args=(stop_event, send_queue))
        recv_thread = threading.Thread(target=recv, args=(stop_event, recv_queue))

        with stream:
            send_thread.start()
            recv_thread.start()
            input("Press Enter to stop...")

    except KeyboardInterrupt:
        print("Finished streaming.")

    finally:
        stop_event.set()
        recv_thread.join()
        send_thread.join()
        udp_socket.close()
        print("Connection closed.")

if __name__ == "__main__":
    parser = HfArgumentParser((ListenAndPlayArguments,))
    (listen_and_play_kwargs,) = parser.parse_args_into_dataclasses()
    listen_and_play(**vars(listen_and_play_kwargs))