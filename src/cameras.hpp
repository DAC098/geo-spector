#pragma once

#include <string>
#include <vector>

struct CameraInfo {
    std::string serial;
    int id;
};

std::vector<CameraInfo> load_camera_data(const std::string& file);
