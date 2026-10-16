(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.Forge3D = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const defaults = Object.freeze({
    name: "Aegis-01 Futuristic Football Helmet",
    prompt: "A futuristic football helmet with an aerodynamic shell, smoked visor, luminous vents, and a protective titanium face cage.",
    template: "futuristic_football_helmet",
    detail: 0.72,
    shell_profile: "aero",
    visor: true,
    face_cage: true,
    luminous_vents: true,
    import_path: "",
    poly_budget: 80000,
    render_size: 720,
    colorways: [
      { name: "Ion Lime", primary: "#A6FF00", secondary: "#10151B", accent: "#E8FFF0" },
      { name: "Plasma Coral", primary: "#FF5F57", secondary: "#1B1024", accent: "#FFB347" },
      { name: "Glacier", primary: "#D8F7FF", secondary: "#16344A", accent: "#51D6FF" },
    ],
  });

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, Number(value)));
  }

  function isHex(value) {
    return /^#[0-9a-f]{6}$/i.test(String(value));
  }

  function normalizeRecipe(value) {
    const recipe = Object.assign(clone(defaults), value || {});
    recipe.name = String(recipe.name || defaults.name).slice(0, 100);
    recipe.prompt = String(recipe.prompt || "").slice(0, 2000);
    recipe.template = "futuristic_football_helmet";
    recipe.detail = clamp(recipe.detail, 0.2, 1);
    recipe.poly_budget = Math.round(clamp(recipe.poly_budget, 1000, 500000));
    recipe.render_size = Math.round(clamp(recipe.render_size, 256, 2048));
    recipe.visor = Boolean(recipe.visor);
    recipe.face_cage = Boolean(recipe.face_cage);
    recipe.luminous_vents = Boolean(recipe.luminous_vents);
    recipe.import_path = String(recipe.import_path || "").slice(0, 1000);
    recipe.colorways = (Array.isArray(recipe.colorways) ? recipe.colorways : defaults.colorways)
      .slice(0, 6)
      .map((colorway, index) => ({
        name: String(colorway.name || `Colorway ${index + 1}`).slice(0, 40),
        primary: isHex(colorway.primary) ? colorway.primary.toUpperCase() : defaults.colorways[index % 3].primary,
        secondary: isHex(colorway.secondary) ? colorway.secondary.toUpperCase() : defaults.colorways[index % 3].secondary,
        accent: isHex(colorway.accent) ? colorway.accent.toUpperCase() : defaults.colorways[index % 3].accent,
      }));
    if (!recipe.colorways.length) recipe.colorways = clone(defaults.colorways);
    return recipe;
  }

  function recipeFromPrompt(prompt, current) {
    const recipe = normalizeRecipe(Object.assign({}, current, { prompt }));
    const text = String(prompt).toLowerCase();
    if (/low[ -]?poly|mobile|lightweight/.test(text)) {
      recipe.detail = 0.42;
      recipe.poly_budget = 35000;
    }
    if (/high detail|cinematic|hero asset/.test(text)) {
      recipe.detail = 0.94;
      recipe.poly_budget = 140000;
    }
    if (/no visor|open face/.test(text)) recipe.visor = false;
    if (/no cage|without (a )?cage/.test(text)) recipe.face_cage = false;
    if (/no glow|no lights|unlit/.test(text)) recipe.luminous_vents = false;
    if (/stealth|matte black|obsidian/.test(text)) {
      recipe.shell_profile = "stealth";
      recipe.colorways[0] = { name: "Night Ops", primary: "#252B31", secondary: "#07090C", accent: "#A6FF00" };
    }
    if (/glacier|ice|arctic|frost/.test(text)) {
      recipe.shell_profile = "aero";
      recipe.colorways[0] = { name: "Glacier", primary: "#D8F7FF", secondary: "#16344A", accent: "#51D6FF" };
    }
    if (/red|coral|ember|fire/.test(text)) {
      recipe.colorways[0] = { name: "Plasma Coral", primary: "#FF5F57", secondary: "#1B1024", accent: "#FFB347" };
    }
    if (/purple|violet|ultraviolet/.test(text)) {
      recipe.colorways[0] = { name: "Ultraviolet", primary: "#875CFF", secondary: "#140D24", accent: "#F4C8FF" };
    }
    return normalizeRecipe(recipe);
  }

  function estimate(recipe) {
    const normalized = normalizeRecipe(recipe);
    let triangles = Math.round(11800 + normalized.detail * 18400);
    if (normalized.visor) triangles += 1200;
    if (normalized.face_cage) triangles += 2800;
    if (normalized.luminous_vents) triangles += 900;
    return Math.round(triangles / 100) * 100;
  }

  function audit(recipe) {
    const normalized = normalizeRecipe(recipe);
    const triangles = estimate(normalized);
    const importPath = normalized.import_path;
    const validImport = !importPath || /\.(glb|gltf|fbx|obj)$/i.test(importPath);
    return [
      { name: "Recipe schema", result: "pass", detail: "All required generator fields are valid." },
      { name: "Triangle target", result: triangles <= normalized.poly_budget ? "pass" : "warn", detail: `${triangles.toLocaleString()} estimated / ${normalized.poly_budget.toLocaleString()} target.` },
      { name: "Material set", result: "pass", detail: `${normalized.colorways.length} colorway${normalized.colorways.length === 1 ? "" : "s"} · 5 named slots.` },
      { name: "External import", result: validImport ? "pass" : "warn", detail: !importPath ? "No external mesh attached." : validImport ? "Supported model extension detected." : "Use GLB, GLTF, FBX, or OBJ." },
      { name: "Export plan", result: "pass", detail: ".blend + GLB + FBX + PNG + QA JSON." },
    ];
  }

  function embedRecipe(template, recipe) {
    const start = "# <FORGE3D_CONFIG>";
    const end = "# </FORGE3D_CONFIG>";
    const startIndex = template.indexOf(start);
    const endIndex = template.indexOf(end);
    if (startIndex < 0 || endIndex < 0 || endIndex <= startIndex) throw new Error("The Blender template is missing configuration markers.");
    const payload = JSON.stringify(normalizeRecipe(recipe), null, 2).replace(/'''/g, "\\u0027\\u0027\\u0027");
    const block = `${start}\nCONFIG = json.loads(r'''${payload}''')\n${end}`;
    return template.slice(0, startIndex) + block + template.slice(endIndex + end.length);
  }

  return { defaults: clone(defaults), normalizeRecipe, recipeFromPrompt, estimate, audit, embedRecipe };
});
