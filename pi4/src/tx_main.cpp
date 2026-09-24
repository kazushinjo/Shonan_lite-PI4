// shonan_tx -- Pi4ネイティブDVB-S2 TXブリッジ。
//
// libiioでPluto+を制御するLibiioSession(Tx方向のみ)とDvbs2Session(Tx方向のみ)を
// JNI依存なしのプレーンC++/CLIツールとして実装。定数(txSampleScale=1400.0,
// txQueueMaxBytes=8MB, ブロックサイズ8192×32等)は実機検証済みの値。
//
// aff3ct/dvbs2のdvbs2_txをFIFO越しに駆動し、そのIQサンプル出力をlibiio経由でPluto+の
// AD9361 TXチェーンへ流し込む。標準入力(または --ts-input で指定したファイル/FIFO)から
// MPEG-TSを読み取り、dvbs2_txの入力FIFOへ書き込む(音声・映像はffmpeg等で別途TS化して
// パイプする想定: `ffmpeg ... -f mpegts - | shonan_tx --ts-input -`)。
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <functional>
#include <iostream>
#include <mutex>
#include <random>
#include <set>
#include <string>
#include <sys/stat.h>
#include <sys/time.h>
#include <thread>
#include <unistd.h>
#include <vector>

extern "C" {
#include <iio/iio.h>
}

#include "datv_dvbs2_bridge.h"

namespace {

// dvbs2_conf/{mod,src} に用意されているMODCOD以外を渡すとaff3ctのConstellation_user/BCH
// コードがconf/ファイル欠如でSIGSEGVする(android Dvbs2Constants.ktのホワイトリストと同じ
// 制約)。CLI側で事前に弾く。
const std::set<std::string> kSupportedModCods = {
    "QPSK-S_3/5", "QPSK-S_8/9", "8PSK-S_3/5", "8PSK-S_8/9", "16APSK-S_8/9",
};

std::atomic<bool> g_shutdown_requested{false};

void handleSignal(int) { g_shutdown_requested.store(true); }

void setupWorkingDirectory(const std::string &cwdPath) {
    if (chdir(cwdPath.c_str()) != 0) {
        std::cerr << "[shonan_tx] chdir失敗 errno=" << errno << " path=" << cwdPath << std::endl;
    }
}

std::string makeFifoPath(const std::string &dir, const char *prefix) {
    struct timeval tv{};
    gettimeofday(&tv, nullptr);
    std::random_device rd;
    std::uniform_int_distribution<int> dist(0, 0xFFFFFF);
    char buf[512];
    snprintf(buf, sizeof(buf), "%s/%s_%ld%06ld_%06x.fifo", dir.c_str(), prefix,
             static_cast<long>(tv.tv_sec), static_cast<long>(tv.tv_usec), dist(rd));
    return std::string(buf);
}

// dvbs2_bridge.cpp の LibiioSession のTx専用部分の移植(Rx関連コードは省略)。
class LibiioSession {
 public:
  std::function<void(const std::string &)> onError;

  // ★DVB-S2のRRCフィルタ通過後のピークがRMSの数倍になり得るため、DACフルスケール
  // (2048.0相当)のままだとクリッピング寸前になる。Tx側だけヘッドルームを持たせる
  // (dvbs2_bridge.cpp:114-118と同じ理由、値もAndroid/iOS版から変更していない)。
  float txSampleScale = 1400.0f;
  // ★診断で確認: 2.5Msps複素IQでは8MBは約0.4秒分の余裕しかなく、ffmpeg(カメラ+
  // libx264エンコード)やaff3ct(dvbs2_tx)側のバースト処理による一時的な供給停滞
  // (実測で数百ms～1秒程度)を吸収しきれずstarved=100%に落ちることがあった。
  // 64MBに増量して約3.2秒分の余裕を持たせ、供給側のジッタを吸収できるようにする。
  static constexpr size_t txQueueMaxBytes = 64 * 1024 * 1024;

