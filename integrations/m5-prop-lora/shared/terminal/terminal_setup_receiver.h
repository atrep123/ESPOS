#pragma once

#include <cstdint>
#include <string>

#include "terminal_setup_apply.h"
#include "terminal_setup_link.h"

namespace terminal_setup_receiver {

constexpr const char* SETUP_OK = terminal_setup_link::RESPONSE_OK;
constexpr const char* SETUP_ERR = terminal_setup_link::RESPONSE_ERR;

enum class Reply {
    None,
    SetupOk,
    SetupErr,
};

struct ReplyResult {
    Reply kind = Reply::None;
    std::uint32_t requestId = 0;
};

struct ReceiverCallbacks {
    void* ctx = nullptr;
    bool (*commitSetup)(void* ctx, const terminal_setup_apply::AppliedSetup& setup) = nullptr;
    bool (*previewSimFire)(void* ctx) = nullptr;

    constexpr ReceiverCallbacks() = default;
    constexpr ReceiverCallbacks(
        void* context,
        bool (*commit)(void* ctx, const terminal_setup_apply::AppliedSetup& setup),
        bool (*preview)(void* ctx))
        : ctx(context), commitSetup(commit), previewSimFire(preview) {}
};

inline ReplyResult handleLineResult(const char* line, const ReceiverCallbacks& callbacks) {
    const terminal_setup_link::ParseResult parsed = terminal_setup_link::parseLine(line);
    ReplyResult result;
    result.requestId = parsed.setup.requestId;

    if (parsed.kind == terminal_setup_link::CommandKind::Empty) {
        result.kind = Reply::None;
        return result;
    }
    if (parsed.kind == terminal_setup_link::CommandKind::Setup) {
        if (callbacks.commitSetup == nullptr) {
            result.kind = Reply::SetupErr;
            return result;
        }
        const terminal_setup_apply::AppliedSetup setup =
            terminal_setup_apply::applySetupCommand(parsed.setup);
        result.kind =
            callbacks.commitSetup(callbacks.ctx, setup) ? Reply::SetupOk : Reply::SetupErr;
        return result;
    }
    if (parsed.kind == terminal_setup_link::CommandKind::SimFire) {
        if (callbacks.previewSimFire == nullptr) {
            result.kind = Reply::SetupErr;
            return result;
        }
        result.kind =
            callbacks.previewSimFire(callbacks.ctx) ? Reply::SetupOk : Reply::SetupErr;
        return result;
    }
    result.kind = Reply::SetupErr;
    return result;
}

inline Reply handleLine(const char* line, const ReceiverCallbacks& callbacks) {
    return handleLineResult(line, callbacks).kind;
}

inline const char* replyLine(Reply reply) {
    switch (reply) {
        case Reply::SetupOk:
            return SETUP_OK;
        case Reply::SetupErr:
            return SETUP_ERR;
        case Reply::None:
            return "";
    }
    return "";
}

inline std::string replyLine(const ReplyResult& result) {
    return terminal_setup_link::formatResponseLine(replyLine(result.kind), result.requestId);
}

}  // namespace terminal_setup_receiver
