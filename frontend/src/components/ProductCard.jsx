import { CheckIcon, PlusIcon, StarIcon } from './Icons.jsx'

// A single product result rendered inline in the chat.
export default function ProductCard({ product, index, inCart, disabled, onAdd }) {
  const { title, price, image, category, rating, rating_count } = product

  return (
    <article className="product">
      <div className="product-media">
        <img src={image} alt={title} loading="lazy" />
        <span className="product-index">{index}</span>
      </div>
      <div className="product-body">
        <span className="product-category">{category}</span>
        <h3 className="product-title" title={title}>{title}</h3>
        {rating != null && (
          <span className="rating">
            <StarIcon width={12} height={12} className="star" />
            {rating.toFixed(1)} <span className="rating-count">({rating_count})</span>
          </span>
        )}
        <div className="product-footer">
          <span className="price">${price.toFixed(2)}</span>
          <button
            className={`add-btn${inCart ? ' added' : ''}`}
            onClick={() => onAdd(product)}
            disabled={disabled}
            title={inCart ? 'Add another' : 'Add to cart'}
          >
            {inCart ? <CheckIcon width={14} height={14} /> : <PlusIcon width={14} height={14} />}
            {inCart ? 'Added' : 'Add'}
          </button>
        </div>
      </div>
    </article>
  )
}
