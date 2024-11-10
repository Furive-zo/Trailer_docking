import rclpy
import rclpy.node
from rclpy.qos import qos_profile_sensor_data
from cv_bridge import CvBridge, CvBridgeError
import numpy as np
import cv2
from scipy.spatial.transform import Rotation as R
from sensor_msgs.msg import CameraInfo, Image
from geometry_msgs.msg import PoseArray, Pose
from ros2_aruco_interfaces.msg import ArucoMarkers
from rcl_interfaces.msg import ParameterDescriptor, ParameterType


class ArucoNode(rclpy.node.Node):
    def __init__(self):
        super().__init__("aruco_node")

        # 파라미터 선언 및 읽기
        self.declare_parameter("marker_size", 0.0625, ParameterDescriptor(
            type=ParameterType.PARAMETER_DOUBLE, description="마커의 크기 (미터 단위)."
        ))
        self.declare_parameter("aruco_dictionary_id", "DICT_5X5_250", ParameterDescriptor(
            type=ParameterType.PARAMETER_STRING, description="마커 생성을 위해 사용된 아루코 사전."
        ))
        self.declare_parameter("image_topic", "/camera/image_raw", ParameterDescriptor(
            type=ParameterType.PARAMETER_STRING, description="구독할 이미지 토픽."
        ))
        self.declare_parameter("camera_info_topic", "/camera/camera_info", ParameterDescriptor(
            type=ParameterType.PARAMETER_STRING, description="구독할 카메라 정보 토픽."
        ))
        self.declare_parameter("camera_frame", "", ParameterDescriptor(
            type=ParameterType.PARAMETER_STRING, description="사용할 카메라 프레임."
        ))

        self.marker_size = self.get_parameter("marker_size").get_parameter_value().double_value
        dictionary_id_name = self.get_parameter("aruco_dictionary_id").get_parameter_value().string_value
        image_topic = self.get_parameter("image_topic").get_parameter_value().string_value
        info_topic = self.get_parameter("camera_info_topic").get_parameter_value().string_value
        self.camera_frame = self.get_parameter("camera_frame").get_parameter_value().string_value

        # 유효한 사전 ID인지 확인
        try:
            dictionary_id = cv2.aruco.__getattribute__(dictionary_id_name)
            if not isinstance(dictionary_id, int):
                raise AttributeError
        except AttributeError:
            self.get_logger().error(f"잘못된 아루코 사전 ID: {dictionary_id_name}")
            options = "\n".join([s for s in dir(cv2.aruco) if s.startswith("DICT")])
            self.get_logger().error(f"유효한 옵션: {options}")
            return

        # 구독 설정
        self.info_sub = self.create_subscription(CameraInfo, info_topic, self.info_callback, qos_profile_sensor_data)
        self.create_subscription(Image, image_topic, self.image_callback, qos_profile_sensor_data)

        # 퍼블리셔 설정 (PoseArray, ArucoMarkers, Aruco 이미지 퍼블리셔 추가)
        self.poses_pub = self.create_publisher(PoseArray, "aruco_poses", 10)
        self.markers_pub = self.create_publisher(ArucoMarkers, "aruco_markers", 10)
        self.image_pub = self.create_publisher(Image, "aruco_image", 10)

        # 카메라 파라미터 초기화
        self.info_msg = None
        self.intrinsic_mat = None
        self.distortion = None

        # 아루코 사전 및 파라미터 설정
        self.aruco_dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.aruco_parameters = cv2.aruco.DetectorParameters()
        self.bridge = CvBridge()

    def info_callback(self, info_msg):
        self.info_msg = info_msg
        self.intrinsic_mat = np.reshape(np.array(self.info_msg.k), (3, 3))
        self.distortion = np.array(self.info_msg.d)
        self.destroy_subscription(self.info_sub)  # 카메라 정보는 한 번만 수신

    def image_callback(self, img_msg):
        if self.info_msg is None:
            self.get_logger().warn("카메라 정보가 수신되지 않았습니다!")
            return

        try:
            # ROS 이미지를 OpenCV 이미지로 변환
            cv_image = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"이미지 변환 실패: {e}")
            return

        markers = ArucoMarkers()
        pose_array = PoseArray()
        markers.header.frame_id = self.camera_frame or self.info_msg.header.frame_id
        pose_array.header.frame_id = markers.header.frame_id
        markers.header.stamp = img_msg.header.stamp
        pose_array.header.stamp = img_msg.header.stamp

        # 아루코 마커 탐지
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        corners, marker_ids, rejected = cv2.aruco.detectMarkers(
            gray, self.aruco_dictionary, parameters=self.aruco_parameters
        )

        if marker_ids is not None:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, self.marker_size, self.intrinsic_mat, self.distortion
            )
            for i, marker_id in enumerate(marker_ids):
                pose = Pose()
                pose.position.x = tvecs[i][0][0]
                pose.position.y = tvecs[i][0][1]
                pose.position.z = tvecs[i][0][2]

                # 회전 행렬에서 쿼터니언으로 변환
                rot_matrix = cv2.Rodrigues(rvecs[i][0])[0]
                rotation = R.from_matrix(rot_matrix)
                quat = rotation.as_quat()

                pose.orientation.x = quat[0]
                pose.orientation.y = quat[1]
                pose.orientation.z = quat[2]
                pose.orientation.w = quat[3]

                pose_array.poses.append(pose)
                markers.poses.append(pose)
                markers.marker_ids.append(marker_id[0])

                # 이미지에 마커와 ID, 자세 축 표시
                cv2.aruco.drawDetectedMarkers(cv_image, corners, marker_id)
                cv2.drawFrameAxes(cv_image, self.intrinsic_mat, self.distortion, rvecs[i], tvecs[i], 0.03, 5)

            # 퍼블리시
            self.poses_pub.publish(pose_array)
            self.markers_pub.publish(markers)

        try:
            # OpenCV 이미지를 ROS 메시지로 변환하여 퍼블리시
            aruco_image_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding="bgr8")
            aruco_image_msg.header = img_msg.header
            self.image_pub.publish(aruco_image_msg)
        except CvBridgeError as e:
            self.get_logger().error(f"이미지 변환 실패: {e}")


def main():
    rclpy.init()
    node = ArucoNode()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
