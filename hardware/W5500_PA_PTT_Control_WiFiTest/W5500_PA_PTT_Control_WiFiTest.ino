// ============================================================
//  W5500_PA_PTT_WiFiTest.ino
//  【一時テスト用】W5500(イーサネット)未実装の段階でHTTPロジックだけを
//  検証するためのWiFi APモード版。
//
//  本番ファームウェア
//  (Shonan_Lite-RasPI5/hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino)
//  のGPIO制御・HTTPハンドラ・遅延設定・IP設定のロジックはそのまま踏襲し、
//  通信層のみ Ethernet(W5500) → WiFi(ESP32内蔵AP) に置き換えている。
//  W5500実装後は本番版を使うこと。本ファイルは削除して構わない。
//
//  【使い方】
//  1) 本スケッチを書き込むとESP32がWiFiアクセスポイントになる
//       SSID: PA-PTT-Test / PASS: ptttest123
//       既定IP: 192.168.4.1（/configで変更可）
//  2) MacのWiFi設定で上記SSIDに接続する
//  3) ブラウザで http://<IP>/ にアクセス
//
//  出力（ラッチ式ON/OFF、いずれもactive-HIGH想定。本番と同一）
//  POWER: GPIO 26
//  PTT  : GPIO 27
//
//  対応パス（本番版と同一仕様）:
//    GET /                          ステータスページ
//    GET /toggle?ch=0..1            指定チャンネルをトグルして / へリダイレクト（ON側は遅延あり、OFF側は即時。/chと同一ロジック）
//    GET /tx?state=on|off           PTTのみ切替（on要求は設定ms後にON、offは即時）
//    GET /ch?idx=0|1&state=on|off   個別チャンネル明示ON/OFF（idx0=POWER, idx1=PTT。
//                                   on要求は遅延後にON、offは即時）
//    GET /api/status                JSON形式で現在状態を返す
//    GET /config                                        設定画面(HTML)
//    GET /config/delay?power_delay_sec=3&ptt_delay_ms=50 遅延時間を保存
//    GET /config/network?ip=...&gateway=...&subnet=...   AP自身のIP設定を保存し自動再起動
// ============================================================

#include <WiFi.h>
#include <Preferences.h>

const char* AP_SSID = "PA-PTT-Test";
const char* AP_PASS = "ptttest123";

const int IDX_POWER = 0;
const int IDX_PTT   = 1;

const int PIN_OUT[2] = { 26, 27 };
const char* OUT_LABEL[2] = { "POWER 12V (GPIO26)", "PTT (GPIO27)" };

const int PIN_ONBOARD_LED = 2;

bool outState[2] = { false, false };
bool txActive = false;

Preferences prefs;
const char* PREFS_NS = "w5500cfg";

// --- 可変設定（NVSに保存、既定値） ---
uint32_t powerDelayMs = 3000;   // 12V電源ON要求からONまでの遅延[ms]（既定3秒）
uint32_t pttDelayMs   = 50;     // PTT ON要求からONまでの遅延[ms]（既定50ms）

IPAddress currentIP(192, 168, 4, 1);
IPAddress currentGateway(192, 168, 4, 1);
IPAddress currentSubnet(255, 255, 255, 0);

// --- 遅延実行の保留状態（非ブロッキング） ---
bool pwrOnPending = false;
unsigned long pwrOnRequestAt = 0;

bool pttOnPending = false;
unsigned long pttOnRequestAt = 0;

WiFiServer server(80);

// ============================================================
//  設定の読み書き（NVS）
// ============================================================

void loadConfig() {
    prefs.begin(PREFS_NS, true);
    powerDelayMs = prefs.getULong("pwr_delay_ms", 3000);
    pttDelayMs   = prefs.getULong("ptt_delay_ms", 50);

    String ipStr   = prefs.getString("ip",   "192.168.4.1");
    String gwStr   = prefs.getString("gw",   "192.168.4.1");
    String maskStr = prefs.getString("mask", "255.255.255.0");
    prefs.end();

    if (!currentIP.fromString(ipStr))       currentIP = IPAddress(192, 168, 4, 1);
    if (!currentGateway.fromString(gwStr))  currentGateway = IPAddress(192, 168, 4, 1);
    if (!currentSubnet.fromString(maskStr)) currentSubnet = IPAddress(255, 255, 255, 0);
}

