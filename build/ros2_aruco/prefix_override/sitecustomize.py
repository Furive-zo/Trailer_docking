import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/furive-zo/Workspace/study/trailer-docking/install/ros2_aruco'
