"""
Material Icons mapping for ESP32OS UI Designer
Icon reference with categories and usage metadata
"""
from __future__ import annotations

from typing import List, Optional, TypedDict


class IconInfo(TypedDict):
    """Icon metadata"""
    name: str
    symbol: str
    category: str
    usage: str
    ascii: str
    size_16: str  # Symbol name for 16px variant
    size_24: str  # Symbol name for 24px variant


# Complete icon set with metadata
MATERIAL_ICONS: List[IconInfo] = [
    # Navigation & UI Control (12 icons)
    {"name": "Back", "symbol": "mi_arrow_back_24px", "category": "navigation", "usage": "Navigate back, return to previous screen", "ascii": "←", "size_16": "mi_arrow_back_24px", "size_24": "mi_arrow_back_24px"},
    {"name": "Forward", "symbol": "mi_arrow_forward_24px", "category": "navigation", "usage": "Navigate forward, next item", "ascii": "→", "size_16": "mi_arrow_forward_24px", "size_24": "mi_arrow_forward_24px"},
    {"name": "Home", "symbol": "mi_home_24px", "category": "navigation", "usage": "Return to main menu/home screen", "ascii": "⌂", "size_16": "mi_home_24px", "size_24": "mi_home_24px"},
    {"name": "Search", "symbol": "mi_search_24px", "category": "navigation", "usage": "Search functionality, find", "ascii": "🔍", "size_16": "mi_search_24px", "size_24": "mi_search_24px"},
    {"name": "Settings", "symbol": "mi_settings_24px", "category": "navigation", "usage": "Settings menu, configuration", "ascii": "⚙", "size_16": "mi_settings_24px", "size_24": "mi_settings_24px"},
    {"name": "Menu", "symbol": "mi_menu_24px", "category": "navigation", "usage": "Hamburger menu, open navigation", "ascii": "☰", "size_16": "mi_menu_24px", "size_24": "mi_menu_24px"},
    {"name": "More (vert)", "symbol": "mi_more_vert_24px", "category": "navigation", "usage": "Additional options menu", "ascii": "⋮", "size_16": "mi_more_vert_24px", "size_24": "mi_more_vert_24px"},
    {"name": "More (horiz)", "symbol": "mi_more_horiz_24px", "category": "navigation", "usage": "Additional options menu", "ascii": "⋯", "size_16": "mi_more_horiz_24px", "size_24": "mi_more_horiz_24px"},
    {"name": "Close", "symbol": "mi_close_24px", "category": "navigation", "usage": "Close dialog, dismiss", "ascii": "✕", "size_16": "mi_close_24px", "size_24": "mi_close_24px"},
    {"name": "Check", "symbol": "mi_check_24px", "category": "navigation", "usage": "Confirm, select, OK", "ascii": "✓", "size_16": "mi_check_24px", "size_24": "mi_check_24px"},
    {"name": "Check Circle", "symbol": "mi_check_circle_24px", "category": "navigation", "usage": "Success confirmation", "ascii": "✓", "size_16": "mi_check_circle_24px", "size_24": "mi_check_circle_24px"},
    {"name": "Help", "symbol": "mi_help_24px", "category": "navigation", "usage": "Help documentation, info", "ascii": "?", "size_16": "mi_help_24px", "size_24": "mi_help_24px"},
    
    # File Operations (14 icons)
    {"name": "Folder", "symbol": "mi_folder_24px", "category": "files", "usage": "Directory, folder view", "ascii": "📁", "size_16": "mi_folder_24px", "size_24": "mi_folder_24px"},
    {"name": "Folder Open", "symbol": "mi_folder_open_24px", "category": "files", "usage": "Active/opened directory", "ascii": "📂", "size_16": "mi_folder_open_24px", "size_24": "mi_folder_open_24px"},
    {"name": "Document", "symbol": "mi_description_24px", "category": "files", "usage": "Generic file, text document", "ascii": "📄", "size_16": "mi_description_24px", "size_24": "mi_description_24px"},
    {"name": "Save", "symbol": "mi_save_24px", "category": "files", "usage": "Save file/settings", "ascii": "💾", "size_16": "mi_save_24px", "size_24": "mi_save_24px"},
    {"name": "Save As", "symbol": "mi_save_alt_24px", "category": "files", "usage": "Save copy, export", "ascii": "💾", "size_16": "mi_save_alt_24px", "size_24": "mi_save_alt_24px"},
    {"name": "Delete", "symbol": "mi_delete_24px", "category": "files", "usage": "Remove file, trash", "ascii": "🗑", "size_16": "mi_delete_24px", "size_24": "mi_delete_24px"},
    {"name": "Copy", "symbol": "mi_content_copy_24px", "category": "files", "usage": "Copy to clipboard", "ascii": "📋", "size_16": "mi_content_copy_24px", "size_24": "mi_content_copy_24px"},
    {"name": "Paste", "symbol": "mi_content_paste_24px", "category": "files", "usage": "Paste from clipboard", "ascii": "📋", "size_16": "mi_content_paste_24px", "size_24": "mi_content_paste_24px"},
    {"name": "Move", "symbol": "mi_drive_file_move_24px", "category": "files", "usage": "Move/cut operation", "ascii": "📦", "size_16": "mi_drive_file_move_24px", "size_24": "mi_drive_file_move_24px"},
    {"name": "Rename", "symbol": "mi_drive_file_rename_outline_24px", "category": "files", "usage": "Rename file dialog", "ascii": "✏", "size_16": "mi_drive_file_rename_outline_24px", "size_24": "mi_drive_file_rename_outline_24px"},
    {"name": "Upload File", "symbol": "mi_file_upload_24px", "category": "files", "usage": "File upload picker", "ascii": "📤", "size_16": "mi_file_upload_24px", "size_24": "mi_file_upload_24px"},
    {"name": "Upload", "symbol": "mi_upload_file_24px", "category": "files", "usage": "Upload operation", "ascii": "⬆", "size_16": "mi_upload_file_24px", "size_24": "mi_upload_file_24px"},
    {"name": "Cloud", "symbol": "mi_cloud_24px", "category": "files", "usage": "Cloud storage", "ascii": "☁", "size_16": "mi_cloud_24px", "size_24": "mi_cloud_24px"},
    {"name": "SD Card", "symbol": "mi_sd_storage_24px", "category": "files", "usage": "SD card storage", "ascii": "💳", "size_16": "mi_sd_storage_24px", "size_24": "mi_sd_storage_24px"},
    
    # File Types / MIME (8 icons)
    {"name": "Text File", "symbol": "mi_text_snippet_24px", "category": "types", "usage": "Plain text, .txt", "ascii": "📝", "size_16": "mi_text_snippet_24px", "size_24": "mi_text_snippet_24px"},
    {"name": "Code", "symbol": "mi_code_24px", "category": "types", "usage": "Source code, programming", "ascii": "<>", "size_16": "mi_code_24px", "size_24": "mi_code_24px"},
    {"name": "HTML", "symbol": "mi_html_24px", "category": "types", "usage": "HTML document", "ascii": "H", "size_16": "mi_html_24px", "size_24": "mi_html_24px"},
    {"name": "JavaScript", "symbol": "mi_javascript_24px", "category": "types", "usage": "JS/script files", "ascii": "JS", "size_16": "mi_javascript_24px", "size_24": "mi_javascript_24px"},
    {"name": "Image", "symbol": "mi_image_24px", "category": "types", "usage": "Photos, graphics", "ascii": "🖼", "size_16": "mi_image_24px", "size_24": "mi_image_24px"},
    {"name": "Audio", "symbol": "mi_audio_file_24px", "category": "types", "usage": "Music, sound", "ascii": "🎵", "size_16": "mi_audio_file_24px", "size_24": "mi_audio_file_24px"},
    {"name": "Video", "symbol": "mi_video_file_24px", "category": "types", "usage": "Video, movie", "ascii": "🎬", "size_16": "mi_video_file_24px", "size_24": "mi_video_file_24px"},
    {"name": "PDF", "symbol": "mi_picture_as_pdf_24px", "category": "types", "usage": "PDF document", "ascii": "PDF", "size_16": "mi_picture_as_pdf_24px", "size_24": "mi_picture_as_pdf_24px"},
    
    # Cloud & Network (5 icons)
    {"name": "Cloud Upload", "symbol": "mi_cloud_upload_24px", "category": "network", "usage": "Upload to cloud", "ascii": "☁⬆", "size_16": "mi_cloud_upload_24px", "size_24": "mi_cloud_upload_24px"},
    {"name": "Cloud Download", "symbol": "mi_cloud_download_24px", "category": "network", "usage": "Download from cloud", "ascii": "☁⬇", "size_16": "mi_cloud_download_24px", "size_24": "mi_cloud_download_24px"},
    {"name": "WiFi", "symbol": "mi_network_wifi_24px", "category": "network", "usage": "WiFi status, network", "ascii": "📶", "size_16": "mi_network_wifi_24px", "size_24": "mi_network_wifi_24px"},
    {"name": "Bluetooth", "symbol": "mi_bluetooth_24px", "category": "network", "usage": "Bluetooth status", "ascii": "Ⓑ", "size_16": "mi_bluetooth_24px", "size_24": "mi_bluetooth_24px"},
    {"name": "Integration", "symbol": "mi_integration_instructions_24px", "category": "network", "usage": "API, webhook, integration", "ascii": "⚡", "size_16": "mi_integration_instructions_24px", "size_24": "mi_integration_instructions_24px"},
    
    # Device Status (6 icons)
    {"name": "Battery Full", "symbol": "mi_battery_full_24px", "category": "status", "usage": "Battery status ≥80%", "ascii": "🔋", "size_16": "mi_battery_full_24px", "size_24": "mi_battery_full_24px"},
    {"name": "Battery Charging", "symbol": "mi_battery_charging_full_24px", "category": "status", "usage": "Charging indicator", "ascii": "⚡", "size_16": "mi_battery_charging_full_24px", "size_24": "mi_battery_charging_full_24px"},
    {"name": "Brightness", "symbol": "mi_brightness_high_24px", "category": "status", "usage": "Screen brightness", "ascii": "☀", "size_16": "mi_brightness_high_24px", "size_24": "mi_brightness_high_24px"},
    {"name": "Volume On", "symbol": "mi_volume_up_24px", "category": "status", "usage": "Volume/sound enabled", "ascii": "🔊", "size_16": "mi_volume_up_24px", "size_24": "mi_volume_up_24px"},
    {"name": "Volume Mute", "symbol": "mi_volume_off_24px", "category": "status", "usage": "Sound muted", "ascii": "🔇", "size_16": "mi_volume_off_24px", "size_24": "mi_volume_off_24px"},
    {"name": "Power", "symbol": "mi_power_settings_new_24px", "category": "status", "usage": "Power button, shutdown", "ascii": "⏻", "size_16": "mi_power_settings_new_24px", "size_24": "mi_power_settings_new_24px"},
    
    # Media Control (3 icons)
    {"name": "Play", "symbol": "mi_play_arrow_24px", "category": "media", "usage": "Start playback", "ascii": "▶", "size_16": "mi_play_arrow_24px", "size_24": "mi_play_arrow_24px"},
    {"name": "Pause", "symbol": "mi_pause_24px", "category": "media", "usage": "Pause playback", "ascii": "⏸", "size_16": "mi_pause_24px", "size_24": "mi_pause_24px"},
    {"name": "Stop", "symbol": "mi_stop_24px", "category": "media", "usage": "Stop playback", "ascii": "⏹", "size_16": "mi_stop_24px", "size_24": "mi_stop_24px"},
    
    # Security & Alerts (5 icons)
    {"name": "Lock", "symbol": "mi_lock_24px", "category": "security", "usage": "Secure, encrypted, locked", "ascii": "🔒", "size_16": "mi_lock_24px", "size_24": "mi_lock_24px"},
    {"name": "Unlock", "symbol": "mi_lock_open_24px", "category": "security", "usage": "Unsecure, decrypted, open", "ascii": "🔓", "size_16": "mi_lock_open_24px", "size_24": "mi_lock_open_24px"},
    {"name": "Info", "symbol": "mi_info_24px", "category": "security", "usage": "Info message", "ascii": "ℹ", "size_16": "mi_info_24px", "size_24": "mi_info_24px"},
    {"name": "Warning", "symbol": "mi_warning_24px", "category": "security", "usage": "Warning message", "ascii": "⚠", "size_16": "mi_warning_24px", "size_24": "mi_warning_24px"},
    {"name": "Error", "symbol": "mi_error_24px", "category": "security", "usage": "Error message, critical alert", "ascii": "⛔", "size_16": "mi_error_24px", "size_24": "mi_error_24px"},
]


