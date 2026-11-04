// Ariadne's icons. Ivory on red ochre: the color of Minoan frescoes at Knossos, and of her thread.
// Run from the repo root: swift scripts/make-icon.swift, then pnpm --filter ariadne-desktop icons
import AppKit
let ivory = NSColor(red: 0.953, green: 0.918, blue: 0.839, alpha: 1)
let ochre = (NSColor(red: 0.620, green: 0.200, blue: 0.137, alpha: 1), NSColor(red: 0.463, green: 0.133, blue: 0.094, alpha: 1))
func canvas(_ px: Int, _ draw: () -> Void) -> NSBitmapImageRep {
  let r = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: r)
  let t = NSAffineTransform(); t.scale(by: CGFloat(px) / 1024); t.concat()
  NSColor.clear.set(); NSRect(x: 0, y: 0, width: 1024, height: 1024).fill(using: .copy)
  draw(); NSGraphicsContext.current = nil; return r
}
func tile(_ c: (NSColor, NSColor)) {
  let p = NSBezierPath(roundedRect: NSRect(x: 100, y: 100, width: 824, height: 824), xRadius: 185, yRadius: 185)
  NSGradient(starting: c.0, ending: c.1)!.draw(in: p, angle: -90)
}
// Ariadne: the classical Cretan labyrinth, grown from the ancient seed: a cross and four dots, joined by one arc after another.
func labyrinth(_ color: NSColor, width w: CGFloat, unit u: CGFloat = 80) {
  NSGraphicsContext.saveGraphicsState()
  color.setStroke()
  let cx = 512 - 0.5 * u, cy = 512 - 1.25 * u
  func P(_ x: CGFloat, _ y: CGFloat) -> NSPoint { NSPoint(x: cx + x * u, y: cy + y * u) }
  func stroke(_ p: NSBezierPath) { p.lineWidth = w; p.lineCapStyle = .round; p.lineJoinStyle = .round; p.stroke() }
  let C = P(0.5, 1)  // all the arcs share this center
  // the cross
  let cross = NSBezierPath(); cross.move(to: P(0, -1)); cross.line(to: P(0, 1)); cross.move(to: P(-2, 0)); cross.line(to: P(2, 0)); stroke(cross)
  // top of cross → top right dot
  var p = NSBezierPath(); p.move(to: P(0, 1)); p.appendArc(withCenter: C, radius: 0.5 * u, startAngle: 180, endAngle: 0, clockwise: true); stroke(p)
  // top left dot → right arm
  p = NSBezierPath(); p.move(to: P(-1, 1)); p.appendArc(withCenter: C, radius: 1.5 * u, startAngle: 180, endAngle: 0, clockwise: true); p.line(to: P(2, 0)); stroke(p)
  // left arm → bottom right dot
  p = NSBezierPath(); p.move(to: P(-2, 0)); p.line(to: P(-2, 1)); p.appendArc(withCenter: C, radius: 2.5 * u, startAngle: 180, endAngle: 0, clockwise: true)
  p.appendArc(from: P(3, -1), to: P(1, -1), radius: 0.5 * u); p.line(to: P(1, -1)); stroke(p)
  // bottom left dot → all the way round → foot of the cross. The way in is the gap between these two ends.
  p = NSBezierPath(); p.move(to: P(-1, -1)); p.appendArc(from: P(-3, -1), to: P(-3, 1), radius: 0.5 * u); p.line(to: P(-3, 1))
  p.appendArc(withCenter: C, radius: 3.5 * u, startAngle: 180, endAngle: 0, clockwise: true)
  p.appendArc(from: P(4, -2), to: P(0, -2), radius: 1 * u); p.appendArc(from: P(0, -2), to: P(0, -1), radius: 0.4 * u); p.line(to: P(0, -1)); stroke(p)
  NSGraphicsContext.restoreGraphicsState()
}
func save(_ r: NSBitmapImageRep, _ p: String) { try! r.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: p)) }
save(canvas(1024) { tile(ochre); labyrinth(ivory, width: 26) }, "apps/desktop/app-icon.png")
save(canvas(44) { labyrinth(.black, width: 48, unit: 118) }, "apps/desktop/src-tauri/icons/tray.png")
