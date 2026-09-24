// ============================================================
//  W5500_PA_PTT_Control.ino
//  ESP32 + W5500 イーサネット経由 GPIO25/26/27 電源制御
//  - PTT / PA用電源のON/OFFをブラウザから制御（ラッチ式）
//  - DHCPでIPアドレス取得
//  - Arduino公式 Ethernet ライブラリ（W5500対応）を使用
//
//  【配線】
//  W5500      ESP32 (VSPI)
//  --------   ------------
//  SCK        GPIO 18
//  MISO       GPIO 19
//  MOSI       GPIO 23
//  CS(SS)     GPIO 5
//  RST        (未使用。EN/3.3Vへ配線 or 未接続可)
//  VCC        3.3V
//  GND        GND
//
//  出力（ラッチ式ON/OFF、いずれもactive-HIGH想定）
//  LNA: GPIO 25 （受信プリアンプ。起動時はON＝受信状態）
//  PTT: GPIO 26 （起動時はOFF）
//  PA : GPIO 27 （起動時はOFF）
//
//  【shonan-android 連携】
//  送信ボタンON  : GET /tx?state=on
//    → LNA off → 100ms待機 → PTT/PA を同時にon
//  送信ボタンOFF : GET /tx?state=off
//    → PA/PTT を同時にoff → 100ms待機 → LNA on
// ============================================================

#include <SPI.h>
#include <Ethernet.h>

// ============================================================
//  設定
// ============================================================

// W5500にはMACアドレスが内蔵されていないため任意の値を設定
// （同一ネットワーク内で他機器と重複しないこと）
static byte mac[] = { 0x02, 0xAA, 0xBB, 0xCC, 0xDE, 0x01 };

const int PIN_CS  = 5;

const int IDX_LNA = 0;
const int IDX_PTT = 1;
const int IDX_PA  = 2;

const int PIN_OUT[3] = { 25, 26, 27 };
const char* OUT_LABEL[3] = { "LNA (GPIO25)", "PTT (GPIO26)", "PA (GPIO27)" };

// 基板搭載LED（PTT ON中に点灯）
const int PIN_ONBOARD_LED = 2;

// 起動時はLNA=ON（受信状態）、PTT/PA=OFF
bool outState[3] = { true, false, false };

bool txActive = false;

EthernetServer server(80);
bool linkUp = false;

// ============================================================
//  出力制御
// ============================================================

void applyOutput(int idx) {
    digitalWrite(PIN_OUT[idx], outState[idx] ? HIGH : LOW);
    Serial.printf("[OUT] %s -> %s\n", OUT_LABEL[idx], outState[idx] ? "ON" : "OFF");
    if (idx == IDX_PTT) {
        digitalWrite(PIN_ONBOARD_LED, outState[IDX_PTT] ? HIGH : LOW);
    }
}

void setOutput(int idx, bool on) {
    if (idx < 0 || idx > 2) return;
    outState[idx] = on;
    applyOutput(idx);
}

void toggleOutput(int idx) {
    if (idx < 0 || idx > 2) return;
    setOutput(idx, !outState[idx]);
}

// ============================================================
//  TX/RX シーケンス（shonan-android 連携）
// ============================================================

void txStart() {
    if (txActive) return;
    txActive = true;
    Serial.println("[TX] 送信シーケンス開始");
    setOutput(IDX_LNA, false);   // LNAを先にOFF
    delay(100);                  // 100ms待機
    setOutput(IDX_PTT, true);    // PTTとPAを同時にON
    setOutput(IDX_PA, true);
    Serial.println("[TX] 送信シーケンス完了 (LNA off -> 100ms -> PTT/PA on)");
}

void txStop() {
    if (!txActive) return;
    txActive = false;
    Serial.println("[TX] 受信復帰シーケンス開始");
    setOutput(IDX_PA, false);    // PAとPTTを先に同時にOFF
    setOutput(IDX_PTT, false);
    delay(100);                  // 100ms待機
    setOutput(IDX_LNA, true);    // LNAをON
    Serial.println("[TX] 受信復帰シーケンス完了 (PA/PTT off -> 100ms -> LNA on)");
}

// ============================================================
//  HTTPリクエスト処理（簡易パーサ）
//  対応パス:
//    GET /               ステータスページ
//    GET /toggle?ch=0..2 指定チャンネルをトグルして / へリダイレクト
//    GET /api/status     JSON形式で現在状態を返す
// ============================================================

