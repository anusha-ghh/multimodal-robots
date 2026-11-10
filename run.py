import subprocess
import sys

processes = []

try:
    processes.append(subprocess.Popen([sys.executable, "server.py"]))

    processes.append(subprocess.Popen([sys.executable, "voice.py"]))

    processes.append(subprocess.Popen([sys.executable, "gesture_detector.py"]))

    for process in processes:
        process.wait()

except KeyboardInterrupt:
    print("\nStopping all processes...")

finally:
    for process in processes:
        process.terminate()

    for process in processes:
        process.wait()
