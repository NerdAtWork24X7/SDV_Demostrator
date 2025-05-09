#!/usr/bin/env python

# Copyright (c) 2020 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Script that render multiple sensors in the same pygame window

By default, it renders four cameras, one LiDAR and one Semantic LiDAR.
It can easily be configure for any different number of sensors. 
To do that, check lines 290-308.
"""

import glob
import os
import sys
import cv2
import math
import UDP_Server


try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import argparse
import random
import time
import numpy as np


try:
    import pygame
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_q
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')

class CustomTimer:
    def __init__(self):
        try:
            self.timer = time.perf_counter
        except AttributeError:
            self.timer = time.time

    def time(self):
        return self.timer()

class DisplayManager:
    def __init__(self, grid_size, window_size):
        pygame.init()
        pygame.font.init()
        self.display = pygame.display.set_mode(window_size, pygame.HWSURFACE | pygame.DOUBLEBUF)

        self.grid_size = grid_size
        self.window_size = window_size
        self.sensor_list = []

    def get_window_size(self):
        return [int(self.window_size[0]), int(self.window_size[1])]

    def get_display_size(self):
        return [int(self.window_size[0]/self.grid_size[1]), int(self.window_size[1]/self.grid_size[0])]

    def get_display_offset(self, gridPos):
        dis_size = self.get_display_size()
        return [int(gridPos[1] * dis_size[0]), int(gridPos[0] * dis_size[1])]

    def add_sensor(self, sensor):
        self.sensor_list.append(sensor)

    def get_sensor_list(self):
        return self.sensor_list

    def render(self):
        if not self.render_enabled():
            return

        for s in self.sensor_list:
            s.render()

        pygame.display.flip()

    def destroy(self):
        for s in self.sensor_list:
            s.destroy()

    def render_enabled(self):
        return self.display != None

class SensorManager:
    cont = 0

    def __init__(self, world, display_man, sensor_type, transform, attached, sensor_options, display_pos):
        self.surface = None
        self.world = world
        self.display_man = display_man
        self.display_pos = display_pos
        self.sensor = self.init_sensor(sensor_type, transform, attached, sensor_options)
        self.sensor_options = sensor_options
        self.timer = CustomTimer()

        self.time_processing = 0.0
        self.tics_processing = 0

        self.display_man.add_sensor(self)

    def init_sensor(self, sensor_type, transform, attached, sensor_options):
        if sensor_type == 'RGBCamera':
            camera_bp = self.world.get_blueprint_library().find('sensor.camera.rgb')
            disp_size = self.display_man.get_display_size()
            camera_bp.set_attribute('image_size_x', str(disp_size[0]))
            camera_bp.set_attribute('image_size_y', str(disp_size[1]))

            for key in sensor_options:
                camera_bp.set_attribute(key, sensor_options[key])

            camera = self.world.spawn_actor(camera_bp, transform, attach_to=attached)
            camera.listen(self.save_rgb_image)

            return camera
        
        else:
            return None

    def get_sensor(self):
        return self.sensor


    def make_coordinates(self, image, line_parameter):
      slope, intercept = line_parameter
      y1 = image.shape[0]
      y2 = int(y1 * (3 / 5))
      x1 = int((y1 - intercept) / slope)
      x2 = int((y2 - intercept) / slope)
      return np.array([x1, y1, x2, y2])        
    
    def detect_road_lanes(self, image):
      #Canny function
      gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
      blurred = cv2.GaussianBlur(gray, (5, 5), 0)
      Canny_img = cv2.Canny(blurred, 50, 150)

       
      #Region of interest
      height = Canny_img.shape[0]
      polygons = np.array([[(0,height-80),(800,height-80),(400,300)]])
      mask = np.zeros_like(Canny_img)
      cv2.fillPoly(mask, polygons, [255,255,255])      
      masked_image = cv2.bitwise_and(Canny_img, mask)

      #Step 10: Apply Hough Line Transform to detect straight lines in the ROI
      lines = cv2.HoughLinesP(masked_image, 2, np.pi / 180, threshold=50, minLineLength=10, maxLineGap=5)
       
      # Step 11: Draw the lines on the original image
      lane_image = np.copy(image)
      
      left_fit = []
      right_fit = []
      if lines is not None:
        for line in lines:
          x1, y1, x2, y2 = line.reshape(4)
          parameters = np.polyfit((x1, x2), (y1, y2), 1)
          slope = parameters[0]
          intercept = parameters[1]
          
          if slope > 0.5 and slope < 1.5:
            right_fit.append((slope, intercept))
          elif slope < -0.5 and slope > -1.5:
            left_fit.append((slope, intercept)) 

        if len(left_fit) > 0: 
          left_fit_average = np.average(left_fit, axis=0)
          left_line = self.make_coordinates(lane_image, left_fit_average)    
          x1, y1, x2, y2 = left_line
          parameters = np.polyfit((x1, x2), (y1, y2), 1)
          slope = parameters[0]
          if slope < -0.7 and slope > -1.0:
            cv2.line(lane_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
            #print("left_line", len(left_line))

        
        if len(right_fit) > 0:      
          right_fit_average = np.average(right_fit, axis=0)
          right_line = self.make_coordinates(lane_image, right_fit_average)
          x1, y1, x2, y2 = right_line
          parameters = np.polyfit((x1, x2), (y1, y2), 1)
          slope = parameters[0]  
          if slope > 0.7 and slope < 1.0:
           cv2.line(lane_image, (x1, y1), (x2, y2), (0, 0, 255), 3)


        #if lines is not None:
        #    for line in lines:
        #        x1, y1, x2, y2 = line[0]
        #        slope = (y2 - y1) / (x2 - x1)
        #        if (slope > 0.5 and slope < 1.5) or (slope < -0.5 and slope > -1.5):
        #            cv2.line(lane_image, (x1, y1), (x2, y2), (0, 255, 0), 3)  # Green lines for lane

      
      return lane_image
       
    
    def save_rgb_image(self, image):
        t_start = self.timer.time()
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        lane_image = self.detect_road_lanes(array)

        if self.display_man.render_enabled():
            self.surface = pygame.surfarray.make_surface(lane_image.swapaxes(0, 1))

        t_end = self.timer.time()
        self.time_processing += (t_end-t_start)
        self.tics_processing += 1

    def render(self):
        if self.surface is not None:
            offset = self.display_man.get_display_offset(self.display_pos)
            self.display_man.display.blit(self.surface, offset)

    def destroy(self):
        self.sensor.destroy()

def run_simulation(args, client):
    """This function performed one test run using the args parameters
    and connecting to the carla client passed.
    """

    display_manager = None
    vehicle = None
    vehicle_list = []
    timer = CustomTimer()
    udpserver = UDP_Server.Server()
    udpserver.start()

    try:
        # Getting the world and
        world = client.get_world()

        original_settings = world.get_settings()

        if args.sync:
            traffic_manager = client.get_trafficmanager(8000)
            settings = world.get_settings()
            traffic_manager.set_synchronous_mode(True)
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 0.05
            world.apply_settings(settings)


        # Instanciating the vehicle to which we attached the sensors
        bp = world.get_blueprint_library().filter('charger_2020')[0]
        vehicle = world.spawn_actor(bp, random.choice(world.get_map().get_spawn_points()))
        vehicle_list.append(vehicle)
        vehicle.set_autopilot(True)

        # Set light state
        light_state = carla.VehicleLightState.NONE  # Initially set all lights to OFF

        # To turn on the headlights, brake lights, and indicator, for example
        light_state = carla.VehicleLightState( 
            carla.VehicleLightState.LowBeam
        )

        vehicle.set_light_state(light_state)  # Apply the light state

        # Display Manager organize all the sensors an its display in a window
        # If can easily configure the grid and the total window size
        display_manager = DisplayManager(grid_size=[1, 1], window_size=[args.width, args.height])

        # Then, SensorManager can be used to spawn RGBCamera, LiDARs and SemanticLiDARs as needed
        # and assign each of them to a grid position, 
        SensorManager(world, display_manager, 'RGBCamera', carla.Transform(carla.Location(x=1.2, z=1.5), carla.Rotation(yaw=+00)), 
                      vehicle, {}, display_pos=[0, 0])


        #Simulation loop
        call_exit = False
        clock = pygame.time.Clock()
        while True:
            start_time = time.time()  # Record the start time of the loop
            # Carla Tick
            if args.sync:
                world.tick()
            else:
                world.wait_for_tick()

            # Render received data
            display_manager.render()
            v = vehicle.get_velocity()
            Speed = int(3.6 * math.sqrt(v.x**2 + v.y**2 + v.z**2))
            udpserver.send_data(speed=Speed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    call_exit = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == K_ESCAPE or event.key == K_q:
                        call_exit = True
                        break

            if call_exit:
                break

            # Measure the time taken for processing and rendering
            processing_time = time.time() - start_time  # Time taken for processing this frame
    
            # Calculate the remaining time to maintain 20 FPS
            time_to_sleep = max(0, 0.045 - processing_time)  # 50ms per frame (20 FPS)
    
            # Sleep to maintain 20 FPS
            time.sleep(time_to_sleep)
            clock.tick()
            print('Client:%16.0f FPS  Speed:%15.0f km/h' % (clock.get_fps(), Speed))



    finally:
        if display_manager:
            display_manager.destroy()

        client.apply_batch([carla.command.DestroyActor(x) for x in vehicle_list])
        world.apply_settings(original_settings)



def main():
    argparser = argparse.ArgumentParser(
        description='CARLA Camera Sensor')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '--sync',
        action='store_true',
        help='Synchronous mode execution')
    argparser.add_argument(
        '--async',
        dest='sync',
        action='store_false',
        help='Asynchronous mode execution')
    argparser.set_defaults(sync=True)
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        #default='1280x720',
        default='800x600',
        help='window resolution (default: 1280x720)')

    args = argparser.parse_args()

    args.width, args.height = [int(x) for x in args.res.split('x')]

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(5.0)
        run_simulation(args, client)

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()