void sendStatusPage(EthernetClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html; charset=UTF-8");
    client.println("Connection: close");
    client.println();

    client.println("<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>");
    client.println("<meta name='viewport' content='width=device-width,initial-scale=1'>");
    client.println("<title>PA/PTT 電源制御</title>");
    client.println("<style>");
    client.println("body{margin:0;font-family:sans-serif;background:#000;color:#eee;text-align:center;padding-top:30px}");
    client.println("h1{color:#aaa;font-size:1.3em}");
    client.println(".card{display:inline-block;margin:12px;background:#111;border-radius:12px;padding:20px 28px;min-width:180px}");
    client.println(".label{color:#888;font-size:.9em;margin-bottom:10px}");
    client.println(".state{font-size:1.6em;font-weight:bold;margin-bottom:14px}");
    client.println(".on{color:#4c9}.off{color:#c66}");
    client.println("a.btn{display:inline-block;padding:10px 26px;border-radius:8px;text-decoration:none;font-size:1em}");
    client.println(".btn-on{background:#1a4;color:#fff}.btn-off{background:#a11;color:#fff}");
    client.println("</style></head><body>");
    client.println("<h1>&#9889; PA/PTT 電源制御</h1>");
    client.print("<p style='font-size:1.1em'>状態: <b style='color:");
    client.print(txActive ? "#f66'>送信中(TX)" : "#6c9'>受信中(RX)");
    client.println("</b></p>");

    for (int i = 0; i < 3; i++) {
        client.print("<div class='card'><div class='label'>");
        client.print(OUT_LABEL[i]);
        client.print("</div><div class='state ");
        client.print(outState[i] ? "on'>ON" : "off'>OFF");
        client.print("</div><a class='btn ");
        client.print(outState[i] ? "btn-off" : "btn-on");
        client.print("' href='/toggle?ch=");
        client.print(i);
        client.print("'>");
        client.print(outState[i] ? "OFFにする" : "ONにする");
        client.println("</a></div>");
    }

    client.print("<p style='color:#555;margin-top:20px;font-size:.8em'>IP: ");
    client.print(Ethernet.localIP());
    client.println("</p>");
    client.println("</body></html>");
}

void sendStatusJson(EthernetClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: application/json");
    client.println("Connection: close");
    client.println();
    client.print("{\"out1\":");
    client.print(outState[0] ? "true" : "false");
    client.print(",\"out2\":");
    client.print(outState[1] ? "true" : "false");
    client.print(",\"out3\":");
    client.print(outState[2] ? "true" : "false");
    client.print(",\"tx_active\":");
    client.print(txActive ? "true" : "false");
    client.println("}");
}

void sendRedirectRoot(EthernetClient& client) {
    client.println("HTTP/1.1 303 See Other");
    client.println("Location: /");
    client.println("Connection: close");
    client.println();
}

void handleClient(EthernetClient& client) {
    String reqLine;
    while (client.connected() && client.available() == 0) delay(1);
    if (client.available()) {
        reqLine = client.readStringUntil('\n');
    }
    // ヘッダー残りを読み捨てる
    while (client.connected()) {
        String line = client.readStringUntil('\n');
        if (line == "\r" || line.length() == 0) break;
    }

    Serial.println("[HTTP] " + reqLine);

    if (reqLine.startsWith("GET /tx")) {
        // shonan-android からのTX開始/終了通知
        if (reqLine.indexOf("state=on") >= 0) {
            txStart();
        } else if (reqLine.indexOf("state=off") >= 0) {
            txStop();
        }
        client.println("HTTP/1.1 200 OK");
        client.println("Content-Type: text/plain");
        client.println("Connection: close");
        client.println();
        client.println(txActive ? "TX" : "RX");
    } else if (reqLine.startsWith("GET /toggle")) {
        // 手動デバッグ用（個別チャンネルのトグル）
        int chIdx = reqLine.indexOf("ch=");
        if (chIdx >= 0) {
            int ch = reqLine.substring(chIdx + 3, chIdx + 4).toInt();
            toggleOutput(ch);
        }
        sendRedirectRoot(client);
    } else if (reqLine.startsWith("GET /api/status")) {
        sendStatusJson(client);
    } else {
        sendStatusPage(client);
    }

    delay(1);
    client.stop();
}

// ============================================================
//  setup / loop
// ============================================================

void setup() {
    Serial.begin(115200);
    delay(3000);
    Serial.println("=== W5500_PA_PTT_Control 起動 ===");

    pinMode(PIN_ONBOARD_LED, OUTPUT);
    digitalWrite(PIN_ONBOARD_LED, LOW);

    for (int i = 0; i < 3; i++) {
        pinMode(PIN_OUT[i], OUTPUT);
        applyOutput(i);   // 起動時状態を反映（LNA=ON, PTT/PA=OFF、LED=OFF）
    }

    Ethernet.init(PIN_CS);

    Serial.print("DHCPでIP取得中...");
    if (Ethernet.begin(mac, 15000, 4000) == 0) {
        Serial.println(" 失敗（DHCPサーバー未応答）");
        if (Ethernet.hardwareStatus() == EthernetNoHardware) {
            Serial.println("W5500が検出できません。配線を確認してください。");
        }
    } else {
        Serial.println(" 成功");
    }

    Serial.print("IPアドレス: ");
    Serial.println(Ethernet.localIP());

    server.begin();
    Serial.println("Webサーバー起動 (port 80)");
}

void loop() {
    // リンク状態の監視
    bool nowUp = (Ethernet.linkStatus() != LinkOFF);
    if (nowUp != linkUp) {
        linkUp = nowUp;
        Serial.println(linkUp ? "[LINK] イーサネット接続" : "[LINK] イーサネット切断");
    }

    // DHCPリース更新
    Ethernet.maintain();

    EthernetClient client = server.available();
    if (client) {
        handleClient(client);
    }
}
