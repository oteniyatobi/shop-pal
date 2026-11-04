import { useEffect } from 'react'
import { BagIcon, XIcon } from './Icons.jsx'

// Slide-over cart panel. Cart changes go through the agent (as chat messages),
// so the conversation and the server-side cart always stay in sync.
export default function CartDrawer({ open, cart, busy, onClose, onRemove, onCheckout }) {
  // Close on Escape.
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const items = cart?.items || []
  const count = cart?.item_count || 0

  return (
    <>
      <div className={`scrim${open ? ' open' : ''}`} onClick={onClose} />
      <aside className={`drawer${open ? ' open' : ''}`} aria-label="Shopping cart" aria-hidden={!open}>
        <header className="drawer-header">
          <div>
            <h2>Your cart</h2>
            <span className="drawer-sub">{count} {count === 1 ? 'item' : 'items'}</span>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close cart">
            <XIcon />
          </button>
        </header>

        {items.length === 0 ? (
          <div className="drawer-empty">
            <span className="drawer-empty-icon"><BagIcon width={22} height={22} /></span>
            <p>Your cart is empty</p>
            <span>Ask ShopPal to find something you'll love.</span>
          </div>
        ) : (
          <>
            <ul className="drawer-items">
              {items.map((item) => (
                <li key={item.id} className="drawer-item">
                  <div className="line-media"><img src={item.image} alt="" /></div>
                  <div className="line-info">
                    <div className="line-title">{item.title}</div>
                    <div className="line-qty">Qty {item.quantity} · ${item.unit_price}</div>
                    <button className="link-btn" onClick={() => onRemove(item)} disabled={busy}>Remove</button>
                  </div>
                  <div className="line-price">${item.line_total}</div>
                </li>
              ))}
            </ul>
            <footer className="drawer-footer">
              <div className="total-row flush">
                <span>Subtotal</span>
                <strong>${cart.total}</strong>
              </div>
              <button className="primary-btn" onClick={onCheckout} disabled={busy}>
                Check out with PayPal
              </button>
            </footer>
          </>
        )}
      </aside>
    </>
  )
}
