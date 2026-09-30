// HTMLファイルをA4のPDFにする(build_docs.pyから呼ばれる)。
// 使い方: swift html2pdf.swift <入力.html> <出力.pdf>
import AppKit

let args = CommandLine.arguments
let data = try! Data(contentsOf: URL(fileURLWithPath: args[1]))
let attr = try! NSAttributedString(
    data: data,
    options: [.documentType: NSAttributedString.DocumentType.html,
              .characterEncoding: String.Encoding.utf8.rawValue],
    documentAttributes: nil)
let paper = NSSize(width: 595, height: 842)  // A4(pt)
let margin: CGFloat = 48
let width = paper.width - margin * 2

// ★本文の実際の高さに合わせたビューで印刷する(固定の高さだと末尾に白紙ページが付く)。
let tv = NSTextView(frame: NSRect(x: 0, y: 0, width: width, height: 10))
tv.isVerticallyResizable = true
tv.textContainer?.widthTracksTextView = true
tv.textStorage?.setAttributedString(attr)
tv.layoutManager?.ensureLayout(for: tv.textContainer!)
let used = tv.layoutManager!.usedRect(for: tv.textContainer!)
tv.setFrameSize(NSSize(width: width, height: ceil(used.height) + 4))

let info = NSPrintInfo()
info.paperSize = paper
info.topMargin = margin; info.bottomMargin = margin
info.leftMargin = margin; info.rightMargin = margin
info.horizontalPagination = .fit
info.verticalPagination = .automatic
info.jobDisposition = .save
info.dictionary()[NSPrintInfo.AttributeKey.jobSavingURL] = URL(fileURLWithPath: args[2])
let op = NSPrintOperation(view: tv, printInfo: info)
op.showsPrintPanel = false
op.showsProgressPanel = false
op.run()
