# shonan-pi4 ネイティブTXブリッジのビルド定義。
#
# 依存ライブラリ(aff3ct/dvbs2, streampu, cpptrace, libiio, zstd, libxml2)は
# ~/shonan-pi4-native-build/build_dvbs2_deps_native.sh で事前にビルド・インストール
# 済みであることを前提とする。インストール先は -DDVBS2_DEPS_DIR=<path> で指定
# (デフォルトは $ENV{HOME}/shonan-pi4-native-build/dvbs2-deps-install-native-aarch64)。
#
# コンパイルフラグ(定義・C++標準)はaff3ct/dvbs2自体のビルド(dvbs2_tx.dir/flags.make)
# から抽出した値をそのまま踏襲している -- aff3ct.hpp/streampu.hppはこれらのマクロに
# よってヘッダの中身が変わるため、勝手に変えるとABI不整合でクラッシュする。
cmake_minimum_required(VERSION 3.18)
project(shonan_pi4_tx CXX)

if(NOT DVBS2_DEPS_DIR)
  set(DVBS2_DEPS_DIR "$ENV{HOME}/shonan-pi4-native-build/dvbs2-deps-install-native-aarch64")
endif()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(shonan_tx
  src/tx_main.cpp
  src/dvbs2_tx_lib.cpp
)

target_include_directories(shonan_tx PRIVATE
  src
  ${DVBS2_DEPS_DIR}/include
)

# dvbs2_tx.dir/flags.make の CXX_DEFINES をそのまま踏襲(aff3ct/streampu/cpptraceの
# 静的ライブラリ自体がこれらのマクロ有効でビルドされているため、ヘッダ側で不一致だと
# ABI不整合を起こす)。
target_compile_definitions(shonan_tx PRIVATE
  AFF3CT_EXT_STRINGS
  AFF3CT_MULTI_PREC
  AFF3CT_POLAR_BIT_PACKING
  CPPTRACE_ADDR2LINE_PATH="/usr/bin/addr2line"
  CPPTRACE_DEMANGLE_WITH_CXXABI
  CPPTRACE_GET_SYMBOLS_WITH_ADDR2LINE
  CPPTRACE_HAS_CXX_EXCEPTION_TYPE
  CPPTRACE_HAS_DL_FIND_OBJECT
  CPPTRACE_STATIC_DEFINE
  CPPTRACE_UNWIND_WITH_UNWIND
  MIPP_ENABLE_BACKTRACE
  SPU_COLORS
  SPU_STACKTRACE
)

target_compile_options(shonan_tx PRIVATE -O3 -DNDEBUG)

target_link_libraries(shonan_tx PRIVATE
  ${DVBS2_DEPS_DIR}/lib/libdvbs2_common.a
  ${DVBS2_DEPS_DIR}/lib/libaff3ct-4.0.0.a
  ${DVBS2_DEPS_DIR}/lib/libstreampu.a
  ${DVBS2_DEPS_DIR}/lib/libcpptrace.a
  ${DVBS2_DEPS_DIR}/lib/libiio.a
  ${DVBS2_DEPS_DIR}/lib/libiiod-responder.a
  ${DVBS2_DEPS_DIR}/lib/libxml2.a
  ${DVBS2_DEPS_DIR}/lib/libzstd.a
  usb-1.0
  dl
  pthread
)
