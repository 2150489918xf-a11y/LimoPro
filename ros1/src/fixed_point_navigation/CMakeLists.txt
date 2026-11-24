cmake_minimum_required(VERSION 3.0.2)
project(multipoint_navigation)


find_package(catkin REQUIRED COMPONENTS
  actionlib
  move_base_msgs
  roscpp
  rospy
)

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES set_nav_point
#  CATKIN_DEPENDS actionlib move_base_msgs roscpp
#  DEPENDS system_lib
)

include_directories(
# include
  ${catkin_INCLUDE_DIRS}
)


 add_executable(multipoint_navigation src/multipoint_navigation.cpp)

 target_link_libraries(multipoint_navigation
   ${catkin_LIBRARIES}
 )

