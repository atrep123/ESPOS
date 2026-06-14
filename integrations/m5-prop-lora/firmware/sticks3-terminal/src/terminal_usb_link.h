#pragma once

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <string>

namespace terminal_usb_link {

constexpr const char* SETUP_OK = "SETUP_OK";
constexpr const char* SETUP_ERR = "SETUP_ERR";
constexpr std::uint32_t REQUEST_ID_MAX = 9999;

enum class UploadEvent {
    None,
    Accepted,
    Rejected,
};

enum class RequestKind {
    None,
    Upload,
    SimFire,
};

inline std::string trimAscii(const std::string& input) {
    std::size_t begin = 0;
    while (begin < input.size() && (input[begin] == ' ' || input[begin] == '\t')) {
        ++begin;
    }
    std::size_t end = input.size();
    while (end > begin && (input[end - 1] == ' ' || input[end - 1] == '\t')) {
        --end;
    }
    return input.substr(begin, end - begin);
}

class UsbSetupLink {
   public:
    explicit UsbSetupLink(std::size_t maxLineLength) : maxLineLength_(maxLineLength) {}

    std::uint32_t beginUpload(std::uint32_t nowMs, std::uint32_t timeoutMs) {
        return beginRequest(RequestKind::Upload, nowMs, timeoutMs);
    }

    std::uint32_t beginSimFire(std::uint32_t nowMs, std::uint32_t timeoutMs) {
        return beginRequest(RequestKind::SimFire, nowMs, timeoutMs);
    }

    std::uint32_t beginRequest(RequestKind kind, std::uint32_t nowMs, std::uint32_t timeoutMs) {
        nextRequestId_ = nextRequestId_ >= REQUEST_ID_MAX ? 1U : nextRequestId_ + 1U;
        requestId_ = nextRequestId_;
        requestKind_ = kind;
        inFlight_ = true;
        startedMs_ = nowMs;
        timeoutMs_ = timeoutMs;
        line_.clear();
        overflow_ = false;
        return requestId_;
    }

    void finishUpload() {
        inFlight_ = false;
        requestKind_ = RequestKind::None;
        line_.clear();
        overflow_ = false;
    }

    bool inFlight() const {
        return inFlight_;
    }

    std::uint32_t requestId() const {
        return requestId_;
    }

    RequestKind requestKind() const {
        return requestKind_;
    }

    UploadEvent push(char ch) {
        if (!inFlight_) {
            return UploadEvent::None;
        }
        if (ch == '\r') {
            return UploadEvent::None;
        }
        if (ch == '\n') {
            if (overflow_) {
                line_.clear();
                overflow_ = false;
                return UploadEvent::Rejected;
            }
            const UploadEvent event = parseLine(line_);
            line_.clear();
            return event;
        }
        if (overflow_) {
            return UploadEvent::None;
        }
        if (line_.size() >= maxLineLength_) {
            line_.clear();
            overflow_ = true;
            return UploadEvent::Rejected;
        }
        line_.push_back(ch);
        return UploadEvent::None;
    }

    UploadEvent pollTimeout(std::uint32_t nowMs) const {
        if (!inFlight_) {
            return UploadEvent::None;
        }
        return nowMs - startedMs_ > timeoutMs_ ? UploadEvent::Rejected : UploadEvent::None;
    }

   private:
    UploadEvent parseLine(const std::string& line) const {
        const std::string trimmed = trimAscii(line);
        if (matchesReply(trimmed, SETUP_OK)) {
            return UploadEvent::Accepted;
        }
        if (matchesReply(trimmed, SETUP_ERR)) {
            return UploadEvent::Rejected;
        }
        return UploadEvent::None;
    }

    bool matchesReply(const std::string& trimmed, const char* token) const {
        const std::string prefix(token);
        if (requestId_ == 0U || trimmed.size() <= prefix.size() ||
            trimmed.compare(0, prefix.size(), prefix) != 0) {
            return false;
        }
        std::size_t pos = prefix.size();
        if (trimmed[pos] != ' ' && trimmed[pos] != '\t') {
            return false;
        }
        while (pos < trimmed.size() && (trimmed[pos] == ' ' || trimmed[pos] == '\t')) {
            ++pos;
        }
        if (pos >= trimmed.size() ||
            std::isdigit(static_cast<unsigned char>(trimmed[pos])) == 0) {
            return false;
        }

        std::uint32_t parsed = 0;
        while (pos < trimmed.size() &&
               std::isdigit(static_cast<unsigned char>(trimmed[pos])) != 0) {
            parsed = parsed * 10U + static_cast<std::uint32_t>(trimmed[pos] - '0');
            if (parsed > REQUEST_ID_MAX) {
                return false;
            }
            ++pos;
        }
        while (pos < trimmed.size() && (trimmed[pos] == ' ' || trimmed[pos] == '\t')) {
            ++pos;
        }
        return pos == trimmed.size() && parsed == requestId_;
    }

    std::size_t maxLineLength_ = 0;
    std::uint32_t nextRequestId_ = 0;
    std::uint32_t requestId_ = 0;
    std::uint32_t startedMs_ = 0;
    std::uint32_t timeoutMs_ = 0;
    RequestKind requestKind_ = RequestKind::None;
    bool inFlight_ = false;
    bool overflow_ = false;
    std::string line_;
};

}  // namespace terminal_usb_link
