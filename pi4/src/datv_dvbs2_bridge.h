#ifndef datv_dvbs2_bridge_h
#define datv_dvbs2_bridge_h

/*
 * dvbs2_tx_lib.cppの実体はaff3ct/streampuのC++型を使うため不透明だが、この関数シグネチャ
 * 自体はC型のみを露出するのでtx_main.cppから直接呼べる。
 *
 * 呼び出し側(tx_main.cpp)はバックグラウンドスレッドでこの関数をブロッキング呼び出しすること。
 * argv形式でdvbs2_txコマンドライン相当の引数(--mod-cod, --src-type USER_BIN,
 * --src-path <入力FIFO>, --src-fifo, --rad-type USER_BIN, --rad-tx-file-path <出力FIFO>,
 * --tx-time-limit 等)を渡す。
 */

#ifdef __cplusplus
extern "C" {
#endif

int datv_dvbs2_tx_run(int argc, char** argv);

/* datv_dvbs2_tx_runはブロッキング実行され、呼び出し側からは外部フラグでしか
 * 停止を要求できない(FIFOを閉じるだけでは内部の実行ループが止まらずCPU/メモリを
 * 消費し続ける事象をAndroid/iOS実機で確認済み、DVBS2_iOS_Port_PoC.md参照)。
 * stop()の際、FIFOハンドルを閉じる前にこれを呼ぶこと。 */
void datv_dvbs2_tx_request_stop(void);

#ifdef __cplusplus
}
#endif

#endif /* datv_dvbs2_bridge_h */
