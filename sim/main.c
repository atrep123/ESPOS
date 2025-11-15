#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <conio.h>
#else
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#endif

#include "../src/services/ui/ui_core.h"

/* ANSI color codes */
#define ANSI_RESET "\033[0m"
#define ANSI_BOLD "\033[1m"
#define ANSI_DIM "\033[2m"
#define ANSI_BLACK "\033[30m"
#define ANSI_RED "\033[31m"
#define ANSI_GREEN "\033[32m"
#define ANSI_YELLOW "\033[33m"
#define ANSI_BLUE "\033[34m"
#define ANSI_MAGENTA "\033[35m"
#define ANSI_CYAN "\033[36m"
#define ANSI_WHITE "\033[37m"
#define ANSI_BG_BLACK "\033[40m"
#define ANSI_BG_RED "\033[41m"
#define ANSI_BG_GREEN "\033[42m"
#define ANSI_BG_YELLOW "\033[43m"
#define ANSI_BG_BLUE "\033[44m"
#define ANSI_BG_MAGENTA "\033[45m"
#define ANSI_BG_CYAN "\033[46m"
#define ANSI_BG_WHITE "\033[47m"

static void clear_screen(void)
{
#ifdef _WIN32
    /* Use ANSI escape sequence - works on Windows 10+ */
    printf("\033[2J\033[H");
#else
    /* ANSI escape sequence to clear screen and move cursor home. */
    printf("\033[2J\033[H");
#endif
}

static void enable_ansi_colors(void)
{
#ifdef _WIN32
    /* Enable ANSI escape sequences on Windows 10+ */
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD dwMode = 0;
    GetConsoleMode(hOut, &dwMode);
    dwMode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING;
    SetConsoleMode(hOut, dwMode);
#endif
}

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r & 0xF8) << 8) | ((uint16_t)(g & 0xFC) << 3) | (uint16_t)(b >> 3);
}

static void rgb565_to_rgb(uint16_t color, uint8_t *r, uint8_t *g, uint8_t *b)
{
    *r = (uint8_t)((color >> 11) & 0x1F) << 3;
    *g = (uint8_t)((color >> 5) & 0x3F) << 2;
    *b = (uint8_t)(color & 0x1F) << 3;
}

static const char* get_ansi_color(uint16_t rgb565_color)
{
    uint8_t r, g, b;
    rgb565_to_rgb(rgb565_color, &r, &g, &b);
    
    /* Map to closest ANSI color */
    uint16_t avg = (r + g + b) / 3;
    
    if (avg < 32) return ANSI_BG_BLACK;
    if (r > 200 && g < 100 && b < 100) return ANSI_BG_RED;
    if (r < 100 && g > 200 && b < 100) return ANSI_BG_GREEN;
    if (r > 200 && g > 200 && b < 100) return ANSI_BG_YELLOW;
    if (r < 100 && g < 100 && b > 200) return ANSI_BG_BLUE;
    if (r > 200 && g < 100 && b > 200) return ANSI_BG_MAGENTA;
    if (r < 100 && g > 200 && b > 200) return ANSI_BG_CYAN;
    if (avg > 180) return ANSI_BG_WHITE;
    
    return ANSI_BG_BLACK;
}

#ifdef _WIN32
static int kbhit_nonblock(void)
{
    return _kbhit();
}

static int getch_nonblock(void)
{
    if (_kbhit()) {
        return _getch();
    }
    return -1;
}
#else
static int kbhit_nonblock(void)
{
    struct termios oldt, newt;
    int ch;
    int oldf;
    
    tcgetattr(STDIN_FILENO, &oldt);
    newt = oldt;
    newt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &newt);
    oldf = fcntl(STDIN_FILENO, F_GETFL, 0);
    fcntl(STDIN_FILENO, F_SETFL, oldf | O_NONBLOCK);
    
    ch = getchar();
    
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    fcntl(STDIN_FILENO, F_SETFL, oldf);
    
    if(ch != EOF) {
        ungetc(ch, stdin);
        return 1;
    }
    return 0;
}

static int getch_nonblock(void)
{
    if (kbhit_nonblock()) {
        return getchar();
    }
    return -1;
}
#endif

