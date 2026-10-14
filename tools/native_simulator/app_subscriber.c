/* Separate translation unit preserves private production names/state. */
#include "services/ui_app/ui_app.c"
int sim_app_screen(void) { return (int)s_screen; }
