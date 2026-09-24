#include <gtk/gtk.h>
#include <stdlib.h>

typedef enum {
    MODE_NONE,
    MODE_RX
} AppMode;

typedef struct {
    GtkApplication *app;
    GtkWidget *window;
    GtkWidget *stack;

    GtkWidget *home_page;
    GtkWidget *rx_page;
    GtkWidget *preset_page;

    GtkWidget *preset_title;

    /* RX */
    GtkWidget *rx_label;

    /* Preset widgets */
    GtkWidget *cmb_freq;
    GtkWidget *cmb_mode;
    GtkWidget *cmb_sr;
    GtkWidget *cmb_rolloff;

    /* Saved preset values */
    gchar *freq_mhz;
    gchar *modulation;
    gchar *symbol_rate;
    gchar *rolloff;

    AppMode current_mode;

} AppData;


/* =========================================================
 * Utility
 * ========================================================= */

static void set_default_presets(AppData *ad)
{
    g_free(ad->freq_mhz);
    g_free(ad->modulation);
    g_free(ad->symbol_rate);
    g_free(ad->rolloff);

    ad->freq_mhz    = g_strdup("2400.0003600");
    ad->modulation  = g_strdup("QPSK1/4");
    ad->symbol_rate = g_strdup("333000");
    ad->rolloff     = g_strdup("0.20");
}


static void go_home(AppData *ad)
{
    ad->current_mode = MODE_NONE;

    gtk_stack_set_visible_child(
        GTK_STACK(ad->stack),
        ad->home_page
    );
}


static void sync_preset_widgets_from_saved(AppData *ad)
{
    /* Frequency */

    if (g_strcmp0(ad->freq_mhz, "437") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 0);
    }
    else if (g_strcmp0(ad->freq_mhz, "438") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 1);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0003600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 2);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0013600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 3);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0023600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 4);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0033600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 5);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0043600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 6);
    }
    else if (g_strcmp0(ad->freq_mhz, "2400.0078600") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 7);
    }
    else {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_freq), 2);
    }


    /* Modulation */

    if (g_strcmp0(ad->modulation, "QPSK1/4") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_mode), 0);
    }
    else if (g_strcmp0(ad->modulation, "QPSK1/2") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_mode), 1);
    }
    else if (g_strcmp0(ad->modulation, "QPSK3/4") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_mode), 2);
    }
    else if (g_strcmp0(ad->modulation, "8PSK3/5") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_mode), 3);
    }
    else {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_mode), 0);
    }


    /* Symbol rate */

    if (g_strcmp0(ad->symbol_rate, "125000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 0);
    }
    else if (g_strcmp0(ad->symbol_rate, "250000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 1);
    }
    else if (g_strcmp0(ad->symbol_rate, "333000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 2);
    }
    else if (g_strcmp0(ad->symbol_rate, "1000000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 3);
    }
    else if (g_strcmp0(ad->symbol_rate, "1500000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 4);
    }
    else if (g_strcmp0(ad->symbol_rate, "2000000") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 5);
    }
    else {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_sr), 2);
    }


    /* Roll-off */

    if (g_strcmp0(ad->rolloff, "0.20") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_rolloff), 0);
    }
    else if (g_strcmp0(ad->rolloff, "0.25") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_rolloff), 1);
    }
    else if (g_strcmp0(ad->rolloff, "0.35") == 0) {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_rolloff), 2);
    }
    else {
        gtk_combo_box_set_active(GTK_COMBO_BOX(ad->cmb_rolloff), 0);
    }
}


