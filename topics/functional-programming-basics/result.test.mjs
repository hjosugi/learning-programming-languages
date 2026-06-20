import assert from "node:assert/strict";
import {
  addTag,
  flatMap,
  map,
  ok,
  optionFromNullable,
  parsePositiveInt,
  priceLine,
} from "./result.mjs";

assert.deepEqual(parsePositiveInt("3"), ok(3));
assert.equal(parsePositiveInt("0").error, "not positive");
assert.equal(parsePositiveInt("abc").error, "not an integer");

assert.deepEqual(map(ok(2), (value) => value * 3), ok(6));
assert.deepEqual(flatMap(ok("5"), parsePositiveInt), ok(5));

assert.deepEqual(optionFromNullable(null), { kind: "none" });
assert.deepEqual(optionFromNullable("x"), { kind: "some", value: "x" });

assert.deepEqual(priceLine("4", 125), ok({
  quantity: 4,
  unitPriceCents: 125,
  subtotalCents: 500,
}));

const original = { id: "u1", tags: ["fp"] };
const updated = addTag(original, "ddd");
assert.deepEqual(original, { id: "u1", tags: ["fp"] });
assert.deepEqual(updated, { id: "u1", tags: ["fp", "ddd"] });

console.log("ok");
