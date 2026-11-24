#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import time
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib

if __name__ == '__main__':
    # 初始化ROS节点
    rospy.init_node('simple_navigation_goals')

    # 创建SimpleActionClient实例
    ac = actionlib.SimpleActionClient('move_base', MoveBaseAction)

    # 等待move_base服务器启动
    rospy.loginfo("Waiting for the move_base action server to come up")
    ac.wait_for_server(rospy.Duration(5.0))

    # 定义第一个目标点的位置
    goal1 = MoveBaseGoal()
    goal1.target_pose.header.frame_id = "map"  # 设置坐标系为地图坐标系
    goal1.target_pose.header.stamp = rospy.Time.now()  # 设置时间戳为当前时间

    goal1.target_pose.pose.position.x = 1.0  # 设置目标点的x坐标
    goal1.target_pose.pose.position.y = 2.0  # 设置目标点的y坐标
    goal1.target_pose.pose.orientation.w = 1.0  # 设置目标点的朝向为正方向。

    # 发送第一个目标点
    rospy.loginfo("Sending goal 1")
    ac.send_goal(goal1)

    # 等待机器人到达第一个目标点
    ac.wait_for_result()

    # 输出机器人到达第一个目标点的结果
    if ac.get_state() == actionlib.GoalStatus.SUCCEEDED:
        rospy.loginfo("Robot reached goal 1")
    else:
        rospy.loginfo("The robot failed to reach goal 1")
        
    time.sleep(4)

    # 定义第二个目标点的位置
    goal2 = MoveBaseGoal()
    goal2.target_pose.header.frame_id = "map"  # 设置坐标系为地图坐标系
    goal2.target_pose.header.stamp = rospy.Time.now()  # 设置时间戳为当前时间

    goal2.target_pose.pose.position.x = 3.0  # 设置目标点的x坐标
    goal2.target_pose.pose.position.y = 4.0  # 设置目标点的y坐标
    goal2.target_pose.pose.orientation.w = 1.0  # 设置目标点的朝向为正方向。

    # 发送第二个目标点
    rospy.loginfo("Sending goal 2")
    ac.send_goal(goal2)

    # 等待机器人到达第二个目标点
    ac.wait_for_result()

    # 输出机器人到达第二个目标点的结果
    if ac.get_state() == actionlib.GoalStatus.SUCCEEDED:
        rospy.loginfo("Robot reached goal 2")
    else:
        rospy.loginfo("The robot failed to reach goal 2")