static void render_frame_sim(const ui_state_t *st, int frame_num, double fps)
{
    /* Map real 256x128 display to character grid.
     * One character column represents 4 pixels horizontally,
     * one row represents 8 pixels vertically. */
    const int width = 256 / 4;   /* 64 cols for 256 px */
    const int height = 128 / 8;  /* 16 rows for 128 px */

    clear_screen();
    
    /* Title bar */
    printf(ANSI_BOLD ANSI_CYAN);
    printf("╔");
    for (int i = 0; i < width; i++) printf("═");
    printf("╗\n" ANSI_RESET);
    
    printf(ANSI_BOLD ANSI_CYAN "║" ANSI_RESET ANSI_BOLD);
    printf(" ESP32 UI SIMULATOR");
    for (int i = 19; i < width; i++) printf(" ");
    printf(ANSI_CYAN "║\n" ANSI_RESET);
    
    printf(ANSI_CYAN);
    printf("╠");
    for (int i = 0; i < width; i++) printf("═");
    printf("╣\n" ANSI_RESET);

    /* Status line */
    const char *scene_name = (st->scene == UI_SCENE_HOME)
                                 ? "HOME"
                                 : (st->scene == UI_SCENE_SETTINGS)
                                       ? "SETTINGS"
                                       : "METRICS";
    uint8_t r, g, b;
    rgb565_to_rgb(st->bg, &r, &g, &b);
    
    printf(ANSI_CYAN "║" ANSI_RESET);
    printf(" Scene: " ANSI_BOLD ANSI_YELLOW "%-10s" ANSI_RESET, scene_name);
    printf(" │ Tick: " ANSI_BOLD "%6ld" ANSI_RESET, (long)st->t);
    printf(" │ FPS: " ANSI_BOLD ANSI_GREEN "%.1f" ANSI_RESET, fps);
    for (int i = 45; i < width; i++) printf(" ");
    printf(ANSI_CYAN "║\n" ANSI_RESET);
    
    /* Color info */
    printf(ANSI_CYAN "║" ANSI_RESET);
    printf(" BG Color: " ANSI_BOLD "RGB(%3d,%3d,%3d)" ANSI_RESET " ", r, g, b);
    printf("0x%04X", st->bg);
    for (int i = 35; i < width; i++) printf(" ");
    printf(ANSI_CYAN "║\n" ANSI_RESET);
    
    printf(ANSI_CYAN);
    printf("╠");
    for (int i = 0; i < width; i++) printf("═");
    printf("╣\n" ANSI_RESET);

    /* Display simulation - large color block */
    const char *bg_color = get_ansi_color(st->bg);
    for (int y = 0; y < height; y++) {
        printf(ANSI_CYAN "║" ANSI_RESET);
        printf("%s", bg_color);
        
        /* Draw some UI elements on the "display" */
        if (y == 2) {
            /* Title on display */
            printf(ANSI_BOLD ANSI_BLACK "  %s  " ANSI_RESET "%s", scene_name, bg_color);
            for (int x = strlen(scene_name) + 4; x < width; x++) printf(" ");
        } else if (y == 5) {
            /* Progress bar */
            int bar_width = width - 4;
            int filled = (int)(st->t % bar_width);
            printf(ANSI_BLACK "  [" ANSI_RESET "%s", bg_color);
            for (int x = 0; x < bar_width; x++) {
                if (x < filled) {
                    printf(ANSI_BOLD ANSI_BLACK "█" ANSI_RESET "%s", bg_color);
                } else {
                    printf(ANSI_DIM ANSI_BLACK "░" ANSI_RESET "%s", bg_color);
                }
            }
            printf(ANSI_BLACK "]" ANSI_RESET "%s ", bg_color);
        } else if (y == 8) {
            /* Status text */
            char status[65];
            snprintf(status, sizeof(status), "  Frame: %d", frame_num);
            printf(ANSI_BLACK "%s" ANSI_RESET "%s", status, bg_color);
            for (int x = strlen(status); x < width; x++) printf(" ");
        } else {
            /* Empty display area */
            for (int x = 0; x < width; x++) printf(" ");
        }
        
        printf(ANSI_RESET ANSI_CYAN "║\n" ANSI_RESET);
    }
    
    printf(ANSI_CYAN);
    printf("╠");
    for (int i = 0; i < width; i++) printf("═");
    printf("╣\n" ANSI_RESET);

    /* Button status */
    printf(ANSI_CYAN "║" ANSI_RESET " Buttons: ");
    
    printf("A:" ANSI_BOLD);
    if (st->btnA) {
        printf(ANSI_GREEN "[●]" ANSI_RESET);
    } else {
        printf(ANSI_DIM "[○]" ANSI_RESET);
    }
    
    printf("  B:" ANSI_BOLD);
    if (st->btnB) {
        printf(ANSI_GREEN "[●]" ANSI_RESET);
    } else {
        printf(ANSI_DIM "[○]" ANSI_RESET);
    }
    
    printf("  C:" ANSI_BOLD);
    if (st->btnC) {
        printf(ANSI_GREEN "[●]" ANSI_RESET);
    } else {
        printf(ANSI_DIM "[○]" ANSI_RESET);
    }
    
    for (int i = 36; i < width; i++) printf(" ");
    printf(ANSI_CYAN "║\n" ANSI_RESET);
    
    printf(ANSI_CYAN);
    printf("╠");
    for (int i = 0; i < width; i++) printf("═");
    printf("╣\n" ANSI_RESET);
    
    /* Help text */
    printf(ANSI_CYAN "║" ANSI_RESET ANSI_DIM);
    printf(" Controls: [A] Button A  [B] Button B  [C] Button C  [Q] Quit");
    for (int i = 60; i < width; i++) printf(" ");
    printf(ANSI_RESET ANSI_CYAN "║\n" ANSI_RESET);
    
    printf(ANSI_CYAN);
    printf("║" ANSI_DIM);
    printf("           [R] Red  [G] Green  [Y] Yellow  [W] White  [K] Black");
    for (int i = 62; i < width; i++) printf(" ");
    printf(ANSI_RESET ANSI_CYAN "║\n" ANSI_RESET);
    
    printf(ANSI_CYAN);
    printf("╚");
    for (int i = 0; i < width; i++) printf("═");
    printf("╝\n" ANSI_RESET);
    
    fflush(stdout);
}

