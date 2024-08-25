import socket
import threading
from queue import Queue
from dataclasses import dataclass, field
import sounddevice as sd
from transformers import HfArgumentParser
import time
import struct

@dataclass
class ListenAndPlayArguments:
    send_rate: int = field(default=16000, metadata={"help": "In Hz. Default is 16000."})
    recv_rate: int = field(default=44100, metadata={"help": "In Hz. Default is 44100."})
    chunk_size: int = field(
        default=1024,
        metadata={"help": "The size of data chunks (in bytes). Default is 1024."},
    )
    host: str = field(
        default="localhost",
        metadata={"help": "The hostname or IP address of the server. Default is 'localhost'."},
    )
    port: int = field(
        default=8082,
        metadata={"help": "The network port for sending and receiving data. Default is 8082."},
    )

def listen_and_play(
    send_rate=16000,
    recv_rate=44100,
    chunk_size=1024,
    host="localhost",
    port=8082,
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (host, port)

    print(f"Attempting to connect to {host}:{port}")
    
    stop_event = threading.Event()
    recv_queue = Queue()
    send_queue = Queue()

    def send(stop_event, send_queue):
        while not stop_event.is_set():
            if not send_queue.empty():
                data = send_queue.get()
                print(f"Sending {len(data)} bytes to server")
                sock.sendto(data, server_address)
            else:
                # Send a heartbeat message
                sock.sendto(b"HEARTBEAT", server_address)
            time.sleep(0.1)  # Small delay to prevent busy-waiting

    def recv(stop_event, recv_queue):
        while not stop_event.is_set():
            try:
                data, _ = sock.recvfrom(chunk_size * 2)
                if data:
                    if data == b"END":
                        print("Received end of audio stream")
                    else:
                        print(f"Received {len(data)} bytes from server")
                        recv_queue.put(data)
            except socket.error as e:
                print(f"Socket error: {e}")
            time.sleep(0.01)  # Small delay to prevent busy-waiting

    def callback_recv(outdata, frames, time, status):
        if not recv_queue.empty():
            data = recv_queue.get()
            outdata[:len(data)] = data
            outdata[len(data):] = b"\x00" * (len(outdata) - len(data))
        else:
            outdata[:] = b"\x00" * len(outdata)

    def callback_send(indata, frames, time, status):
        data = bytes(indata)
        send_queue.put(data)

    try:
        send_stream = sd.RawInputStream(
            samplerate=send_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_size,
            callback=callback_send,
        )
        recv_stream = sd.RawOutputStream(
            samplerate=recv_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_size,
            callback=callback_recv,
        )
        
        send_thread = threading.Thread(target=send, args=(stop_event, send_queue))
        recv_thread = threading.Thread(target=recv, args=(stop_event, recv_queue))
        
        send_stream.start()
        recv_stream.start()
        send_thread.start()
        recv_thread.start()

        print("Streams and threads started. Sending initial message...")
        sock.sendto(b"Hello, server! This is the client!", server_address)

        input("Press Enter to stop...")

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        print("Cleaning up...")
        stop_event.set()
        if 'send_stream' in locals():
            send_stream.stop()
        if 'recv_stream' in locals():
            recv_stream.stop()
        recv_thread.join()
        send_thread.join()
        sock.close()
        print("Connection closed.")

if __name__ == "__main__":
    parser = HfArgumentParser((ListenAndPlayArguments,))
    (listen_and_play_kwargs,) = parser.parse_args_into_dataclasses()
    listen_and_play(**vars(listen_and_play_kwargs))