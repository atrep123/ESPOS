
# Hal
file(GLOB_RECURSE HAL_SRCS
    hal/*.c
    hal/*.cpp
)
set(HAL_INCS
    hal/
)

# App
file(GLOB_RECURSE APP_SRCS
    apps/*.c
    apps/*.cpp
)
list(APPEND APP_SRCS
    apps/app_prop_tx/gui/gui_prop_tx.cpp
    apps/app_prop_tx/chain_key_poller.cpp
)
list(REMOVE_DUPLICATES APP_SRCS)
set(APP_INCS
    apps/
)



idf_component_register(SRCS "main.cpp" ${HAL_SRCS} ${APP_SRCS}
                    INCLUDE_DIRS "." ${HAL_INCS} ${APP_INCS} "../../../shared/protocol")
