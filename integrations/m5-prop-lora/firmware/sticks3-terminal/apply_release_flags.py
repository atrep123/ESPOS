import os

Import("env")

flags = os.environ.get("PROP_RELEASE_BUILD_FLAGS", "").split()
if flags:
    env.Append(BUILD_FLAGS=flags)
