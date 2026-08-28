export default function ModelSelector({
  title,
  models,
  selected,
  setSelected,
}) {
  const MAX_MODELS = 4;

  const toggle = (m) => {
    if (selected.includes(m)) {
      setSelected(selected.filter((x) => x !== m));
    } else if (selected.length < MAX_MODELS) {
      setSelected([...selected, m]);
    }
  };

  const selectMax = () => {
    if (selected.length > 0) {
      setSelected([]);
    } else {
      setSelected(models.slice(0, MAX_MODELS));
    }
  };

  const atLimit = selected.length >= MAX_MODELS;

  return (
    <section className="selector">
      <div className="selectorHead">
        <h3>
          {title} ({selected.length}/{MAX_MODELS})
        </h3>

        <button
          type="button"
          className="link"
          onClick={selectMax}
        >
          {selected.length > 0 ? "Clear" : "Select 4"}
        </button>
      </div>

      <div className="modelList">
        {models.map((m) => {
          const isSelected = selected.includes(m);

          return (
            <label className="model" key={m}>
              <input
                type="checkbox"
                checked={isSelected}
                disabled={atLimit && !isSelected}
                onChange={() => toggle(m)}
              />
              <span>{m}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}