"""Registry and end-to-end serial/EKF tests; only a virtual serial port is opened."""

import math
import os
from pathlib import Path
import pty
import runpy
import signal
import struct
import subprocess
import tempfile
import time

import pytest
import rclpy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from rcl_interfaces.srv import GetParameters
from tf2_msgs.msg import TFMessage
import yaml


PACKAGE = Path(__file__).resolve().parents[1]
REGISTRY = PACKAGE / 'param' / 'local_odometry.yaml'
LOAD = runpy.run_path(str(PACKAGE / 'launch' / 'limo_start.launch.py'))['load_profile']


def test_profiles_and_rejected_tf_conflict():
    registry = yaml.safe_load(REGISTRY.read_text())
    assert LOAD(REGISTRY, 'default')[0] == registry['default_profile']
    assert LOAD(REGISTRY, 'raw')[1]['driver']['publish_tf'] is True
    ekf = LOAD(REGISTRY, 'ekf')[1]
    assert ekf['driver']['publish_tf'] is False
    params = ekf['nodes'][0]['parameters']
    assert [i for i, enabled in enumerate(params['odom0_config']) if enabled] == [6, 7]
    assert [i for i, enabled in enumerate(params['imu0_config']) if enabled] == [11]
    with pytest.raises(ValueError, match='Unknown odometry profile'):
        LOAD(REGISTRY, 'typo')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as stream:
        registry['profiles']['ekf']['driver']['publish_tf'] = True
        yaml.safe_dump(registry, stream)
        stream.flush()
        with pytest.raises(ValueError, match='driver TF off'):
            LOAD(stream.name, 'ekf')
        registry['profiles']['ekf']['driver']['publish_tf'] = False
        registry['profiles']['ekf']['driver']['twist_linear_variance'] = 0
        stream.seek(0)
        stream.truncate()
        yaml.safe_dump(registry, stream)
        stream.flush()
        with pytest.raises(ValueError, match='positive variance'):
            LOAD(stream.name, 'ekf')


def packet(identifier, values):
    data = struct.pack('>hhhh', *values)
    return b'\x55\x0e' + struct.pack('>H', identifier) + data + b'\x00' + bytes([sum(data) & 255])


def yaw_of(msg):
    q = msg.pose.pose.orientation
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


@pytest.mark.parametrize('profile', ['raw', 'ekf'])
def test_virtual_serial_pipeline(profile, monkeypatch):
    # The child launch shares this isolated ROS domain, never the real car's graph.
    monkeypatch.setenv('ROS_DOMAIN_ID', '196')
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')
    monkeypatch.delenv('CYCLONEDDS_URI', raising=False)
    master, slave = pty.openpty()
    os.set_blocking(master, False)
    rclpy.init()
    node = rclpy.create_node('odometry_pipeline_test')
    output, raw, imus, odom_transforms = [], [], [], []
    node.create_subscription(Odometry, '/odom', output.append, 100)
    node.create_subscription(Odometry, '/odom/raw', raw.append, 100)
    node.create_subscription(Imu, '/imu', imus.append, 100)

    def on_tf(msg):
        odom_transforms.extend(t for t in msg.transforms
                               if t.header.frame_id == 'odom' and t.child_frame_id == 'base_link')

    node.create_subscription(TFMessage, '/tf', on_tf, 100)
    with tempfile.TemporaryFile(mode='w+') as log:
        process = subprocess.Popen([
            'ros2', 'launch', 'limo_bringup', 'limo_start.launch.py',
            'odometry:=' + profile, 'start_lidar:=false',
            'port_name:=' + os.ttyname(slave), 'odometry_config:=' + str(REGISTRY),
        ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.05)
                if (node.count_publishers('/imu') == 1
                        and node.count_publishers('/odom') == 1):
                    break
                assert process.poll() is None, 'launch exited before discovery'
            assert node.count_publishers('/imu') == 1
            assert node.count_publishers('/odom') == 1
            duration = 5.0 if profile == 'ekf' else 3.0
            started, index, next_frame = time.monotonic(), 0, time.monotonic()
            while time.monotonic() - started < duration:
                if time.monotonic() >= next_frame:
                    # Raw test crosses +180/-180 in tiny increments. EKF receives
                    # contradictory raw orientation/angular velocity to detect double fusion.
                    yaw_deg = ((179.0 + 0.05 * index + 180) % 360) - 180
                    if profile == 'ekf':
                        yaw_deg = 110.0 if index % 2 else -70.0
                    data = packet(0x322, (0, 0, round(math.degrees(0.25) * 100), 0))
                    data += packet(0x323, (round(yaw_deg * 100), 0, 0, 0))
                    data += packet(0x221, (500, -750, 0, 0))
                    os.write(master, data)
                    index += 1
                    next_frame += 0.02
                rclpy.spin_once(node, timeout_sec=0.002)
                try:
                    os.read(master, 4096)  # drain driver's virtual enable-command frame
                except BlockingIOError:
                    pass
            assert len(output) > 70
            assert len(imus) > 70
            assert len(odom_transforms) > 70
            # Foxy Python callbacks do not expose publisher GIDs. Verify the
            # enabled TF authorities via their actual runtime parameters instead.
            authorities = [('limo_base', 'pub_odom_tf', profile == 'raw')]
            if profile == 'ekf':
                authorities.append(('local_ekf', 'publish_tf', True))
            for owner, parameter, expected in authorities:
                client = node.create_client(GetParameters, '/' + owner + '/get_parameters')
                assert client.wait_for_service(timeout_sec=3)
                request = GetParameters.Request(names=[parameter])
                future = client.call_async(request)
                rclpy.spin_until_future_complete(node, future, timeout_sec=3)
                assert future.result().values[0].bool_value is expected
            assert output[-1].header.frame_id == 'odom'
            assert output[-1].child_frame_id == 'base_link'
            for msg in output:
                values = [msg.pose.pose.position.x, msg.pose.pose.position.y, yaw_of(msg)]
                assert all(math.isfinite(value) for value in values)
            source = raw[-1] if profile == 'ekf' else output[-1]
            assert source.twist.covariance[0] == pytest.approx(0.0025)
            assert imus[-1].angular_velocity_covariance[8] == pytest.approx(0.0004)
            if profile == 'ekf':
                assert len(raw) > 70
                assert node.count_publishers('/odom/raw') == 1
                assert output[-1].twist.twist.angular.z == pytest.approx(0.25, abs=0.03)
                assert 0.95 < yaw_of(output[-1]) < 1.5
                assert output[-1].pose.pose.position.x > 1.4
                assert output[-1].pose.pose.position.y > 0.8
                assert output[-1].pose.covariance[0] > 0
            else:
                expected = math.radians(0.05 * (index - 1))
                assert yaw_of(output[-1]) == pytest.approx(expected, abs=0.03)
                assert node.count_publishers('/odom/raw') == 0
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