  std::atomic<bool> isConnected{false};
  std::atomic<bool> isStreaming{false};
  std::atomic<double> lastTxStarvedPercent{0.0};
  std::atomic<double> lastTxDmaRms{0.0};

  LibiioSession() : ringBuffer_(new uint8_t[txQueueMaxBytes]) {}
  ~LibiioSession() { delete[] ringBuffer_; }
  LibiioSession(const LibiioSession &) = delete;
  LibiioSession &operator=(const LibiioSession &) = delete;

  bool connect(const std::string &uri, int maxAttempts = 10) {
    if (ctx_) return true;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      iio_context *context = iio_create_context(nullptr, uri.c_str());
      int err = context ? iio_err(context) : -9999;
      if (context && err == 0) {
        ctx_ = context;
        isConnected = true;
        iio_context_set_timeout(context, 30000);
        return true;
      }
      reportError("Pluto+への接続に失敗しました(uri=" + uri + ", err=" + std::to_string(err) +
                  ", attempt=" + std::to_string(attempt) + "/" + std::to_string(maxAttempts) + ")");
      if (context) iio_context_destroy(context);
      if (attempt < maxAttempts) std::this_thread::sleep_for(std::chrono::seconds(2));
    }
    return false;
  }

  void disconnect() {
    stopStreaming();
    if (stream_) { iio_stream_destroy(stream_); stream_ = nullptr; }
    if (mask_) { iio_channels_mask_destroy(mask_); mask_ = nullptr; }
    if (ctx_) { iio_context_destroy(ctx_); ctx_ = nullptr; }
    device_ = nullptr;
    channelI_ = nullptr;
    channelQ_ = nullptr;
    isConnected = false;
  }

  bool setup(int64_t bandwidthHz, int64_t sampleRateHz, int64_t loHz, const std::string &rfPort,
             double txPowerDb = 0.0) {
    if (!ctx_) { reportError("先にconnectを呼んでください"); return false; }
    iio_device *phy = iio_context_find_device(ctx_, "ad9361-phy");
    if (!phy) { reportError("ad9361-phyデバイスが見つかりません"); return false; }

    // ループバックデバッグ属性は毎回明示的に0へリセットする(実機で不揮発的に残ることを
    // 確認済み、dvbs2_bridge.cpp:186-191と同じ対応)。
    if (const iio_attr *loopbackAttr = iio_device_find_debug_attr(phy, "loopback")) {
      iio_attr_write_string(loopbackAttr, "0");
    }

    iio_channel *phyChan = iio_device_find_channel(phy, "voltage0", /*isOutput=*/true);
    if (!phyChan) { reportError("ad9361-phyのvoltage0チャンネルが見つかりません"); return false; }

    if (const iio_attr *attr = iio_channel_find_attr(phyChan, "rf_port_select")) {
      iio_attr_write_string(attr, rfPort.c_str());
    }
    writeLongLong(phyChan, "rf_bandwidth", bandwidthHz);
    writeLongLong(phyChan, "sampling_frequency", sampleRateHz);
    // AD9361のTX hardwaregainは減衰量(dB)。0.0=最大出力、負値ほど減衰が大きい
    // (GUIのTX Power画面 -70..0dB に対応、既定は最大出力の0.0)。
    if (const iio_attr *attr = iio_channel_find_attr(phyChan, "hardwaregain")) {
      iio_attr_write_double(attr, txPowerDb);
    }

    if (iio_channel *loChan = iio_device_find_channel(phy, "altvoltage1", true)) {
      writeLongLong(loChan, "frequency", loHz);
    }

    iio_device *dev = iio_context_find_device(ctx_, "cf-ad9361-dds-core-lpc");
    if (!dev) { reportError("cf-ad9361-dds-core-lpcデバイスが見つかりません"); return false; }
    device_ = dev;

    // DDSトーン生成器を無効化(実際の変調波形にDDSトーンが混入しないよう、
    // dvbs2_bridge.cpp:231-244と同じ対応)。
    for (const char *ddsChanID : {"altvoltage0", "altvoltage1", "altvoltage2", "altvoltage3"}) {
      iio_channel *ddsChan = iio_device_find_channel(dev, ddsChanID, true);
      if (!ddsChan) continue;
      if (const iio_attr *rawAttr = iio_channel_find_attr(ddsChan, "raw")) iio_attr_write_string(rawAttr, "0");
      if (const iio_attr *scaleAttr = iio_channel_find_attr(ddsChan, "scale")) iio_attr_write_double(scaleAttr, 0.0);
    }

    iio_channel *chI = iio_device_find_channel(dev, "voltage0", true);
    iio_channel *chQ = iio_device_find_channel(dev, "voltage1", true);
    if (!chI || !chQ) { reportError("ストリーミングI/Qチャンネルが見つかりません"); return false; }
    channelI_ = chI;
    channelQ_ = chQ;

    iio_channels_mask *m = iio_create_channels_mask(iio_device_get_channels_count(dev));
    if (!m) { reportError("channels maskの確保に失敗しました"); return false; }
    mask_ = m;
    iio_channel_enable(chI, m);
    iio_channel_enable(chQ, m);

    iio_buffer *buf = iio_device_get_buffer(dev, 0);
    if (!buf) { reportError("バッファの取得に失敗しました"); return false; }

    constexpr size_t blockSize = 8192;
    constexpr size_t nBlocks = 32;
    iio_stream *strm = iio_buffer_create_stream(buf, nBlocks, blockSize, m);
    if (!strm || iio_err(strm) != 0) { reportError("ストリームの作成に失敗しました"); return false; }
    stream_ = strm;
    return true;
  }

