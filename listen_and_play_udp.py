import socket
import threading
from queue import Queue
import sounddevice as sd
import argparse

def listen_and_play(
    send_rate=16000,
    recv_rate=44100,
    list_play_chunk_size=1024,
    local_host="0.0.0.0",
    local_port=0,  # 0 means the OS will assign a free port
    remote_host="localhost",
    remote_port=8082,
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_host, local_port))
    local_addr = sock.getsockname()

    print(f"Listening on {local_addr[0]}:{local_addr[1]}")
    print(f"Sending to {remote_host}:{remote_port}")

    stop_event = threading.Event()
    recv_queue = Queue()
    send_queue = Queue()

    def callback_recv(outdata, frames, time, status):
        if not recv_queue.empty():
            data = recv_queue.get()
            outdata[: len(data)] = data
            outdata[len(data) :] = b"\x00" * (len(outdata) - len(data))
        else:
            outdata[:] = b"\x00" * len(outdata)

    def callback_send(indata, frames, time, status):
        if recv_queue.empty():
            data = bytes(indata)
            send_queue.put(data)

    def send(stop_event, send_queue):
        while not stop_event.is_set():
            data = send_queue.get()
            sock.sendto(data, (remote_host, remote_port))

    def recv(stop_event, recv_queue):
        while not stop_event.is_set():
            data, _ = sock.recvfrom(list_play_chunk_size * 2)
            if data:
                recv_queue.put(data)

    try:
        send_stream = sd.RawInputStream(
            samplerate=send_rate,
            channels=1,
            dtype="int16",
            blocksize=list_play_chunk_size,
            callback=callback_send,
        )
        recv_stream = sd.RawOutputStream(
            samplerate=recv_rate,
            channels=1,
            dtype="int16",
            blocksize=list_play_chunk_size,
            callback=callback_recv,
        )
        threading.Thread(target=send_stream.start).start()
        threading.Thread(target=recv_stream.start).start()

        send_thread = threading.Thread(target=send, args=(stop_event, send_queue))
        send_thread.start()
        recv_thread = threading.Thread(target=recv, args=(stop_event, recv_queue))
        recv_thread.start()

        input("Press Enter to stop...")

    except KeyboardInterrupt:
        print("Finished streaming.")

    finally:
        stop_event.set()
        recv_thread.join()
        send_thread.join()
        sock.close()
        print("Connection closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen and play audio over UDP.")
    parser.add_argument("--local_host", default="0.0.0.0", help="Local IP to bind to")
    parser.add_argument("--local_port", type=int, default=0, help="Local port to bind to (0 for auto-assign)")
    parser.add_argument("--remote_host", required=True, help="Remote server IP")
    parser.add_argument("--remote_port", type=int, required=True, help="Remote server port")
    parser.add_argument("--send_rate", type=int, default=16000, help="Send rate in Hz")
    parser.add_argument("--recv_rate", type=int, default=44100, help="Receive rate in Hz")
    parser.add_argument("--list_play_chunk_size", type=int, default=1024, help="Chunk size in bytes")

    args = parser.parse_args()

    listen_and_play(
        send_rate=args.send_rate,
        recv_rate=args.recv_rate,
        list_play_chunk_size=args.list_play_chunk_size,
        local_host=args.local_host,
        local_port=args.local_port,
        remote_host=args.remote_host,
        remote_port=args.remote_port
    )