static void save_presets_from_widgets(AppData *ad)
{
    gchar *freq;
    gchar *mode;
    gchar *sr;
    gchar *ro;

    freq = gtk_combo_box_text_get_active_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq)
    );

    mode = gtk_combo_box_text_get_active_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_mode)
    );

    sr = gtk_combo_box_text_get_active_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr)
    );

    ro = gtk_combo_box_text_get_active_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_rolloff)
    );


    if (freq != NULL) {
        g_free(ad->freq_mhz);
        ad->freq_mhz = g_strdup(freq);
        g_free(freq);
    }

    if (mode != NULL) {
        g_free(ad->modulation);
        ad->modulation = g_strdup(mode);
        g_free(mode);
    }

    if (sr != NULL) {
        g_free(ad->symbol_rate);
        ad->symbol_rate = g_strdup(sr);
        g_free(sr);
    }

    if (ro != NULL) {
        g_free(ad->rolloff);
        ad->rolloff = g_strdup(ro);
        g_free(ro);
    }


    g_print(
        "Saved preset: freq=%s MHz mode=%s sr=%s rolloff=%s\n",
        ad->freq_mhz,
        ad->modulation,
        ad->symbol_rate,
        ad->rolloff
    );
}


static long long mhz_to_hz(const gchar *mhz)
{
    return (long long)(
        g_ascii_strtod(mhz, NULL) * 1000000.0 + 0.5
    );
}


/* =========================================================
 * RX command
 * ========================================================= */

static void launch_rx_command(AppData *ad)
{
    long long rx_hz;
    gchar *cmd;
    GError *error = NULL;

    rx_hz = mhz_to_hz(ad->freq_mhz);

    cmd = g_strdup_printf(
        "./start_rx.sh %lld %s %s",
        rx_hz,
        ad->modulation,
        ad->symbol_rate
    );

    g_print("[RX] command: %s\n", cmd);

    if (!g_spawn_command_line_async(cmd, &error)) {
        g_printerr(
            "[RX] start error: %s\n",
            error != NULL ? error->message : "unknown error"
        );

        g_clear_error(&error);
    }

    g_free(cmd);
}


static void stop_rx(AppData *ad)
{
    GError *error = NULL;

    (void)ad;

    g_print("[RX] stop\n");

    if (!g_spawn_command_line_async("./stop_rx.sh", &error)) {
        g_printerr(
            "[RX] stop error: %s\n",
            error != NULL ? error->message : "unknown error"
        );

        g_clear_error(&error);
    }
}


/* =========================================================
 * Handlers
 * ========================================================= */

static void on_rx_clicked(GtkButton *button, gpointer user_data)
{
    AppData *ad = (AppData *)user_data;
    gchar *status_text;

    (void)button;

    ad->current_mode = MODE_RX;

    launch_rx_command(ad);

    status_text = g_strdup_printf(
        "Receiving...\n\n"
        "%s MHz\n"
        "%s\n"
        "%s Sym/s\n"
        "Roll-off %s\n\n"
        "Touch screen to stop",
        ad->freq_mhz,
        ad->modulation,
        ad->symbol_rate,
        ad->rolloff
    );

    gtk_label_set_text(
        GTK_LABEL(ad->rx_label),
        status_text
    );

    g_free(status_text);

    gtk_stack_set_visible_child(
        GTK_STACK(ad->stack),
        ad->rx_page
    );
}

/*
static void on_rx_screen_clicked(
    GtkGestureClick *gesture,
    gint n_press,
    gdouble x,
    gdouble y,
    gpointer user_data
)
{
    AppData *ad = (AppData *)user_data;

    (void)gesture;
    (void)x;
    (void)y;

    if (n_press == 1) {
        stop_rx(ad);
        go_home(ad);
    }
}
*/

static void on_stop_rx_clicked(GtkButton *button, gpointer user_data)
{
    AppData *ad = (AppData *)user_data;

    (void)button;

    stop_rx(ad);
    go_home(ad);
}

static void on_preset_done_clicked(
    GtkButton *button,
    gpointer user_data
)
{
    AppData *ad = (AppData *)user_data;

    (void)button;

    save_presets_from_widgets(ad);
    go_home(ad);
}


static void on_open_preset_clicked(
    GtkButton *button,
    gpointer user_data
)
{
    AppData *ad = (AppData *)user_data;

    (void)button;

    sync_preset_widgets_from_saved(ad);

    gtk_label_set_text(
        GTK_LABEL(ad->preset_title),
        "Receiver Preset"
    );

    gtk_stack_set_visible_child(
        GTK_STACK(ad->stack),
        ad->preset_page
    );
}


