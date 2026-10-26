import socket, threading

HOST = "127.0.0.1" # localhost
PORT = 7777

def handle_client(conn, addr):
	while True:
		try:
			data = conn.recv(1024)
			if not data:
				break
			print(f"Received : {data.decode()}")
			conn.sendall(f"Server response: {data.decode()}"
				.encode())
		except ConnectionResetError:
			print(f"Client has disconnected.")
	conn.close()

def start_server():
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
		server_socket.bind((HOST, PORT))
		server_socket.listen()
		print(f"Server listening...")
	
		while True:
			conn, addr = server_socket.accept()
			thread = threading.Thread(target=handle_client,
				args=(conn, addr))
			thread.start()

if __name__ == "__main__":
	start_server()

	

	