void saveDelayConfig(uint32_t pwrMs, uint32_t pttMs) {
    prefs.begin(PREFS_NS, false);
    prefs.putULong("pwr_delay_ms", pwrMs);
    prefs.putULong("ptt_delay_ms", pttMs);
    prefs.end();
    powerDelayMs = pwrMs;
    pttDelayMs = pttMs;
}

void saveNetworkConfig(const String& ipStr, const String& gwStr, const String& maskStr) {
    prefs.begin(PREFS_NS, false);
    prefs.putString("ip", ipStr);
    prefs.putString("gw", gwStr);
    prefs.putString("mask", maskStr);
    prefs.end();
}

// ============================================================
//  出力制御（本番版と同一ロジック）
// ============================================================

void applyOutput(int idx) {
    digitalWrite(PIN_OUT[idx], outState[idx] ? HIGH : LOW);
    Serial.printf("[OUT] %s -> %s\n", OUT_LABEL[idx], outState[idx] ? "ON" : "OFF");
    if (idx == IDX_PTT) {
        digitalWrite(PIN_ONBOARD_LED, outState[IDX_PTT] ? HIGH : LOW);
    }
}

void setOutput(int idx, bool on) {
    if (idx < 0 || idx > 1) return;
    outState[idx] = on;
    applyOutput(idx);
}

// ============================================================
//  12V電源 / PTT の遅延付き制御（非ブロッキング、本番版と同一ロジック）
// ============================================================

void requestPowerOn() {
    pwrOnPending = true;
    pwrOnRequestAt = millis();
    Serial.printf("[PWR] ON要求受信 -> %lu ms後にON予定\n", (unsigned long)powerDelayMs);
}

void requestPowerOff() {
    pwrOnPending = false;
    setOutput(IDX_POWER, false);
    Serial.println("[PWR] OFF要求受信 -> 即時OFF");
}

void requestPttOn() {
    pttOnPending = true;
    pttOnRequestAt = millis();
    Serial.printf("[PTT] ON要求受信 -> %lu ms後にON予定\n", (unsigned long)pttDelayMs);
}

void requestPttOff() {
    pttOnPending = false;
    setOutput(IDX_PTT, false);
    Serial.println("[PTT] OFF要求受信 -> 即時OFF");
}

void servicePendingOutputs() {
    if (pwrOnPending && (unsigned long)(millis() - pwrOnRequestAt) >= powerDelayMs) {
        pwrOnPending = false;
        setOutput(IDX_POWER, true);
        Serial.println("[PWR] 遅延経過 -> ON");
    }
    if (pttOnPending && (unsigned long)(millis() - pttOnRequestAt) >= pttDelayMs) {
        pttOnPending = false;
        setOutput(IDX_PTT, true);
        Serial.println("[PTT] 遅延経過 -> ON");
    }
}

// ============================================================
//  TX/RX 切替（本番版と同一。12V電源はここでは触らない）
// ============================================================

void txStart() {
    if (txActive) return;
    txActive = true;
    requestPttOn();
    Serial.println("[TX] 送信シーケンス開始");
}

void txStop() {
    if (!txActive) return;
    txActive = false;
    requestPttOff();
    Serial.println("[TX] 受信復帰");
}

// ============================================================
//  クエリパラメータ簡易パーサ（本番版と同一）
// ============================================================

static String extractQuery(const String& line) {
    int qIdx = line.indexOf('?');
    if (qIdx < 0) return String();
    int spIdx = line.indexOf(' ', qIdx);
    return line.substring(qIdx + 1, spIdx > 0 ? spIdx : line.length());
}

bool getQueryStr(const String& line, const String& key, String& outVal) {
    String query = extractQuery(line);
    if (query.length() == 0) return false;
    String pattern = key + "=";
    int pos = query.indexOf(pattern);
    if (pos < 0) return false;
    if (pos > 0 && query.charAt(pos - 1) != '&') return false;
    int start = pos + pattern.length();
    int end = query.indexOf('&', start);
    if (end < 0) end = query.length();
    outVal = query.substring(start, end);
    return true;
}