/* ウィンドウを閉じるとき受信も停止する */
static gboolean on_window_close_request(
    GtkWindow *window,
    gpointer user_data
)
{
    AppData *ad = (AppData *)user_data;

    (void)window;

    if (ad->current_mode == MODE_RX) {
        stop_rx(ad);
    }

    return FALSE;
}


/* =========================================================
 * Page creation
 * ========================================================= */

static GtkWidget *create_home_page(AppData *ad)
{
    GtkWidget *box;
    GtkWidget *title;
    GtkWidget *btn_rx;
    GtkWidget *btn_preset;

    box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 20);

    title = gtk_label_new("DVB-S2 Receiver");

    btn_rx = gtk_button_new_with_label("RX");
    btn_preset = gtk_button_new_with_label("Preset");

    gtk_widget_set_margin_top(box, 20);
    gtk_widget_set_margin_bottom(box, 20);
    gtk_widget_set_margin_start(box, 20);
    gtk_widget_set_margin_end(box, 20);

    gtk_widget_set_margin_bottom(title, 5);

    gtk_widget_set_hexpand(btn_rx, TRUE);
    gtk_widget_set_vexpand(btn_rx, TRUE);

    gtk_widget_set_hexpand(btn_preset, TRUE);
    gtk_widget_set_vexpand(btn_preset, TRUE);

    gtk_box_append(GTK_BOX(box), title);
    gtk_box_append(GTK_BOX(box), btn_rx);
    gtk_box_append(GTK_BOX(box), btn_preset);

    g_signal_connect(
        btn_rx,
        "clicked",
        G_CALLBACK(on_rx_clicked),
        ad
    );

    g_signal_connect(
        btn_preset,
        "clicked",
        G_CALLBACK(on_open_preset_clicked),
        ad
    );

    return box;
}

/*

*/





static GtkWidget *create_rx_page(AppData *ad)
{
    GtkWidget *box;
    GtkWidget *stop_button;

    box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);

    gtk_widget_set_margin_top(box, 20);
    gtk_widget_set_margin_bottom(box, 20);
    gtk_widget_set_margin_start(box, 20);
    gtk_widget_set_margin_end(box, 20);

    ad->rx_label = gtk_label_new(
        "Receiving...\n\nPress STOP RX to stop"
    );

    gtk_label_set_justify(
        GTK_LABEL(ad->rx_label),
        GTK_JUSTIFY_CENTER
    );

    gtk_widget_set_hexpand(ad->rx_label, TRUE);
    gtk_widget_set_vexpand(ad->rx_label, TRUE);

    stop_button = gtk_button_new_with_label("STOP RX");

    gtk_widget_set_hexpand(stop_button, TRUE);
    gtk_widget_set_size_request(stop_button, -1, 80);

    gtk_box_append(GTK_BOX(box), ad->rx_label);
    gtk_box_append(GTK_BOX(box), stop_button);

    g_signal_connect(
        stop_button,
        "clicked",
        G_CALLBACK(on_stop_rx_clicked),
        ad
    );

    return box;
}


