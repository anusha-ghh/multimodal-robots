import socket, os
import speech_recognition as sr

HOST = '127.0.0.1' # localhost
PORT = 7777        # port
COMMANDS = ["play music", "increase", "decrease", "go to", "approach"]

def is_command(text):
	for command in COMMANDS:
		if command in text:
			return True
	return False

def listen():
	"""
	Listen for audio input.
	"""
	listen_limit = 30.0
	phrase_limit = 10.0
	mic = sr.Recognizer()

	try:
		with sr.Microphone() as source:
			mic.adjust_for_ambient_noise(source, duration=1)
			print(f"Adjusted for ambient noise.")
			audio = mic.listen(
					source,
					timeout=listen_limit,
					phrase_time_limit = phrase_limit)
			text = mic.recognize_google(audio)
			text = text.lower()
			print(f"Said {text}")
			return text
	except Exception as e:
			print(f"Could not understand : {e}")
			return ""

def send_info_server():
	"""
	Wait until a command is spoken, and
	send the text to the server.
	"""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
		client_socket.connect((HOST, PORT))
		while True:
			message = listen()

			if not message:
				continue

			if message == "quit":
				break

			if is_command(message):
				message = "voice:" + message + "\n"
				client_socket.sendall(message.encode())# send
				data = client_socket.recv(1024)  # response
	print("Voice disconnected.")


if __name__ == "__main__":
	send_info_server()
