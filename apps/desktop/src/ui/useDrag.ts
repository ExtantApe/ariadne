import type { PointerEvent as ReactPointerEvent } from 'react'

/**
 * Drag a row to another place, shared by Theseus and Ariadne. Rows carry data-drag-id; the lists they can land in carry data-drop-group.
 * Pointer events rather than HTML drag and drop, so it behaves the same in the app's web view and can't be mistaken for a file drop.
 * Escape cancels. Clicks on buttons and fields inside a row stay clicks.
 */
export type DropTarget = { group: string; before: string | null }

export function startRowDrag(e: ReactPointerEvent, id: string, label: string, onDrop: (target: DropTarget) => void) {
  if (e.button !== 0) return
  if ((e.target as HTMLElement).closest('button, input, textarea, a, summary input, [data-no-drag]')) return
  const x0 = e.clientX
  const y0 = e.clientY
  const source = e.currentTarget as HTMLElement
  const scroller = source.closest('.main') as HTMLElement | null
  let ghost: HTMLDivElement | null = null
  let marker: HTMLDivElement | null = null
  let target: DropTarget | null = null
  let lastY = y0
  let timer = 0

  const stop = () => {
    document.removeEventListener('pointermove', move)
    document.removeEventListener('pointerup', up)
    document.removeEventListener('keydown', key)
    window.clearInterval(timer)
    ghost?.remove()
    marker?.remove()
    source.classList.remove('dragging')
    document.body.classList.remove('is-dragging')
    document.querySelectorAll('.drop-hover').forEach((n) => n.classList.remove('drop-hover'))
  }

  const aim = (x: number, y: number) => {
    document.querySelectorAll('.drop-hover').forEach((n) => n.classList.remove('drop-hover'))
    target = null
    if (marker) marker.style.display = 'none'
    const under = document.elementFromPoint(x, y)
    const groupEl = under?.closest('[data-drop-group]') as HTMLElement | null
    if (!groupEl) return
    const group = groupEl.dataset.dropGroup!
    const rows = [...groupEl.querySelectorAll<HTMLElement>('[data-drag-id]')]
    const others = rows.filter((r) => r !== source)
    const next = others.find((r) => {
      const b = r.getBoundingClientRect()
      return y < b.top + b.height / 2
    })
    target = { group, before: next?.dataset.dragId ?? null }
    groupEl.classList.add('drop-hover')
    const edge = next ?? others[others.length - 1]
    if (edge && marker) {
      const b = edge.getBoundingClientRect()
      marker.style.cssText = `display:block;left:${b.left}px;width:${b.width}px;top:${(next ? b.top : b.bottom) - 1}px`
    }
  }

  const move = (ev: PointerEvent) => {
    if (!ghost) {
      if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < 5) return
      ghost = document.createElement('div')
      ghost.className = 'drag-ghost'
      ghost.textContent = label
      marker = document.createElement('div')
      marker.className = 'drop-line'
      document.body.append(ghost, marker)
      source.classList.add('dragging')
      document.body.classList.add('is-dragging')
      // Near the top or bottom edge, keep scrolling.
      timer = window.setInterval(() => {
        if (!scroller) return
        const b = scroller.getBoundingClientRect()
        if (lastY < b.top + 44) scroller.scrollBy(0, -14)
        else if (lastY > b.bottom - 44) scroller.scrollBy(0, 14)
      }, 30)
    }
    lastY = ev.clientY
    ghost.style.transform = `translate(${ev.clientX + 10}px, ${ev.clientY + 6}px)`
    aim(ev.clientX, ev.clientY)
  }
  const up = () => {
    const dragged = !!ghost
    const t = target
    stop()
    if (dragged && t) onDrop(t)
  }
  const key = (ev: KeyboardEvent) => {
    if (ev.key === 'Escape') stop()
  }
  document.addEventListener('pointermove', move)
  document.addEventListener('pointerup', up)
  document.addEventListener('keydown', key)
}