static GtkWidget *create_preset_page(AppData *ad)
{
    GtkWidget *box;
    GtkWidget *grid;
    GtkWidget *done_btn;

    GtkWidget *lbl0;
    GtkWidget *lbl1;
    GtkWidget *lbl2;
    GtkWidget *lbl3;

    box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    grid = gtk_grid_new();
    done_btn = gtk_button_new_with_label("Done");

    lbl0 = gtk_label_new("Frequency (MHz)");
    lbl1 = gtk_label_new("Mode");
    lbl2 = gtk_label_new("Symbol Rate");
    lbl3 = gtk_label_new("Roll-off");

    ad->cmb_freq = gtk_combo_box_text_new();
    ad->cmb_mode = gtk_combo_box_text_new();
    ad->cmb_sr = gtk_combo_box_text_new();
    ad->cmb_rolloff = gtk_combo_box_text_new();

    ad->preset_title = gtk_label_new("Receiver Preset");

    gtk_widget_set_margin_top(box, 20);
    gtk_widget_set_margin_bottom(box, 20);
    gtk_widget_set_margin_start(box, 20);
    gtk_widget_set_margin_end(box, 20);

    gtk_label_set_xalign(
        GTK_LABEL(ad->preset_title),
        0.0f
    );

    gtk_box_append(
        GTK_BOX(box),
        ad->preset_title
    );

    gtk_grid_set_row_spacing(GTK_GRID(grid), 10);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);


    /* Frequency */

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "437"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "438"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0003600"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0013600"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0023600"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0033600"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0043600"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_freq),
        "2400.0078600"
    );


    /* Mode */

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_mode),
        "QPSK1/4"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_mode),
        "QPSK1/2"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_mode),
        "QPSK3/4"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_mode),
        "8PSK3/5"
    );


    /* Symbol rate */

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "125000"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "250000"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "333000"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "1000000"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "1500000"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_sr),
        "2000000"
    );


    /* Roll-off */

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_rolloff),
        "0.20"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_rolloff),
        "0.25"
    );

    gtk_combo_box_text_append_text(
        GTK_COMBO_BOX_TEXT(ad->cmb_rolloff),
        "0.35"
    );


    gtk_grid_attach(
        GTK_GRID(grid),
        lbl0,
        0, 0, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        ad->cmb_freq,
        1, 0, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        lbl1,
        0, 1, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        ad->cmb_mode,
        1, 1, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        lbl2,
        0, 2, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        ad->cmb_sr,
        1, 2, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        lbl3,
        0, 3, 1, 1
    );

    gtk_grid_attach(
        GTK_GRID(grid),
        ad->cmb_rolloff,
        1, 3, 1, 1
    );

    gtk_box_append(GTK_BOX(box), grid);

    gtk_widget_set_margin_top(done_btn, 20);
    gtk_widget_set_size_request(done_btn, -1, 60);

    gtk_box_append(GTK_BOX(box), done_btn);

    g_signal_connect(
        done_btn,
        "clicked",
        G_CALLBACK(on_preset_done_clicked),
        ad
    );

    return box;
}


/* =========================================================
 * Activate / main
 * ========================================================= */

static void activate(GtkApplication *app, gpointer user_data)
{
    AppData *ad;

    (void)user_data;

    ad = g_new0(AppData, 1);

    ad->app = app;
    ad->current_mode = MODE_NONE;

    set_default_presets(ad);

    ad->window = gtk_application_window_new(app);

    gtk_window_set_title(
        GTK_WINDOW(ad->window),
        "DVB-S2 Receiver"
    );

    gtk_window_set_default_size(
        GTK_WINDOW(ad->window),
        800,
        480
    );

    ad->stack = gtk_stack_new();

    gtk_window_set_child(
        GTK_WINDOW(ad->window),
        ad->stack
    );

    ad->home_page = create_home_page(ad);
    ad->rx_page = create_rx_page(ad);
    ad->preset_page = create_preset_page(ad);

    gtk_stack_add_named(
        GTK_STACK(ad->stack),
        ad->home_page,
        "home"
    );

    gtk_stack_add_named(
        GTK_STACK(ad->stack),
        ad->rx_page,
        "rx"
    );

    gtk_stack_add_named(
        GTK_STACK(ad->stack),
        ad->preset_page,
        "preset"
    );

    gtk_stack_set_visible_child(
        GTK_STACK(ad->stack),
        ad->home_page
    );

    g_signal_connect(
        ad->window,
        "close-request",
        G_CALLBACK(on_window_close_request),
        ad
    );

    gtk_window_present(GTK_WINDOW(ad->window));
}


int main(int argc, char **argv)
{
    GtkApplication *app;
    int status;

    app = gtk_application_new(
        "com.shinji.dvbs2receiver",
        G_APPLICATION_DEFAULT_FLAGS
    );

    g_signal_connect(
        app,
        "activate",
        G_CALLBACK(activate),
        NULL
    );

    status = g_application_run(
        G_APPLICATION(app),
        argc,
        argv
    );

    g_object_unref(app);

    return status;
}

