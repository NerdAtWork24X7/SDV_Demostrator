import socket
import random
import time
import math


# bind to specific ip on ethernet adapter
## Replace with the IP address of the Ethernet adapter you want to use
#local_ip = '192.168.1.100'  # Your Ethernet adapter's IP
#target_ip = '192.168.1.200'
#target_port = 5005
#
## Create UDP socket
#sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#
## Bind the socket to the local interface
#sock.bind((local_ip, 0))  # Bind to the adapter's IP and an ephemeral port
#
## Send message
#message = b'Hello over Ethernet'
#sock.sendto(message, (target_ip, target_port))



class Server():

    UDP_IP = "0.0.0.0"
    UDP_PORT = 5005
    CHUNK_SIZE = 1024
    ACK_TIMEOUT = 10  # seconds
    Client_addr = None


    def __init__(self, ip=UDP_IP, port=UDP_PORT):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.ip, self.port))
        self.sock.settimeout(self.ACK_TIMEOUT)
        print(f"Server started at {self.ip}:{self.port}")

    def start(self):
        print("Waiting for client...")
        while True:
            data, self.Client_addr = self.sock.recvfrom(512)
            if data.decode() == "READY":
                print(f"Client ready: {self.Client_addr}")
                break

    
    def calculate_rpm(self, speed_kph):
       final_drive = 3.9
       tire_diameter_m = 0.65
       tire_circ = math.pi * tire_diameter_m
       result_rpm = 1000
       selected_gear = "0"
       # Gear ratios from 1st to 6th
       gear_ratios = [3.8, 2.5, 2, 1.5, 0.6, 0.8]
       
       # Desired RPM range
       min_rpm = 1500
       max_rpm = 6000
       # Try gears from highest to lowest
       for i, gear_ratio in reversed(list(enumerate(gear_ratios, start=1))):
           rpm = (speed_kph * gear_ratio * final_drive * 1000) / (tire_circ * 60)
           if min_rpm <= rpm <= max_rpm:
               selected_gear = str(i)
               result_rpm = int(rpm)
               break
       return selected_gear, result_rpm
           
    
    
    
    def send_data(self,speed):

      # Calculate RPM
      gear , rpm = self.calculate_rpm(speed)
      temperature = random.randint(70, 110)
      fuel = random.randint(0, 100)
      #gear = random.choice(['P', 'R', 'N', 'D'])

      # Create a data packet
      data_packet = f"SPEED:{speed},RPM:{rpm},TEMP:{temperature},FUEL:{fuel},GEAR:{gear}"
      #print(f"Data packet: {data_packet}")
      # Send the data packet to the client
      self.sock.sendto(data_packet.encode(), self.Client_addr)
      print(f"Sent data: {data_packet}")






