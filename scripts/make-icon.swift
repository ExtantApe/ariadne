// Draws apps/desktop/app-icon.png: a ball of thread with one strand leading out. Run: swift scripts/make-icon.swift
import AppKit
let s: CGFloat = 1024
let img = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1024, pixelsHigh: 1024, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: img)
NSColor(red: 0.06, green: 0.46, blue: 0.43, alpha: 1).setFill()
NSBezierPath(roundedRect: NSRect(x: 64, y: 64, width: s - 128, height: s - 128), xRadius: 200, yRadius: 200).fill()
NSColor.white.setStroke()
let c = NSPoint(x: 420, y: 560), r: CGFloat = 190
let ball = NSBezierPath(ovalIn: NSRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r)); ball.lineWidth = 30; ball.stroke()
for (a, f) in [(-35.0, 0.72), (-35.0, 0.36), (35.0, 0.54)] {
    let t = NSAffineTransform(); t.translateX(by: c.x, yBy: c.y); t.rotate(byDegrees: a)
    let e = NSBezierPath(ovalIn: NSRect(x: -r, y: -r * f, width: 2 * r, height: 2 * r * f)); e.lineWidth = 20; e.transform(using: t as AffineTransform); e.stroke()
}
let strand = NSBezierPath(); strand.move(to: NSPoint(x: c.x + r * 0.7, y: c.y - r * 0.7))
strand.curve(to: NSPoint(x: 820, y: 230), controlPoint1: NSPoint(x: 700, y: 180), controlPoint2: NSPoint(x: 640, y: 420))
strand.lineWidth = 30; strand.lineCapStyle = .round; strand.stroke()
NSGraphicsContext.current = nil
try! img.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "apps/desktop/app-icon.png"))
