#pragma once

#include <stdint.h>

#ifndef HAVE_ICONS
#define HAVE_ICONS 0
#endif

typedef struct {
    const char* name;
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
    const uint8_t* data;
} icon_t;

extern const icon_t mi_arrow_back_16px;
extern const icon_t mi_arrow_forward_16px;
extern const icon_t mi_audio_file_16px;
extern const icon_t mi_battery_charging_full_16px;
extern const icon_t mi_battery_full_16px;
extern const icon_t mi_bluetooth_16px;
extern const icon_t mi_brightness_high_16px;
extern const icon_t mi_check_16px;
extern const icon_t mi_check_circle_16px;
extern const icon_t mi_close_16px;
extern const icon_t mi_cloud_16px;
extern const icon_t mi_cloud_download_16px;
extern const icon_t mi_cloud_upload_16px;
extern const icon_t mi_code_16px;
extern const icon_t mi_content_copy_16px;
extern const icon_t mi_content_paste_16px;
extern const icon_t mi_delete_16px;
extern const icon_t mi_description_16px;
extern const icon_t mi_drive_file_move_16px;
extern const icon_t mi_drive_file_rename_outline_16px;
extern const icon_t mi_error_16px;
extern const icon_t mi_file_upload_16px;
extern const icon_t mi_folder_16px;
extern const icon_t mi_folder_open_16px;
extern const icon_t mi_help_16px;
extern const icon_t mi_home_16px;
extern const icon_t mi_html_16px;
extern const icon_t mi_image_16px;
extern const icon_t mi_info_16px;
extern const icon_t mi_integration_instructions_16px;
extern const icon_t mi_javascript_16px;
extern const icon_t mi_lock_16px;
extern const icon_t mi_lock_open_16px;
extern const icon_t mi_menu_16px;
extern const icon_t mi_more_horiz_16px;
extern const icon_t mi_more_vert_16px;
extern const icon_t mi_network_wifi_16px;
extern const icon_t mi_pause_16px;
extern const icon_t mi_picture_as_pdf_16px;
extern const icon_t mi_play_arrow_16px;
extern const icon_t mi_power_settings_new_16px;
extern const icon_t mi_save_16px;
extern const icon_t mi_save_alt_16px;
extern const icon_t mi_sd_storage_16px;
extern const icon_t mi_search_16px;
extern const icon_t mi_settings_16px;
extern const icon_t mi_stop_16px;
extern const icon_t mi_text_snippet_16px;
extern const icon_t mi_upload_file_16px;
extern const icon_t mi_video_file_16px;
extern const icon_t mi_volume_off_16px;
extern const icon_t mi_volume_up_16px;
extern const icon_t mi_warning_16px;
