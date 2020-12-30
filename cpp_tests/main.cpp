#include <iostream>
#include "hero_workshop_core.h"

int main() {
    auto response = protobuf_entry_point(::rust::Vec<uint8_t>());
    std::cout << "Got core response: " << std::string((const char*) response.data(), response.size()) << std::endl;
    return 0;
}