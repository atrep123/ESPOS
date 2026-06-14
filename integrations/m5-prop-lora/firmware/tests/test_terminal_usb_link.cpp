#include "../sticks3-terminal/src/terminal_usb_link.h"

#include <iostream>

namespace {

using terminal_usb_link::UploadEvent;
using terminal_usb_link::RequestKind;
using terminal_usb_link::UsbSetupLink;

UploadEvent feedLine(UsbSetupLink& link, const char* line) {
    UploadEvent last = UploadEvent::None;
    for (const char* p = line; *p != '\0'; ++p) {
        const UploadEvent event = link.push(*p);
        if (event != UploadEvent::None) {
            last = event;
        }
    }
    const UploadEvent newline = link.push('\n');
    return newline == UploadEvent::None ? last : newline;
}

bool acceptsMatchingRequestScopedRepliesOnly() {
    UsbSetupLink link(16);
    const std::uint32_t firstRequestId = link.beginUpload(100, 1500);
    if (firstRequestId != 1 || link.requestId() != 1 || link.requestKind() != RequestKind::Upload) {
        return false;
    }
    if (feedLine(link, "SETUP_OKAY") != UploadEvent::None) {
        return false;
    }
    if (feedLine(link, "SETUP_OK extra") != UploadEvent::None) {
        return false;
    }
    if (feedLine(link, " SETUP_OK ") != UploadEvent::None) {
        return false;
    }
    if (feedLine(link, "SETUP_OK 999") != UploadEvent::None) {
        return false;
    }
    if (feedLine(link, " SETUP_OK 1 ") != UploadEvent::Accepted) {
        return false;
    }

    link.finishUpload();
    const std::uint32_t secondRequestId = link.beginUpload(200, 1500);
    return secondRequestId == 2 &&
           feedLine(link, "\tSETUP_ERR 1\t") == UploadEvent::None &&
           feedLine(link, "\tSETUP_ERR 2\t") == UploadEvent::Rejected;
}

bool simFireRequestAcceptsScopedRepliesOnly() {
    UsbSetupLink link(16);
    const std::uint32_t requestId = link.beginSimFire(100, 1500);
    return requestId == 1 &&
           link.requestKind() == RequestKind::SimFire &&
           feedLine(link, "SETUP_OK") == UploadEvent::None &&
           feedLine(link, "SETUP_ERR 2") == UploadEvent::None &&
           feedLine(link, "SETUP_ERR 1") == UploadEvent::Rejected;
}

bool ignoresNoisyUsbLinesWhileUploadIsPending() {
    UsbSetupLink link(32);
    const std::uint32_t requestId = link.beginUpload(100, 1500);
    const char* noise[] = {"OK TX", "ERR DUTY", "ACK 1234", "BOOT READY", "[hb] ok"};
    for (const char* line : noise) {
        if (feedLine(link, line) != UploadEvent::None) {
            return false;
        }
    }
    return requestId == 1 &&
           feedLine(link, "SETUP_OK") == UploadEvent::None &&
           feedLine(link, "SETUP_OK 1") == UploadEvent::Accepted;
}

bool ignoresUnscopedOverflowErrorWhileUploadIsPending() {
    UsbSetupLink link(32);
    const std::uint32_t requestId = link.beginUpload(100, 1500);
    return requestId == 1 &&
           feedLine(link, "SETUP_ERR 0") == UploadEvent::None &&
           feedLine(link, "SETUP_OK 1") == UploadEvent::Accepted;
}

bool rejectsOnTimeoutAfterGraceWindow() {
    UsbSetupLink link(16);
    link.beginUpload(100, 1500);
    if (link.pollTimeout(1600) != UploadEvent::None) {
        return false;
    }
    return link.pollTimeout(1601) == UploadEvent::Rejected;
}

bool rejectsOverlongLines() {
    UsbSetupLink link(4);
    link.beginUpload(0, 1500);
    return link.push('A') == UploadEvent::None &&
           link.push('B') == UploadEvent::None &&
           link.push('C') == UploadEvent::None &&
           link.push('D') == UploadEvent::None &&
           link.push('E') == UploadEvent::Rejected;
}

bool ignoresInputWhileIdle() {
    UsbSetupLink link(8);
    return feedLine(link, "SETUP_OK") == UploadEvent::None &&
           feedLine(link, "SETUP_OK 1") == UploadEvent::None &&
           link.pollTimeout(9999) == UploadEvent::None;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("accepts matching request-scoped replies only", acceptsMatchingRequestScopedRepliesOnly) ? 0 : 1;
    failures += runCase("sim-fire request accepts scoped replies only", simFireRequestAcceptsScopedRepliesOnly) ? 0 : 1;
    failures += runCase("ignores noisy USB lines while upload is pending", ignoresNoisyUsbLinesWhileUploadIsPending) ? 0 : 1;
    failures += runCase("ignores unscoped overflow error while upload is pending", ignoresUnscopedOverflowErrorWhileUploadIsPending) ? 0 : 1;
    failures += runCase("rejects on timeout after grace window", rejectsOnTimeoutAfterGraceWindow) ? 0 : 1;
    failures += runCase("rejects overlong lines", rejectsOverlongLines) ? 0 : 1;
    failures += runCase("ignores input while idle", ignoresInputWhileIdle) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
