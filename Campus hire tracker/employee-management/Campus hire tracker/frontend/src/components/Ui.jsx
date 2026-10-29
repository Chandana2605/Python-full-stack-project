export function SectionCard({ title, subtitle, actions, children }) {
  const hasHeader = title || subtitle || actions;

  return (
    <section className="section-card">
      {hasHeader ? (
        <div className="section-card__header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {actions ? <div className="section-card__actions">{actions}</div> : null}
        </div>
      ) : null}
      <div className="section-card__body">{children}</div>
    </section>
  );
}

export function MetricCard({ label, value, tone = "default", hint }) {
  return (
    <div className={`metric metric--${tone}`}>
      <div className="metric__label">{label}</div>
      <div className="metric__value">{value}</div>
      {hint ? <div className="metric__hint">{hint}</div> : null}
    </div>
  );
}

export function StatusBadge({ children, tone = "neutral" }) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <div className="empty-state__title">{title}</div>
      <div className="empty-state__description">{description}</div>
    </div>
  );
}

export function InlineAlert({ tone = "info", message }) {
  if (!message) {
    return null;
  }

  return <div className={`alert alert--${tone}`}>{message}</div>;
}

export function SegmentedTabs({ items, value, onChange }) {
  return (
    <div className="segmented-tabs" role="tablist" aria-label="Workspace sections">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          role="tab"
          aria-selected={value === item.value}
          className={`segmented-tabs__item${value === item.value ? " segmented-tabs__item--active" : ""}`}
          onClick={() => onChange(item.value)}
        >
          <span>{item.label}</span>
          {item.caption ? <small>{item.caption}</small> : null}
        </button>
      ))}
    </div>
  );
}

export function KeyValueList({ items }) {
  return (
    <div className="key-value-list">
      {items.map((item) => (
        <div className="key-value-list__item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function LoadingState({ label = "Loading data..." }) {
  return <div className="loading-state">{label}</div>;
}

export function SectionIntro({ eyebrow, title, description, actions }) {
  return (
    <div className="section-intro">
      <div>
        {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="section-intro__actions">{actions}</div> : null}
    </div>
  );
}

export function ContextBar({ items }) {
  return (
    <div className="context-bar">
      {items.map((item) => (
        <div className="context-bar__item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}