  void startStreaming() {
    if (isStreaming.exchange(true)) return;
    streamThread_ = std::thread([this] { txLoop(); });
  }

  void stopStreaming() {
    if (!isStreaming.exchange(false)) return;
    if (stream_) iio_stream_cancel(stream_);
    if (streamThread_.joinable()) streamThread_.join();
  }

  // dvbs2_bridge.cpp:308-311と同じ理由: std::vector::insert/eraseの代わりに固定容量の
  // 生メモリリングバッファを使う(高頻度呼び出しでのO(n)シフトによるRSS増加を避ける)。
  void pushTxIQ(const uint8_t *data, size_t len) {
    std::lock_guard<std::mutex> lock(txQueueMutex_);
    if (len > txQueueMaxBytes) {
      size_t skip = len - txQueueMaxBytes;
      len = txQueueMaxBytes;
      std::memcpy(ringBuffer_, data + skip, len);
      ringReadPos_ = 0;
      ringCount_ = len;
      return;
    }
    if (ringCount_ + len > txQueueMaxBytes) {
      size_t drop = ringCount_ + len - txQueueMaxBytes;
      ringReadPos_ = (ringReadPos_ + drop) % txQueueMaxBytes;
      ringCount_ -= drop;
    }
    size_t writePos = (ringReadPos_ + ringCount_) % txQueueMaxBytes;
    size_t firstChunk = std::min(len, txQueueMaxBytes - writePos);
    std::memcpy(ringBuffer_ + writePos, data, firstChunk);
    if (firstChunk < len) std::memcpy(ringBuffer_, data + firstChunk, len - firstChunk);
    ringCount_ += len;
  }

 private:
  iio_context *ctx_ = nullptr;
  iio_device *device_ = nullptr;
  iio_channel *channelI_ = nullptr;
  iio_channel *channelQ_ = nullptr;
  iio_channels_mask *mask_ = nullptr;
  iio_stream *stream_ = nullptr;
  std::thread streamThread_;

  std::mutex txQueueMutex_;
  uint8_t *ringBuffer_ = nullptr;
  size_t ringReadPos_ = 0;
  size_t ringCount_ = 0;

