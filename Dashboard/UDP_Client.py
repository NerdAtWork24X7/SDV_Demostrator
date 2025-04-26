import socket
import select
import threading

class Client:
    def __init__(self, udp_ip="localhost", udp_port=5005):
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.data_dict = {
            'SPEED': 0,
            'RPM': 0,
            'TEMP': 0,
            'FUEL': 0,
            'GEAR': 'N'
        }

    def data_callback(self):
        print(f"Callback: Received Data: Speed={self.data_dict['SPEED']} RPM={self.data_dict['RPM']} Temp={self.data_dict['TEMP']} Fuel={self.data_dict['FUEL']} Gear={self.data_dict['GEAR']}")

    def client_thread(self, callback):
        def run():
            # Notify server
            self.sock.sendto("READY".encode(), (self.udp_ip, self.udp_port))

            print("Waiting for data...")

            while True:
                # Use select to wait for data on the socket
                ready_sockets, _, _ = select.select([self.sock], [], [], None)

                for s in ready_sockets:
                    if s == self.sock:
                        try:
                            # Receive data packet from server
                            data, addr = self.sock.recvfrom(1024)
                            decoded_data = data.decode()

                            # Parse the received data
                            data_parts = decoded_data.split(',')
                            self.data_dict = {key_value.split(':')[0]: key_value.split(':')[1] for key_value in data_parts}

                            # Call the callback function with the received data
                            #callback()

                            # Send acknowledgment back to the server
                            self.sock.sendto("ACK".encode(), addr)

                        except socket.timeout:
                            print("Timeout waiting for data...")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        print("Client thread started.")

