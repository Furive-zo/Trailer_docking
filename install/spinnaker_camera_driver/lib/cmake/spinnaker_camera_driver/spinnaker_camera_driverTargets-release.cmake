#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "spinnaker_camera_driver::camera_driver" for configuration "Release"
set_property(TARGET spinnaker_camera_driver::camera_driver APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(spinnaker_camera_driver::camera_driver PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libcamera_driver.so"
  IMPORTED_SONAME_RELEASE "libcamera_driver.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS spinnaker_camera_driver::camera_driver )
list(APPEND _IMPORT_CHECK_FILES_FOR_spinnaker_camera_driver::camera_driver "${_IMPORT_PREFIX}/lib/libcamera_driver.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
