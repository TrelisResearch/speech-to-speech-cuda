import socket
import threading
from queue import Queue
import sounddevice as sd
import argparse

def listen_and_play(
    send_rate=16000,
    recv_rate=44100,
    chunk_size=1024,
    remote_host="localhost",
    remote_port=8082,
):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Connecting to {remote_host}:{remote_port}")

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
        data = bytes(indata)
        send_queue.put(data)

    def send(stop_event, send_queue):
        while not stop_event.is_set():
            data = send_queue.get()
            sock.sendto(data, (remote_host, remote_port))

    def recv(stop_event, recv_queue):
        while not stop_event.is_set():
            try:
                data, _ = sock.recvfrom(chunk_size * 2)
                if data:
                    recv_queue.put(data)
            except socket.error:
                pass

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
    parser = argparse.ArgumentParser(description="Send and receive audio over UDP.")
    parser.add_argument("--remote_host", required=True, help="Remote server IP")
    parser.add_argument("--remote_port", type=int, required=True, help="Remote server port")
    parser.add_argument("--send_rate", type=int, default=16000, help="Send rate in Hz")
    parser.add_argument("--recv_rate", type=int, default=44100, help="Receive rate in Hz")
    parser.add_argument("--chunk_size", type=int, default=1024, help="Chunk size in bytes")

    args = parser.parse_args()

    listen_and_play(
        send_rate=args.send_rate,
        recv_rate=args.recv_rate,
        chunk_size=args.chunk_size,
        remote_host=args.remote_host,
        remote_port=args.remote_port
    )