  void reportError(const std::string &message) { if (onError) onError(message); }

  void writeLongLong(iio_channel *channel, const char *name, int64_t value) {
    const iio_attr *attr = iio_channel_find_attr(channel, name);
    if (!attr) return;
    long long current = 0;
    if (iio_attr_read_longlong(attr, &current) == 0 && current == value) return;
    iio_attr_write_longlong(attr, value);
  }

  void txLoop() {
    while (isStreaming) {
      const iio_block *block = iio_stream_get_next_block(stream_);
      if (!block || iio_err(block) != 0) { reportError("Txブロック取得に失敗しました"); break; }
      void *start = iio_block_first(block, channelI_);
      void *end = iio_block_end(block);
      if (!start || !end) continue;
      size_t byteCount = static_cast<uint8_t *>(end) - static_cast<uint8_t *>(start);
      size_t sampleCount = byteCount / sizeof(int16_t);

      std::vector<float> floats(sampleCount, 0.0f);
      size_t neededBytes = sampleCount * sizeof(float);
      size_t available;
      {
        std::lock_guard<std::mutex> lock(txQueueMutex_);
        available = std::min(neededBytes, ringCount_);
        if (available > 0) {
          auto *dstBytes = reinterpret_cast<uint8_t *>(floats.data());
          size_t firstChunk = std::min(available, txQueueMaxBytes - ringReadPos_);
          std::memcpy(dstBytes, ringBuffer_ + ringReadPos_, firstChunk);
          if (firstChunk < available) std::memcpy(dstBytes + firstChunk, ringBuffer_, available - firstChunk);
          ringReadPos_ = (ringReadPos_ + available) % txQueueMaxBytes;
          ringCount_ -= available;
        }
      }
      size_t starvedSamples = sampleCount - (available / sizeof(float));

      auto *dst = static_cast<int16_t *>(start);
      double sumSq = 0;
      int16_t maxAbs = 0;
      for (size_t i = 0; i < sampleCount; i++) {
        float scaled = floats[i] * txSampleScale;
        if (scaled > 32767.0f) scaled = 32767.0f;
        if (scaled < -32768.0f) scaled = -32768.0f;
        dst[i] = static_cast<int16_t>(scaled);
        sumSq += static_cast<double>(dst[i]) * dst[i];
        maxAbs = std::max(maxAbs, static_cast<int16_t>(std::abs(dst[i])));
      }
      if (sampleCount > 0) lastTxDmaRms = std::sqrt(sumSq / static_cast<double>(sampleCount));
      double starvedPct = sampleCount > 0
          ? (100.0 * static_cast<double>(starvedSamples) / static_cast<double>(sampleCount)) : 0.0;
      lastTxStarvedPercent = starvedPct;
    }
  }
};

// dvbs2_bridge.cpp の Dvbs2Session のTx専用部分の移植。
struct TxSession {
  std::string modCod = "QPSK-S_3/5";
  std::string tmpDir;
  std::string runtimeDir; // conf/ の親ディレクトリ(cwd/がこの下に作られる)
  std::string inputFifoPath;
  std::string outputFifoPath;
  int inputWriteFd = -1;
  std::thread runThread;
  std::thread openInputThread;
  std::thread outputReadThread;
  std::atomic<bool> running{false};

  LibiioSession libiio;

  bool prepare(const std::string &plutoUri, int64_t bandwidthHz, int64_t sampleRateHz, int64_t loHz,
               const std::string &rfPort, double txPowerDb) {
    inputFifoPath = makeFifoPath(tmpDir, "shonan_tx_in");
    outputFifoPath = makeFifoPath(tmpDir, "shonan_tx_out");
    ::unlink(inputFifoPath.c_str());
    ::unlink(outputFifoPath.c_str());
    if (mkfifo(inputFifoPath.c_str(), 0600) != 0 || mkfifo(outputFifoPath.c_str(), 0600) != 0) {
      std::cerr << "[shonan_tx] FIFO作成に失敗しました(errno=" << errno << ")" << std::endl;
      return false;
    }

    libiio.onError = [](const std::string &msg) { std::cerr << "[shonan_tx] libiio: " << msg << std::endl; };

    if (!libiio.connect(plutoUri)) return false;
    if (!libiio.setup(bandwidthHz, sampleRateHz, loHz, rfPort, txPowerDb)) {
      libiio.disconnect();
      return false;
    }
    return true;
  }

