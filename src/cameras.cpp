#include <exception>
#include <iostream>
#include <utility>
#include <filesystem>
#include <memory>
#include <sstream>
#include <tuple>
#include <fstream>
#include <unordered_map>

#include <json.hpp>

#include "cameras.hpp"
#include "usb.hpp"

std::vector<CameraInfo> load_camera_data(const std::string& file) {
    std::ifstream json_file = std::ifstream(file);

    if (!json_file.is_open()) {
        throw std::runtime_error("failed to open json file");
    }

    nlohmann::json data = nlohmann::json::parse(json_file);

    if (!data.is_object()) {
        throw std::runtime_error("invalid json structure");
    }

    std::unordered_map<std::string, nlohmann::json> dict;
    data.get_to(dict);

    std::unordered_map<std::string, int> serial_index;
    auto capture_devices = find_capture_devices();
    std::vector<CameraInfo> rtn;

    if (capture_devices.empty()) {
        return rtn;
    } else {
        for (const auto& device : capture_devices) {
            serial_index.insert({std::get<1>(device), std::get<0>(device)});
        }
    }

    for (const auto& [name, info] : dict) {
        //std::cout << "checking: \"" << name << "\"\n";

        if (!info.is_object()) {
            //std::cout << "key: \"" << name << "\" is not an object\n";
            continue;
        }

        std::string serial;

        //std::cout << "checking serial\n";

        if (info.contains("serial")) {
            info["serial"].get_to(serial);
        }

        if (serial.empty()) {
            //std::cout << "missing usb serial id \"" << name << "\"\n";
        } else {
            auto found = serial_index.find(serial);

            if (found == serial_index.end()) {
                //std::cout << "camera device not found: \"" << name << "\"\n";
            } else {
                //std::cout << "camer device found: \"" << name << "\" id: " << found->second << "\n";

                CameraInfo camera;
                camera.serial = serial;
                camera.id = found->second;

                rtn.push_back(camera);
            }
        }
    }

    return rtn;
}
