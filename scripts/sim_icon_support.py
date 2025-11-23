"""
Icon support for simulator - maps Material Icon symbols to ASCII/Unicode
"""
from typing import Dict

# Icon symbol -> ASCII/Unicode mapping for simulator rendering
# Generated from ui_icons.MATERIAL_ICONS
ICON_ASCII_MAP: Dict[str, str] = {
    # Navigation & UI Control
    "mi_arrow_back_24px": "←",
    "mi_arrow_forward_24px": "→",
    "mi_home_24px": "⌂",
    "mi_search_24px": "🔍",
    "mi_settings_24px": "⚙",
    "mi_menu_24px": "☰",
    "mi_more_vert_24px": "⋮",
    "mi_more_horiz_24px": "⋯",
    "mi_close_24px": "✕",
    "mi_check_24px": "✓",
    "mi_check_circle_24px": "✓",
    "mi_help_24px": "?",
    
    # File Operations
    "mi_folder_24px": "📁",
    "mi_folder_open_24px": "📂",
    "mi_description_24px": "📄",
    "mi_save_24px": "💾",
    "mi_save_alt_24px": "💾",
    "mi_delete_24px": "🗑",
    "mi_content_copy_24px": "📋",
    "mi_content_paste_24px": "📋",
    "mi_drive_file_move_24px": "📦",
    "mi_drive_file_rename_outline_24px": "✏",
    "mi_file_upload_24px": "📤",
    "mi_upload_file_24px": "⬆",
    "mi_cloud_24px": "☁",
    "mi_sd_storage_24px": "💳",
    
    # File Types / MIME
    "mi_text_snippet_24px": "📝",
    "mi_code_24px": "<>",
    "mi_html_24px": "H",
    "mi_javascript_24px": "JS",
    "mi_image_24px": "🖼",
    "mi_audio_file_24px": "🎵",
    "mi_video_file_24px": "🎬",
    "mi_picture_as_pdf_24px": "PDF",
    
    # Cloud & Network
    "mi_cloud_upload_24px": "☁⬆",
    "mi_cloud_download_24px": "☁⬇",
    "mi_network_wifi_24px": "📶",
    "mi_bluetooth_24px": "Ⓑ",
    "mi_integration_instructions_24px": "⚡",
    
    # Device Status
    "mi_battery_full_24px": "🔋",
    "mi_battery_charging_full_24px": "⚡",
    "mi_brightness_high_24px": "☀",
    "mi_volume_up_24px": "🔊",
    "mi_volume_off_24px": "🔇",
    "mi_power_settings_new_24px": "⏻",
    
    # Media Control
    "mi_play_arrow_24px": "▶",
    "mi_pause_24px": "⏸",
    "mi_stop_24px": "⏹",
    
    # Security & Alerts
    "mi_lock_24px": "🔒",
    "mi_lock_open_24px": "🔓",
    "mi_info_24px": "ℹ",
    "mi_warning_24px": "⚠",
    "mi_error_24px": "⛔",
}


def get_icon_ascii(symbol: str, fallback: str = "?") -> str:
    """
    Get ASCII/Unicode representation of an icon symbol.
    
    Args:
        symbol: Icon symbol name (e.g., "mi_home_24px")
        fallback: Character to return if symbol not found
    
    Returns:
        ASCII/Unicode character(s) representing the icon
    """
    return ICON_ASCII_MAP.get(symbol, fallback)


def icon_exists(symbol: str) -> bool:
    """Check if an icon symbol is recognized."""
    return symbol in ICON_ASCII_MAP
