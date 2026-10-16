"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const core = require("../dist/generator-core.js");

const recipe = core.recipeFromPrompt(
  "A low-poly stealth black futuristic football helmet with no visor and no glow",
  core.defaults,
);

assert.equal(recipe.template, "futuristic_football_helmet");
assert.equal(recipe.detail, 0.42);
assert.equal(recipe.visor, false);
assert.equal(recipe.luminous_vents, false);
assert.equal(recipe.colorways[0].name, "Night Ops");
assert.ok(core.estimate(recipe) < core.estimate(core.defaults));

const audit = core.audit({ ...recipe, import_path: "C:\\models\\helmet.zip" });
assert.equal(audit.length, 5);
assert.equal(audit.find((check) => check.name === "External import").result, "warn");

const template = fs.readFileSync(path.join(__dirname, "../blender/forge3d_item_factory.py"), "utf8");
const embedded = core.embedRecipe(template, recipe);
assert.match(embedded, /CONFIG = json\.loads/);
assert.match(embedded, /Night Ops/);
assert.match(embedded, /"visor": false/);
assert.equal((embedded.match(/<FORGE3D_CONFIG>/g) || []).length, 1);

console.log("Forge3D generator tests passed.");
