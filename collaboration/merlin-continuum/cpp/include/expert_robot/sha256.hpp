#pragma once

#include <string>
#include <string_view>

namespace expert_robot {

[[nodiscard]] std::string sha256_hex(std::string_view input);

} // namespace expert_robot