bool getQueryLong(const String& line, const String& key, long& outVal) {
    String s;
    if (!getQueryStr(line, key, s)) return false;
    outVal = s.toInt();
    return true;
}

// ============================================================
//  HTTPレスポンス補助
// ============================================================

void sendPlain(WiFiClient& client, const String& body) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain; charset=UTF-8");
    client.println("Connection: close");
    client.println();
    client.println(body);
}

void sendRedirect(WiFiClient& client, const char* location) {
    client.println("HTTP/1.1 303 See Other");
    client.print("Location: ");
    client.println(location);
    client.println("Connection: close");
    client.println();
}

// ============================================================
//  HTMLページ
// ============================================================

void sendStatusPage(WiFiClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html; charset=UTF-8");
    client.println("Connection: close");
    client.println();

    client.println("<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>");
    client.println("<meta name='viewport' content='width=device-width,initial-scale=1'>");
    if (pwrOnPending || pttOnPending) {
        client.println("<meta http-equiv='refresh' content='1'>");
    }
    client.println("<title>[TEST] 12V電源/PTT 制御</title>");
    client.println("<style>");
    client.println("body{margin:0;font-family:sans-serif;background:#000;color:#eee;text-align:center;padding-top:30px}");
    client.println("h1{color:#aaa;font-size:1.3em}");
    client.println(".card{display:inline-block;margin:12px;background:#111;border-radius:12px;padding:20px 28px;min-width:180px}");
    client.println(".label{color:#888;font-size:.9em;margin-bottom:10px}");
    client.println(".state{font-size:1.6em;font-weight:bold;margin-bottom:14px}");
    client.println(".on{color:#4c9}.off{color:#c66}.pending{color:#fc6}");
    client.println("a.btn{display:inline-block;padding:10px 26px;border-radius:8px;text-decoration:none;font-size:1em}");
    client.println(".btn-on{background:#1a4;color:#fff}.btn-off{background:#a11;color:#fff}");
    client.println("a.cfg{display:inline-block;margin-top:10px;color:#8cf;text-decoration:none}");
    client.println("</style></head><body>");
    client.println("<h1>&#9889; [WiFiテスト版] 12V電源/PTT 制御</h1>");
    client.print("<p style='font-size:1.1em'>状態: <b style='color:");
    client.print(txActive ? "#f66'>送信中(TX)" : "#6c9'>受信中(RX)");
    client.println("</b></p>");

    for (int i = 0; i < 2; i++) {
        bool pending = (i == IDX_POWER && pwrOnPending) || (i == IDX_PTT && pttOnPending);
        client.print("<div class='card'><div class='label'>");
        client.print(OUT_LABEL[i]);
        client.print("</div><div class='state ");
        if (pending) {
            client.print("pending'>ON待ち");
        } else {
            client.print(outState[i] ? "on'>ON" : "off'>OFF");
        }
        client.print("</div><a class='btn ");
        client.print(outState[i] ? "btn-off" : "btn-on");
        client.print("' href='/toggle?ch=");
        client.print(i);
        client.print("'>");
        client.print(outState[i] ? "OFFにする" : "ONにする");
        client.println("</a></div>");
    }

    client.print("<p style='color:#555;margin-top:10px;font-size:.8em'>IP: ");
    client.print(WiFi.softAPIP());
    client.println("</p>");
    client.println("<div><a class='cfg' href='/config'>&#9881; 遅延時間・IPアドレス設定</a></div>");
    client.println("</body></html>");
}