  void beginStreaming() {
    if (running.exchange(true)) return;

    libiio.startStreaming();
    runThread = std::thread([this] { runTx(); });
    // dvbs2_tx側は入力FIFOのreaderとして自分でopenする。POSIX FIFOはreader/writer双方が
    // openするまでopen(2)がブロックするため、writer側(こちら)も別スレッドで非同期に開く
    // (dvbs2_bridge.cpp:554-563と同じ理由。これを忘れるとdvbs2_tx側のopen(2)が永遠に
    // ブロックしTXが開始しない)。
    openInputThread = std::thread([this] {
      inputWriteFd = ::open(inputFifoPath.c_str(), O_WRONLY);
      if (inputWriteFd < 0) std::cerr << "[shonan_tx] 入力FIFOのopenに失敗しました" << std::endl;
    });
    outputReadThread = std::thread([this] { readOutputLoopTx(); });
  }

  // TSデータを入力FIFOへ書き込む(呼び出し元は標準入力/ファイルから読んだTSを渡す)。
  void write(const uint8_t *data, size_t len) {
    if (!running || inputWriteFd < 0) return;
    ssize_t n = ::write(inputWriteFd, data, len);
    (void)n; // stop()と競合した際に発生しうるが、書き込み側は既に停止処理中なので無視してよい
  }

  void stop() {
    if (!running.exchange(false)) return;

    // ★実機検証で、libiioのUSBバックエンド(iio_stream_cancel)がまれにストリーム
    // キャンセルに応答せずstopStreaming()内でハングする事象を確認した(USB転送の
    // タイムアウト競合と思われる、dvbs2_bridge.cpp:760-773のコメントにある既知の
    // libiio不具合と同系統)。Linuxではプロセス単位の強制終了が可能なので、
    // 一定時間で終わらない場合はwatchdogでプロセスごと終了させ、電波を出しっぱなしに
    // しない(停止処理の一部がハングしてもRF送信自体はlibiio.stopStreamingへ到達済み
    // なのでハード的には止まっているはずだが、念のため確実に終了させる)。
    std::thread watchdog([] {
      std::this_thread::sleep_for(std::chrono::seconds(10));
      std::cerr << "[shonan_tx] stop()が10秒以内に完了しませんでした。強制終了します。" << std::endl;
      std::_Exit(1);
    });
    watchdog.detach();

    datv_dvbs2_tx_request_stop();
    if (inputWriteFd >= 0) { ::close(inputWriteFd); inputWriteFd = -1; }
    libiio.stopStreaming();
    libiio.disconnect();
    if (runThread.joinable()) runThread.join();
    if (openInputThread.joinable()) openInputThread.join();
    if (outputReadThread.joinable()) outputReadThread.join();
    if (!inputFifoPath.empty()) ::unlink(inputFifoPath.c_str());
    if (!outputFifoPath.empty()) ::unlink(outputFifoPath.c_str());
  }

 private:
  void runTx() {
    setupWorkingDirectory(runtimeDir + "/cwd");

    std::vector<std::string> argStrings = {
        "dvbs2_tx", "--mod-cod", modCod,
        "--src-type", "USER_BIN", "--src-path", inputFifoPath, "--src-fifo",
        "--rad-type", "USER_BIN", "--rad-tx-file-path", outputFifoPath,
        "--tx-time-limit", "0",
    };
    std::vector<char *> argv;
    for (auto &s : argStrings) argv.push_back(const_cast<char *>(s.c_str()));

    int result = datv_dvbs2_tx_run(static_cast<int>(argv.size()), argv.data());
    if (result != 0) std::cerr << "[shonan_tx] datv_dvbs2_tx_run異常終了(code=" << result << ")" << std::endl;
  }

