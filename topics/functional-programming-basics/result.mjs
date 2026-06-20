export const ok = (value) => ({ ok: true, value });
export const err = (error) => ({ ok: false, error });

export function map(result, fn) {
  return result.ok ? ok(fn(result.value)) : result;
}

export function flatMap(result, fn) {
  return result.ok ? fn(result.value) : result;
}

export function pipe(value, ...fns) {
  return fns.reduce((current, fn) => fn(current), value);
}

export function optionFromNullable(value) {
  return value === null || value === undefined
    ? { kind: "none" }
    : { kind: "some", value };
}

export function parsePositiveInt(input) {
  const value = Number(input);
  if (!Number.isInteger(value)) {
    return err("not an integer");
  }
  if (value <= 0) {
    return err("not positive");
  }
  return ok(value);
}

export function priceLine(rawQuantity, unitPriceCents) {
  return pipe(
    parsePositiveInt(rawQuantity),
    (quantity) => map(quantity, (value) => ({
      quantity: value,
      unitPriceCents,
      subtotalCents: value * unitPriceCents,
    })),
  );
}

export function addTag(user, tag) {
  return {
    ...user,
    tags: [...user.tags, tag],
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(JSON.stringify({
    ok: priceLine("3", 250),
    error: priceLine("0", 250),
    option: optionFromNullable("value"),
    immutableUpdate: addTag({ id: "u1", tags: ["fp"] }, "ddd"),
  }, null, 2));
}