void sendConfigPage(WiFiClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html; charset=UTF-8");
    client.println("Connection: close");
    client.println();

    client.println("<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>");
    client.println("<meta name='viewport' content='width=device-width,initial-scale=1'>");
    client.println("<title>設定</title>");
    client.println("<style>");
    client.println("body{margin:0;font-family:sans-serif;background:#000;color:#eee;padding:24px}");
    client.println("h1{color:#aaa;font-size:1.2em}");
    client.println("fieldset{border:1px solid #333;border-radius:10px;margin-bottom:20px;padding:16px}");
    client.println("legend{color:#8cf;padding:0 6px}");
    client.println("label{display:block;margin:10px 0 4px;color:#aaa;font-size:.9em}");
    client.println("input{background:#111;border:1px solid #444;color:#eee;border-radius:6px;padding:8px;width:220px}");
    client.println("button{margin-top:14px;padding:10px 22px;border:0;border-radius:8px;background:#1a4;color:#fff;font-size:1em}");
    client.println("a{color:#8cf}");
    client.println("</style></head><body>");
    client.println("<h1>&#9881; 遅延時間・IPアドレス設定</h1>");

    client.println("<form action='/config/delay' method='GET'>");
    client.println("<fieldset><legend>遅延時間</legend>");
    client.print("<label>12V電源 ON 遅延 [秒]（/ch?idx=0&state=on 受信からON実行までの待ち時間）</label>");
    client.print("<input type='number' step='0.1' min='0' name='power_delay_sec' value='");
    client.print(powerDelayMs / 1000.0, 1);
    client.println("'>");
    client.print("<label>PTT ON 遅延 [ms]（/tx?state=on または /ch?idx=1&state=on 受信からON実行までの待ち時間）</label>");
    client.print("<input type='number' step='1' min='0' name='ptt_delay_ms' value='");
    client.print(pttDelayMs);
    client.println("'>");
    client.println("<div><button type='submit'>遅延時間を保存</button></div>");
    client.println("</fieldset></form>");

    client.println("<form action='/config/network' method='GET'>");
    client.println("<fieldset><legend>ネットワーク設定（AP自身のIP。保存後に自動再起動します）</legend>");
    client.print("<label>IPアドレス</label><input type='text' name='ip' value='");
    client.print(currentIP);
    client.println("'>");
    client.print("<label>ゲートウェイ</label><input type='text' name='gateway' value='");
    client.print(currentGateway);
    client.println("'>");
    client.print("<label>サブネットマスク</label><input type='text' name='subnet' value='");
    client.print(currentSubnet);
    client.println("'>");
    client.println("<div><button type='submit'>保存して再起動</button></div>");
    client.println("</fieldset></form>");

    client.println("<p><a href='/'>&larr; ステータス画面へ戻る</a></p>");
    client.println("</body></html>");
}

void sendRestartingPage(WiFiClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html; charset=UTF-8");
    client.println("Connection: close");
    client.println();
    client.println("<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>");
    client.println("<title>再起動中</title></head><body style='font-family:sans-serif;background:#000;color:#eee;text-align:center;padding-top:60px'>");
    client.println("<h1>設定を保存しました</h1><p>新しいIPアドレスで再起動します...</p>");
    client.println("</body></html>");
}

void sendStatusJson(WiFiClient& client) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: application/json");
    client.println("Connection: close");
    client.println();
    client.print("{\"power\":");
    client.print(outState[IDX_POWER] ? "true" : "false");
    client.print(",\"power_pending\":");
    client.print(pwrOnPending ? "true" : "false");
    client.print(",\"ptt\":");
    client.print(outState[IDX_PTT] ? "true" : "false");
    client.print(",\"ptt_pending\":");
    client.print(pttOnPending ? "true" : "false");
    client.print(",\"tx_active\":");
    client.print(txActive ? "true" : "false");
    client.print(",\"power_delay_ms\":");
    client.print(powerDelayMs);
    client.print(",\"ptt_delay_ms\":");
    client.print(pttDelayMs);
    client.print(",\"ip\":\"");
    client.print(WiFi.softAPIP());
    client.println("\"}");
}

// ============================================================
//  HTTPリクエスト処理（本番版と同一の簡易パーサ）
// ============================================================