  // dvbs2_bridge.cpp:672-692と同じ理由でread()の戻り値のみをループ条件にする(runningで
  // 早期にfdを閉じるとdvbs2_tx側がwriter-without-readerで例外を投げる)。
  void readOutputLoopTx() {
    int fd = ::open(outputFifoPath.c_str(), O_RDONLY);
    if (fd < 0) { std::cerr << "[shonan_tx] 出力FIFOのopenに失敗しました" << std::endl; return; }
    std::vector<uint8_t> buf(65536);
    while (true) {
      ssize_t n = ::read(fd, buf.data(), buf.size());
      if (n <= 0) break;
      if (running) libiio.pushTxIQ(buf.data(), static_cast<size_t>(n));
    }
    ::close(fd);
  }
};

struct Args {
  // ★USBバックエンドは同一デバイスへ1プロセスしか接続できない(libusbのインターフェース
  // 排他制御)ため、TXとRXを別プロセスで同時に動かせない。Pluto+はUSB接続時もCDC-ECM
  // 仮想ネットワークインターフェース(既定IP 192.168.2.1)を持ち、そちらは内蔵iiodが
  // 複数クライアントを裁くため、TX/RX同時実行が可能(Android/iOS版と同じ"ip:"方式)。
  std::string plutoUri = "ip:192.168.0.136";
  int64_t loHz = 437000000;
  int64_t bandwidthHz = 2000000;
  int64_t sampleRateHz = 2500000;
  std::string modCod = "QPSK-S_3/5";
  std::string rfPort = "A_BALANCED";
  std::string tmpDir = "/tmp";
  std::string runtimeDir; // conf/の親(必須)
  std::string tsInput = "-"; // "-" = stdin
  int statusIntervalSec = 1;
  double txPowerDb = 0.0; // AD9361 TX減衰量(dB)。0.0=最大出力、範囲-70..0
};

void printUsage(const char *prog) {
  std::cerr <<
      "Usage: " << prog << " --runtime-dir <dir containing conf/> [options]\n"
      "  --pluto-uri <uri>       libiio URI (default: ip:192.168.0.136)\n"
      "  --lo-hz <hz>            TX LO周波数 (default: 437000000)\n"
      "  --bandwidth-hz <hz>     RF帯域幅 (default: 2000000)\n"
      "  --sample-rate-hz <hz>   サンプルレート (default: 2500000)\n"
      "  --mod-cod <modcod>      QPSK-S_3/5 | QPSK-S_8/9 | 8PSK-S_3/5 | 8PSK-S_8/9 | 16APSK-S_8/9\n"
      "  --rf-port <port>        (default: A_BALANCED)\n"
      "  --tmp-dir <dir>         FIFO作成先 (default: /tmp)\n"
      "  --runtime-dir <dir>     conf/ の親ディレクトリ(必須。cwd/ をこの下に作成する)\n"
      "  --ts-input <path|->     入力MPEG-TS (default: - = 標準入力)\n"
      "  --tx-power-db <db>      TX減衰量、0.0=最大出力 (default: 0.0, 範囲-70..0)\n";
}