# Lookup helpers
def get_icon_by_name(name: str) -> Optional[IconInfo]:
    """Get icon info by display name"""
    for icon in MATERIAL_ICONS:
        if icon["name"].lower() == name.lower():
            return icon
    return None


def get_icon_by_symbol(symbol: str) -> Optional[IconInfo]:
    """Get icon info by C symbol name"""
    for icon in MATERIAL_ICONS:
        if icon["symbol"] == symbol or icon["size_16"] == symbol or icon["size_24"] == symbol:
            return icon
    return None


def get_icons_by_category(category: str) -> List[IconInfo]:
    """Get all icons in a category"""
    return [icon for icon in MATERIAL_ICONS if icon["category"] == category]


def get_all_categories() -> List[str]:
    """Get all unique categories"""
    return sorted(set(icon["category"] for icon in MATERIAL_ICONS))


# Icon palette for UI Designer
ICON_PALETTE = {
    "navigation": [icon for icon in MATERIAL_ICONS if icon["category"] == "navigation"],
    "files": [icon for icon in MATERIAL_ICONS if icon["category"] == "files"],
    "types": [icon for icon in MATERIAL_ICONS if icon["category"] == "types"],
    "network": [icon for icon in MATERIAL_ICONS if icon["category"] == "network"],
    "status": [icon for icon in MATERIAL_ICONS if icon["category"] == "status"],
    "media": [icon for icon in MATERIAL_ICONS if icon["category"] == "media"],
    "security": [icon for icon in MATERIAL_ICONS if icon["category"] == "security"],
}


def filter_icons(term: str = "", category: Optional[str] = None) -> List[IconInfo]:
    """Filter icons by search term (name or symbol or ascii) and optional category.

    Args:
        term: Case-insensitive substring to match against name, symbol, ascii.
        category: Optional category to restrict results (must match exact category name).

    Returns:
        List of matching icon metadata dictionaries ordered by name.
    """
    term_low = term.strip().lower()
    results: List[IconInfo] = []
    for icon in MATERIAL_ICONS:
        if category and icon["category"] != category:
            continue
        if not term_low:
            results.append(icon)
            continue
        if (
            term_low in icon["name"].lower()
            or term_low in icon["symbol"].lower()
            or term_low in icon["ascii"].lower()
        ):
            results.append(icon)
    return sorted(results, key=lambda ic: ic["name"].lower())