void handleClient(WiFiClient& client) {
    String reqLine;
    while (client.connected() && client.available() == 0) delay(1);
    if (client.available()) {
        reqLine = client.readStringUntil('\n');
    }
    while (client.connected()) {
        String line = client.readStringUntil('\n');
        if (line == "\r" || line.length() == 0) break;
    }

    Serial.println("[HTTP] " + reqLine);

    if (reqLine.startsWith("GET /tx")) {
        if (reqLine.indexOf("state=on") >= 0) {
            txStart();
        } else if (reqLine.indexOf("state=off") >= 0) {
            txStop();
        }
        sendPlain(client, (outState[IDX_PTT] || pttOnPending) ? "TX" : "RX");

    } else if (reqLine.startsWith("GET /toggle")) {
        // ステータス画面のON/OFFボタン用（/ch と同じ遅延ON・即時OFFロジックを適用）
        long ch = -1;
        if (getQueryLong(reqLine, "ch", ch)) {
            if (ch == IDX_POWER) {
                if (outState[IDX_POWER] || pwrOnPending) requestPowerOff();
                else requestPowerOn();
            } else if (ch == IDX_PTT) {
                if (outState[IDX_PTT] || pttOnPending) requestPttOff();
                else requestPttOn();
            }
        }
        sendRedirect(client, "/");

    } else if (reqLine.startsWith("GET /ch")) {
        long ch = -1;
        getQueryLong(reqLine, "idx", ch);
        if (ch == IDX_POWER) {
            if (reqLine.indexOf("state=on") >= 0) requestPowerOn();
            else if (reqLine.indexOf("state=off") >= 0) requestPowerOff();
        } else if (ch == IDX_PTT) {
            if (reqLine.indexOf("state=on") >= 0) requestPttOn();
            else if (reqLine.indexOf("state=off") >= 0) requestPttOff();
        }
        bool on = (ch == IDX_POWER) ? (outState[IDX_POWER] || pwrOnPending)
                : (ch == IDX_PTT)   ? (outState[IDX_PTT] || pttOnPending)
                : false;
        sendPlain(client, on ? "ON" : "OFF");

    } else if (reqLine.startsWith("GET /config/delay")) {
        String pwrSecStr;
        long pttMs = -1;
        if (getQueryStr(reqLine, "power_delay_sec", pwrSecStr)) {
            float pwrSec = pwrSecStr.toFloat();
            if (pwrSec >= 0) {
                uint32_t newPwrMs = (uint32_t)(pwrSec * 1000.0f + 0.5f);
                uint32_t newPttMs = pttDelayMs;
                if (getQueryLong(reqLine, "ptt_delay_ms", pttMs) && pttMs >= 0) {
                    newPttMs = (uint32_t)pttMs;
                }
                saveDelayConfig(newPwrMs, newPttMs);
            }
        } else if (getQueryLong(reqLine, "ptt_delay_ms", pttMs) && pttMs >= 0) {
            saveDelayConfig(powerDelayMs, (uint32_t)pttMs);
        }
        sendRedirect(client, "/config");

    } else if (reqLine.startsWith("GET /config/network")) {
        String ipStr, gwStr, maskStr;
        IPAddress testIp, testGw, testMask;
        bool ok = getQueryStr(reqLine, "ip", ipStr) && testIp.fromString(ipStr)
               && getQueryStr(reqLine, "gateway", gwStr) && testGw.fromString(gwStr)
               && getQueryStr(reqLine, "subnet", maskStr) && testMask.fromString(maskStr);
        if (ok) {
            saveNetworkConfig(ipStr, gwStr, maskStr);
            sendRestartingPage(client);
            client.flush();
            delay(500);
            client.stop();
            delay(1000);
            ESP.restart();
            return;
        } else {
            sendRedirect(client, "/config");
        }

    } else if (reqLine.startsWith("GET /config")) {
        sendConfigPage(client);

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
    delay(1000);
    Serial.println("=== W5500_PA_PTT_Control [WiFiテスト版] 起動 ===");

    loadConfig();
    Serial.printf("[CFG] 12V電源ON遅延=%lums, PTT ON遅延=%lums\n",
                   (unsigned long)powerDelayMs, (unsigned long)pttDelayMs);

    pinMode(PIN_ONBOARD_LED, OUTPUT);
    digitalWrite(PIN_ONBOARD_LED, LOW);

    for (int i = 0; i < 2; i++) {
        pinMode(PIN_OUT[i], OUTPUT);
        applyOutput(i);
    }

    WiFi.softAPConfig(currentIP, currentGateway, currentSubnet);
    WiFi.softAP(AP_SSID, AP_PASS);
    Serial.print("APモードで起動しました。SSID=");
    Serial.print(AP_SSID);
    Serial.print(" PASS=");
    Serial.println(AP_PASS);
    Serial.print("IPアドレス: ");
    Serial.println(WiFi.softAPIP());

    server.begin();
    Serial.println("Webサーバー起動 (port 80)");
}

void loop() {
    servicePendingOutputs();

    WiFiClient client = server.available();
    if (client) {
        handleClient(client);
    }
}
