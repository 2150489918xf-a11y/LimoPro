"""Exercise the fixed EKF launch using a virtual serial port, never real hardware."""

import math
import os
import pty
import signal
import struct
import subprocess
import tempfile
import time

import pytest
import rclpy
from nav_msgs.msg import Odometry
from rcl_interfaces.srv import GetParameters
from sensor_msgs.msg import Imu
from tf2_msgs.msg import TFMessage


def packet(identifier, values):
    data = struct.pack('>hhhh', *values)
    return b'\x55\x0e' + struct.pack('>H', identifier) + data + b'\x00' + bytes([sum(data) & 255])


def test_fixed_ekf_serial_input(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID', '196')
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')
    monkeypatch.delenv('CYCLONEDDS_URI', raising=False)
    master, slave = pty.openpty()
    os.set_blocking(master, False)
    rclpy.init()
    node = rclpy.create_node('fixed_ekf_test')
    filtered, raw, imus, transforms = [], [], [], []
    node.create_subscription(Odometry, '/odom', filtered.append, 100)
    node.create_subscription(Odometry, '/odom/raw', raw.append, 100)
    node.create_subscription(Imu, '/imu', imus.append, 100)
    node.create_subscription(TFMessage, '/tf', transforms.append, 100)
    with tempfile.TemporaryFile(mode='w+') as log:
        process = subprocess.Popen([
            'ros2', 'launch', 'limo_bringup', 'limo_start.launch.py',
            'start_lidar:=false', 'port_name:=' + os.ttyname(slave),
        ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.05)
                if node.count_publishers('/imu') == 1 and node.count_publishers('/odom') == 1:
                    break
                assert process.poll() is None, 'launch exited before discovery'
            assert node.count_publishers('/odom') == 1
            assert node.count_publishers('/odom/raw') == 1
            started, next_frame, index = time.monotonic(), time.monotonic(), 0
            while time.monotonic() - started < 5:
                if time.monotonic() >= next_frame:
                    # Deliberately contradict raw pose/yaw rate: EKF must only use
                    # the configured chassis vx/vy and positive IMU gyro Z.
                    yaw = 11000 if index % 2 else -7000
                    data = packet(0x322, (0, 0, round(math.degrees(0.25) * 100), 0))
                    data += packet(0x323, (yaw, 0, 0, 0))
                    data += packet(0x221, (500, -750, 0, 0))
                    os.write(master, data)
                    next_frame += 0.02
                    index += 1
                rclpy.spin_once(node, timeout_sec=0.002)
                try:
                    os.read(master, 4096)
                except BlockingIOError:
                    pass
            assert len(filtered) > 150 and len(raw) > 150 and len(imus) > 150
            assert any(t.header.frame_id == 'odom' and t.child_frame_id == 'base_link'
                       for msg in transforms for t in msg.transforms)
            for owner, parameter, expected in [('limo_base', 'pub_odom_tf', False),
                                                ('local_ekf', 'publish_tf', True)]:
                client = node.create_client(GetParameters, '/' + owner + '/get_parameters')
                assert client.wait_for_service(timeout_sec=3)
                future = client.call_async(GetParameters.Request(names=[parameter]))
                rclpy.spin_until_future_complete(node, future, timeout_sec=3)
                assert future.result().values[0].bool_value is expected
            last = filtered[-1]
            q = last.pose.pose.orientation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            assert last.header.frame_id == 'odom' and last.child_frame_id == 'base_link'
            assert last.twist.twist.angular.z == pytest.approx(0.25, abs=0.03)
            assert 0.95 < yaw < 1.5
            assert last.pose.pose.position.x > 1.4 and last.pose.pose.position.y > 0.8
            assert raw[-1].twist.covariance[0] == pytest.approx(0.0025)
            assert imus[-1].angular_velocity_covariance[8] == pytest.approx(0.0004)
            assert all(math.isfinite(value) for value in last.pose.covariance)
            log.seek(0)
            assert 'Check sum failed' not in log.read()
        except Exception:
            log.seek(0)
            print(log.read())
            raise
        finally:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=7)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            node.destroy_node()
            rclpy.shutdown()
            os.close(master)
            os.close(slave)