int main(void)
{
    enable_ansi_colors();
    
    ui_state_t st;
    ui_core_init(&st);

    int frame = 0;
    int running = 1;
    int auto_demo = 0; /* Toggle for auto demo mode */
    
    clock_t start_time = clock();
    clock_t last_frame_time = start_time;
    double fps = 0.0;

    printf(ANSI_BOLD ANSI_GREEN "\n=== ESP32 UI SIMULATOR STARTED ===\n" ANSI_RESET);
    printf(ANSI_DIM "Press keys to interact or wait for auto demo...\n\n" ANSI_RESET);
    
#ifdef _WIN32
    Sleep(1000);
#else
    sleep(1);
#endif

    while (running) {
        clock_t current_time = clock();
        double elapsed = (double)(current_time - last_frame_time) / CLOCKS_PER_SEC;
        
        /* Calculate FPS */
        if (elapsed > 0) {
            fps = 1.0 / elapsed;
        }
        last_frame_time = current_time;
        
        st.t++;

        /* Check for keyboard input */
        int key = getch_nonblock();
        if (key != -1) {
            switch (key) {
                case 'q':
                case 'Q':
                    running = 0;
                    break;
                case 'a':
                case 'A':
                    ui_core_on_button(&st, 0, !st.btnA);
                    break;
                case 'b':
                case 'B':
                    ui_core_on_button(&st, 1, !st.btnB);
                    break;
                case 'c':
                case 'C':
                    ui_core_on_button(&st, 2, !st.btnC);
                    break;
                case 'r':
                case 'R':
                    ui_core_on_rpc_bg(&st, 0xFF0000U); /* red */
                    break;
                case 'g':
                case 'G':
                    ui_core_on_rpc_bg(&st, 0x00FF00U); /* green */
                    break;
                case 'y':
                case 'Y':
                    ui_core_on_rpc_bg(&st, 0xFFFF00U); /* yellow */
                    break;
                case 'w':
                case 'W':
                    ui_core_on_rpc_bg(&st, 0xFFFFFFU); /* white */
                    break;
                case 'k':
                case 'K':
                    ui_core_on_rpc_bg(&st, 0x000000U); /* black */
                    break;
                case 'd':
                case 'D':
                    auto_demo = !auto_demo;
                    break;
            }
        }

        /* Auto demo script */
        if (auto_demo) {
            if (frame == 30) {
                ui_core_on_button(&st, 0, true);
            }
            if (frame == 35) {
                ui_core_on_button(&st, 0, false);
            }
            if (frame == 50) {
                ui_core_on_rpc_bg(&st, 0xFF0000U); /* red */
            }
            if (frame == 80) {
                ui_core_on_rpc_bg(&st, 0x00A040U); /* green-ish */
            }
            if (frame == 110) {
                ui_core_on_rpc_bg(&st, 0x4080FFU); /* blue */
            }
            if (frame == 140) {
                ui_core_on_rpc_bg(&st, 0xFFC000U); /* orange */
            }
            if (frame == 170) {
                ui_core_on_button(&st, 1, true);
            }
            if (frame == 175) {
                ui_core_on_button(&st, 1, false);
            }
            if (frame >= 200) {
                frame = 0;
                ui_core_init(&st);
            }
        }

        ui_core_on_tick(&st);
        render_frame_sim(&st, frame, fps);
        frame++;

        /* Frame delay (~120 FPS target) */
#ifdef _WIN32
        Sleep(8);
#else
        struct timespec ts = {0, 8 * 1000 * 1000};
        nanosleep(&ts, NULL);
#endif
    }

    clear_screen();
    printf(ANSI_BOLD ANSI_YELLOW "\n=== SIMULATOR STOPPED ===\n" ANSI_RESET);
    printf("Total frames: %d\n", frame);
    printf("Total time: %.2f seconds\n", (double)(clock() - start_time) / CLOCKS_PER_SEC);
    printf(ANSI_DIM "Goodbye!\n\n" ANSI_RESET);

    return 0;
}
