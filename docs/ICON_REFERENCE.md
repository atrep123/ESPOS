# ESP32OS Icon Reference

Generated from Material Design Icons (Apache 2.0 license).  
All icons are 16×16px, 1-bit per pixel, packed MSB-first.

## Icon Categories

### Navigation & UI Control (12 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_arrow_back_24px` | Back arrow | Navigate back, return to previous screen |
| `mi_arrow_forward_24px` | Forward arrow | Navigate forward, next item |
| `mi_home_24px` | Home | Return to main menu/home screen |
| `mi_search_24px` | Search | Search functionality, find |
| `mi_settings_24px` | Settings | Settings menu, configuration |
| `mi_menu_24px` | Menu | Hamburger menu, open navigation |
| `mi_more_vert_24px` | More (vertical) | Additional options menu |
| `mi_more_horiz_24px` | More (horizontal) | Additional options menu |
| `mi_close_24px` | Close | Close dialog, dismiss |
| `mi_check_24px` | Check | Confirm, select, OK |
| `mi_check_circle_24px` | Check circle | Success confirmation |
| `mi_help_24px` | Help | Help documentation, info |

### File Operations (14 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_folder_24px` | Folder (closed) | Directory, folder view |
| `mi_folder_open_24px` | Folder (open) | Active/opened directory |
| `mi_description_24px` | Document | Generic file, text document |
| `mi_save_24px` | Save | Save file/settings |
| `mi_save_alt_24px` | Save as | Save copy, export |
| `mi_delete_24px` | Delete | Remove file, trash |
| `mi_content_copy_24px` | Copy | Copy to clipboard |
| `mi_content_paste_24px` | Paste | Paste from clipboard |
| `mi_drive_file_move_24px` | Move file | Move/cut operation |
| `mi_drive_file_rename_outline_24px` | Rename | Rename file dialog |
| `mi_file_upload_24px` | Upload file | File upload picker |
| `mi_upload_file_24px` | Upload action | Upload operation |
| `mi_cloud_24px` | Cloud | Cloud storage |
| `mi_sd_storage_24px` | SD card | SD card storage |

### File Types / MIME (8 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_text_snippet_24px` | Text file | Plain text, .txt |
| `mi_code_24px` | Code file | Source code, programming |
| `mi_html_24px` | HTML file | HTML document |
| `mi_javascript_24px` | JavaScript file | JS/script files |
| `mi_image_24px` | Image file | Photos, graphics |
| `mi_audio_file_24px` | Audio file | Music, sound |
| `mi_video_file_24px` | Video file | Video, movie |
| `mi_picture_as_pdf_24px` | PDF file | PDF document |

### Cloud & Network (5 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_cloud_upload_24px` | Cloud upload | Upload to cloud |
| `mi_cloud_download_24px` | Cloud download | Download from cloud |
| `mi_network_wifi_24px` | WiFi | WiFi status, network |
| `mi_bluetooth_24px` | Bluetooth | Bluetooth status |
| `mi_integration_instructions_24px` | Integration | API, webhook, integration |

### Device Status (6 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_battery_full_24px` | Battery full | Battery status ≥80% |
| `mi_battery_charging_full_24px` | Battery charging | Charging indicator |
| `mi_brightness_high_24px` | Brightness | Screen brightness |
| `mi_volume_up_24px` | Volume on | Volume/sound enabled |
| `mi_volume_off_24px` | Volume mute | Sound muted |
| `mi_power_settings_new_24px` | Power | Power button, shutdown |

### Media Control (3 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_play_arrow_24px` | Play | Start playback |
| `mi_pause_24px` | Pause | Pause playback |
| `mi_stop_24px` | Stop | Stop playback |

### Security & Alerts (5 icons)
| Symbol | Name | Usage |
|--------|------|-------|
| `mi_lock_24px` | Locked | Secure, encrypted, locked |
| `mi_lock_open_24px` | Unlocked | Unsecure, decrypted, open |
| `mi_info_24px` | Information | Info message |
| `mi_warning_24px` | Warning | Warning message |
| `mi_error_24px` | Error | Error message, critical alert |

## C Usage

```c
#include "icons.h"

// All icons are 16×16px with the icon_t structure:
typedef struct {
    const char* name;        // Symbol name for debugging
    uint16_t width;          // Always 16
    uint16_t height;         // Always 16
    uint16_t stride_bytes;   // Bytes per row (2 for 16px width)
    const uint8_t* data;     // Packed 1bpp bitmap, MSB-first
} icon_t;

// Example: Draw a folder icon at (10, 20)
display_draw_icon(&mi_folder_24px, 10, 20);
```

## Python/JSON Usage (UI Designer)

```json
{
  "type": "icon",
  "x": 10,
  "y": 20,
  "icon": "mi_folder_24px"
}
```

## Simulator Support

Icons can be approximated in the text-based simulator using ASCII:
- Navigation: `←` `→` `⌂` `⚙` `☰` `✕` `✓`
- Files: `📁` `📄` `💾` `🗑`
- Status: `🔋` `⚡` `🔒` `⚠` `ℹ`

## Asset Sources

- **Source**: Google Material Design Icons (https://github.com/google/material-design-icons)
- **License**: Apache 2.0
- **Format**: 24dp baseline black PNGs, converted to 16×16 1bpp
- **Pipeline**: `tools/icon_pipeline.py --src assets/icons/material/filled --size 16 --invert`

## Regenerating Icons

```powershell
# 16px set (current)
python tools/icon_pipeline.py --src assets/icons/material/filled --size 16 --invert --out-c src/icons.c --out-h src/icons.h

# 24px set (high-res variant)
python tools/icon_pipeline.py --src assets/icons/material/filled --size 24 --invert --out-c src/icons_24.c --out-h src/icons_24.h
```

## Notes

- Icons use inverted threshold (`--invert`) because source PNGs are black on transparent
- All icons are monochrome (1-bit); foreground/background colors are applied at render time
- Symbol names preserve the `_24px` suffix to match Material Icons naming
- Prefix `mi_` = Material Icons
