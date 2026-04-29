#include <exception>
#include <iostream>
#include <utility>
#include <filesystem>
#include <memory>
#include <sstream>
#include <tuple>
#include <vector>

#include "usb.hpp"

//https://stackoverflow.com/questions/478898/how-do-i-execute-a-command-and-get-the-output-of-the-command-within-c-using-po
std::string exec(const char* cmd) {
    std::string rtn;
    std::array<char, 128> buffer;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);

    if (!pipe) {
        throw std::runtime_error("popen() failed");
    }

    while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr) {
        rtn += buffer.data();
    }

    return rtn;
}

std::string check_if_video_capture(const std::filesystem::path& path) {
    std::stringstream ss;
    ss << "udevadm info --query=all " << path;

    auto query = exec(ss.str().c_str());

    std::string::size_type start = 0;
    std::string::size_type end = query.find("\n");

    bool is_capture = false;
    std::string serial_short;

    while (end != std::string::npos) {
        auto substr = query.substr(start, end - start);

        if (!substr.empty()) {
            if (substr[0] == 'E') {
                auto data = substr.substr(3);
                auto delim = data.find("=");

                if (delim != std::string::npos) {
                    auto key = data.substr(0, delim);
                    auto value = data.substr(delim + 1);

                    if (key == "ID_V4L_CAPABILITIES" && value.find(":capture:") != std::string::npos) {
                        // found a camera with capture capabilities
                        is_capture = true;
                    } else if (key == "ID_SERIAL_SHORT") {
                        serial_short = value;
                    }
                } else {
                    //std::cout << "not key=value \"" << substr << "\"\n";
                }
            } else {
                //std::cout << "not E: \"" << substr << "\"\n";
            }
        }

        start = end + 1;
        end = query.find("\n", end + 1);
    }

    if (is_capture) {
        //std::cout << "found video capture device: " << video_id << " " << serial_short << "\n";
        return serial_short;
    } else {
        return "";
    }
}

std::vector<std::tuple<int, std::string>> find_capture_devices() {
    std::vector<std::tuple<int, std::string>> rtn;

    for (const auto& entry : std::filesystem::directory_iterator("/dev")) {
        auto filename = entry.path().filename().string();

        if (filename.empty()) {
            continue;
        }

        auto found = filename.find("video");

        if (found == std::string::npos || found != 0) {
            continue;
        }

        int video_id = 0;

        try {
            video_id = std::stoi(filename.substr(5));
        } catch (std::invalid_argument const& _err) {
            // invalid string
            continue;
        } catch (std::out_of_range const& _err) {
            // too large of a number
            continue;
        }

        auto serial_short = check_if_video_capture(entry.path());

        if (!serial_short.empty()) {
            rtn.push_back({video_id, serial_short});
        }
    }

    return rtn;
}
