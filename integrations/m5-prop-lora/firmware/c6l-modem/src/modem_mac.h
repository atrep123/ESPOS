// Tiny dependency-free header holding the MAC length constant shared by both
// modem_core.h (PeerTracker) and modem_hal.h (IEspNow::RxItem). It exists to break
// the otherwise-circular include between those two headers: modem_hal.h needs
// MAC_LEN, and modem_core.h needs the HAL interfaces -- if modem_hal.h pulled in
// modem_core.h for MAC_LEN and was included first, the cycle would leave the HAL
// interfaces undeclared when class Modem references them. Both headers include this
// instead. (Flagged LOW by the Codex council review, 2026-05-29.)
#pragma once

#include <cstddef>

namespace modem_core {

constexpr std::size_t MAC_LEN = 6;  // Ethernet MAC length; matches ESP_NOW_ETH_ALEN

}  // namespace modem_core
