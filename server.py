import socket, threading, time

HOST = "127.0.0.1" # localhost
PORT = 7777


class Server:

        def __init__(self):
                self._voice = ""
                self._gesture = ""
                self._prev_gesture = None
                self._gesture_time_start = None
                self._lock = threading.Lock()

        def check_inputs(self):
                while True:
                        self.process_inputs()
                        time.sleep(0.05)

        def process_inputs(self):
                with self._lock:
                        if not self._voice:
                                return

                        if not self._gesture:
                                return

                        if self._gesture_time_start is None:
                                return

                        duration = time.monotonic() - self._gesture_time_start
                            
                        # at least 1 second.
                        if duration < GESTURE_HOLD_TIME:
                                return

                        current_pair = (self._voice, self._gesture)

                        # Prevent processing the same pair repeatedly.
                        if current_pair == self._last_processed:
                                return

                        if self.is_valid_combination(
                                self._voice,
                                self._gesture
                                ):

                                print("\n--- MATCH FOUND ---")
                                print(f"Voice: {self._voice}")
                                print(f"Gesture: {self._gesture}")
                                print(f"Gesture duration: {duration:.2f}s\n")
                                                                                    

                        self._last_processed = current_pair
                        self._voice = ""

        def handle_client(self, conn, addr):
                buffer = ""
                new_gesture = "NONE"
                
                try:
                        while True:
                                data = conn.recv(1024)
                                if not data:
                                        break
                                buffer += data.decode()
                                while "\n" in buffer:
                                        message, buffer = buffer.split("\n", 1)
                                        message = message.strip()

                                        if not message:
                                                continue

                                        print(f"Received: {message}")

                                        with self._lock:
                                                if message.startswith("voice:"):
                                                        self._voice = message[6:].strip()
                                                elif message.startswith("gesture:"):
                                                        new_gesture = message[8:].strip()

                                                if new_gesture != self._gesture:
                                                        self._gesture = new_gesture

                                                if new_gesture == "NONE":
                                                        self._gesture_start = None

                                                else:
                                                        self._gesture_start = time.monotonic()

                                                self._last_processed = None

                                        self.process_inputs()
                                        
                except ConnectionResetError:
                        print(f"Client has disconnected.")

                finally:
                        conn.close()

        def start_server(self):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                        server_socket.setsockopt(
                                socket.SOL_SOCKET,
                                socket.SO_REUSEADDR,
                                1)
                        server_socket.bind((HOST, PORT))
                        server_socket.listen()
                        print(f"Server listening...")


                        threading.Thread(
                                target=self.check_inputs,
                                daemon=True).start()
                        
                        while True:
                                conn, addr = server_socket.accept()
                                thread = threading.Thread(
                                        target=self.handle_client,
                                        args=(conn, addr),
                                        daemon=True)
                                thread.start()
			
			
def main():
        s = Server()
        s.start_server()


if __name__ == "__main__":
	main()

	

	
