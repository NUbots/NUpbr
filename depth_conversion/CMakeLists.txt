CMAKE_MINIMUM_REQUIRED(VERSION 3.2)
PROJECT (depth_conversion LANGUAGES CXX)

FIND_PACKAGE(PkgConfig)
PKG_CHECK_MODULES(OpenEXR REQUIRED OpenEXR)

LINK_DIRECTORIES(${OpenEXR_LIBRARY_DIRS})

ADD_EXECUTABLE (depth_conversion depth_conversion.cpp)
TARGET_COMPILE_FEATURES(depth_conversion PRIVATE cxx_std_11)
TARGET_INCLUDE_DIRECTORIES(depth_conversion PRIVATE ${OpenEXR_INCLUDE_DIRS})
TARGET_LINK_LIBRARIES(depth_conversion PRIVATE ${OpenEXR_LIBRARIES})
TARGET_COMPILE_OPTIONS(depth_conversion PRIVATE ${OpenEXR_CFLAGS_OTHER})
SET_TARGET_PROPERTIES(depth_conversion PROPERTIES LINK_FLAGS ${OpenEXR_LDFLAGS})
