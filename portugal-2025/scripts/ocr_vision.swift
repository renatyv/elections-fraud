// OCR PDF-сканов через Apple Vision (macOS встроенный).
// Использование: ocr_vision <file.pdf> [scale]
// Печает текст с примерным сохранением раскладки (колоночные позиции),
// страницы разделены строкой === PAGE n ===.
import Foundation
import PDFKit
import AppKit
import Vision

struct Tok {
    let text: String
    let x: CGFloat   // нормализованный левый край (0..1)
    let yMid: CGFloat
    let h: CGFloat
}

func ocrPage(_ page: PDFPage, scale: CGFloat) throws -> [Tok] {
    let r = page.bounds(for: .mediaBox)
    let w = Int(ceil(r.width * scale)), h = Int(ceil(r.height * scale))
    guard w > 0, h > 0, w < 20000, h < 20000 else { return [] }
    let img = NSImage(size: NSSize(width: CGFloat(w), height: CGFloat(h)))
    img.lockFocus()
    guard let ctx = NSGraphicsContext.current?.cgContext else {
        img.unlockFocus()
        return []
    }
    ctx.interpolationQuality = .high
    ctx.translateBy(x: 0, y: 0)
    page.draw(with: .mediaBox, to: ctx)
    img.unlockFocus()
    guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return [] }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    if #available(macOS 13, *) {
        let langs = try? VNRecognizeTextRequest.supportedRecognitionLanguages(for: .accurate, revision: req.revision)
        let pref = ["pt-PT", "pt-BR", "en-US"].filter { langs?.contains($0) ?? false }
        if !pref.isEmpty { req.recognitionLanguages = pref }
    }
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try handler.perform([req])
    var out: [Tok] = []
    for obs in (req.results ?? []) {
        guard let cand = obs.topCandidates(1).first else { continue }
        let bb = obs.boundingBox
        out.append(Tok(text: cand.string, x: bb.minX, yMid: bb.midY, h: bb.height))
    }
    return out
}

// группировка токенов в строки по y
func renderLines(_ toks: [Tok], widthChars: Int) -> String {
    guard !toks.isEmpty else { return "" }
    let sorted = toks.sorted { $0.yMid > $1.yMid }
    var lines: [[Tok]] = []
    var cur: [Tok] = [sorted[0]]
    let medH = sorted.map { Double($0.h) }.sorted()[sorted.count / 2]
    for t in sorted.dropFirst() {
        let ref = cur.last!
        if abs(Double(t.yMid - ref.yMid)) < max(0.006, Double(ref.h) * 0.55 + Double(t.h) * 0.0) + medH * 0.2 {
            cur.append(t)
        } else {
            lines.append(cur)
            cur = [t]
        }
    }
    lines.append(cur)
    var out: [String] = []
    for line in lines {
        let toks = line.sorted { $0.x < $1.x }
        var s = "", pos = 0
        for t in toks {
            let col = Int((t.x * CGFloat(widthChars)).rounded())
            let target = max(pos + 1, col)
            s += String(repeating: " ", count: target - pos) + t.text
            pos = target + t.text.count
        }
        if !s.trimmingCharacters(in: .whitespaces).isEmpty {
            out.append(String(s.drop(while: { $0 == " " })))
        }
    }
    return out.joined(separator: "\n")
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: ocr_vision <pdf|png|jpg> [scale]\n".data(using: .utf8)!)
    exit(2)
}
let path = args[1]
let scale: CGFloat = args.count >= 3 ? CGFloat(Double(args[2]) ?? 2.5) : 2.5

func toksFromCG(_ cg: CGImage) -> [Tok] {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    var out: [Tok] = []
    for obs in (req.results ?? []) {
        guard let cand = obs.topCandidates(1).first else { continue }
        let bb = obs.boundingBox
        out.append(Tok(text: cand.string, x: bb.minX, yMid: bb.midY, h: bb.height))
    }
    return out
}

var all: [String] = []
if path.lowercased().hasSuffix(".pdf") {
    guard let doc = PDFDocument(url: URL(fileURLWithPath: path)) else {
        FileHandle.standardError.write("cannot open \(path)\n".data(using: .utf8)!)
        exit(1)
    }
    for i in 0..<doc.pageCount {
        guard let page = doc.page(at: i) else { continue }
        let toks = (try? ocrPage(page, scale: scale)) ?? []
        all.append("=== PAGE \(i + 1) ===")
        all.append(renderLines(toks, widthChars: 150))
    }
} else {
    // растровый файл (PNG/JPG): отдаём как есть Vision
    guard let ns = NSImage(contentsOfFile: path),
          let cg = ns.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("cannot open image \(path)\n".data(using: .utf8)!)
        exit(1)
    }
    let flipped = cg // Vision boundingBox: y снизу; CGImage через VNImageRequestHandler(cgImage:) тоже снизу — ок
    all.append("=== PAGE 1 ===")
    all.append(renderLines(toksFromCG(flipped), widthChars: 150))
}
print(all.joined(separator: "\n"))