bool parseArgs(int argc, char **argv, Args *out) {
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    auto next = [&](const char *name) -> std::string {
      if (i + 1 >= argc) { std::cerr << "[shonan_tx] " << name << " に値がありません" << std::endl; exit(1); }
      return argv[++i];
    };
    if (a == "--pluto-uri") out->plutoUri = next("--pluto-uri");
    else if (a == "--lo-hz") out->loHz = std::stoll(next("--lo-hz"));
    else if (a == "--bandwidth-hz") out->bandwidthHz = std::stoll(next("--bandwidth-hz"));
    else if (a == "--sample-rate-hz") out->sampleRateHz = std::stoll(next("--sample-rate-hz"));
    else if (a == "--mod-cod") out->modCod = next("--mod-cod");
    else if (a == "--rf-port") out->rfPort = next("--rf-port");
    else if (a == "--tx-power-db") out->txPowerDb = std::stod(next("--tx-power-db"));
    else if (a == "--tmp-dir") out->tmpDir = next("--tmp-dir");
    else if (a == "--runtime-dir") out->runtimeDir = next("--runtime-dir");
    else if (a == "--ts-input") out->tsInput = next("--ts-input");
    else if (a == "-h" || a == "--help") { printUsage(argv[0]); exit(0); }
    else { std::cerr << "[shonan_tx] 不明な引数: " << a << std::endl; printUsage(argv[0]); exit(1); }
  }
  if (out->runtimeDir.empty()) { std::cerr << "[shonan_tx] --runtime-dir は必須です" << std::endl; return false; }
  if (kSupportedModCods.find(out->modCod) == kSupportedModCods.end()) {
    std::cerr << "[shonan_tx] 未対応のmod-cod: " << out->modCod
              << " (conf/ファイル欠如でSIGSEGVするため拒否)" << std::endl;
    return false;
  }
  return true;
}

} // namespace

int main(int argc, char **argv) {
  Args args;
  if (!parseArgs(argc, argv, &args)) { printUsage(argv[0]); return 1; }

  std::signal(SIGINT, handleSignal);
  std::signal(SIGTERM, handleSignal);

  TxSession session;
  session.modCod = args.modCod;
  session.tmpDir = args.tmpDir;
  session.runtimeDir = args.runtimeDir;

  std::cerr << "[shonan_tx] Pluto+へ接続中 (" << args.plutoUri << ")..." << std::endl;
  if (!session.prepare(args.plutoUri, args.bandwidthHz, args.sampleRateHz, args.loHz, args.rfPort,
                        args.txPowerDb)) {
    std::cerr << "[shonan_tx] 準備に失敗しました" << std::endl;
    return 1;
  }
  std::cerr << "[shonan_tx] TX開始 mod-cod=" << args.modCod << " lo=" << args.loHz
            << "Hz bw=" << args.bandwidthHz << "Hz sr=" << args.sampleRateHz << "Hz" << std::endl;
  session.beginStreaming();

  FILE *in = stdin;
  bool closeIn = false;
  if (args.tsInput != "-") {
    in = fopen(args.tsInput.c_str(), "rb");
    if (!in) {
      std::cerr << "[shonan_tx] --ts-input を開けません: " << args.tsInput << std::endl;
      session.stop();
      return 1;
    }
    closeIn = true;
  }

  std::thread statusThread([&] {
    while (!g_shutdown_requested.load()) {
      std::this_thread::sleep_for(std::chrono::seconds(args.statusIntervalSec));
      if (g_shutdown_requested.load()) break;
      std::cerr << "[shonan_tx] starved=" << session.libiio.lastTxStarvedPercent.load()
                << "% dmaRms=" << session.libiio.lastTxDmaRms.load() << std::endl;
    }
  });

  std::vector<uint8_t> buf(65536);
  while (!g_shutdown_requested.load()) {
    size_t n = fread(buf.data(), 1, buf.size(), in);
    if (n > 0) session.write(buf.data(), n);
    if (n == 0) {
      if (feof(in)) break;
      if (ferror(in)) { std::cerr << "[shonan_tx] --ts-input 読み取りエラー" << std::endl; break; }
    }
  }

  g_shutdown_requested.store(true);
  if (statusThread.joinable()) statusThread.join();
  if (closeIn) fclose(in);

  std::cerr << "[shonan_tx] 停止中..." << std::endl;
  session.stop();
  std::cerr << "[shonan_tx] 終了しました" << std::endl;
  return 0;
}
