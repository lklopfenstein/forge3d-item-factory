(function () {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const core = window.Forge3D;
  let recipe = core.normalizeRecipe(core.defaults);
  let templateSource = "";
  let selectedColorway = 0;
  let yaw = -0.18;
  let targetYaw = -0.18;
  let dragging = false;
  let dragStart = 0;
  let yawStart = 0;

  const canvas = $("#helmetCanvas");
  const ctx = canvas.getContext("2d");

  function toast(message) {
    const node = $("#toast");
    node.textContent = message;
    node.classList.add("show");
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => node.classList.remove("show"), 2600);
  }

  function hexToRgb(hex) {
    const value = String(hex).replace("#", "");
    return [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16));
  }

  function rgba(hex, alpha) {
    const [r, g, b] = hexToRgb(hex);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function shade(hex, amount) {
    const [r, g, b] = hexToRgb(hex).map((value) => Math.max(0, Math.min(255, value + amount)));
    return `rgb(${r},${g},${b})`;
  }

  function path(points, close = true) {
    ctx.beginPath();
    points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    if (close) ctx.closePath();
  }

  function drawHelmet() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(320, Math.floor(rect.width));
    const height = Math.max(360, Math.floor(rect.height));
    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    ctx.translate(width / 2, height / 2 + 12);
    const scale = Math.min(width / 660, height / 560);
    ctx.scale(scale, scale);
    ctx.rotate(yaw * 0.025);

    const colorway = recipe.colorways[selectedColorway] || recipe.colorways[0];
    const flip = Math.cos(yaw);
    const side = Math.sin(yaw);
    const squash = 0.88 + Math.abs(flip) * 0.12;
    ctx.scale(squash, 1);

    // Ground halo and engineering arcs.
    const halo = ctx.createRadialGradient(0, 175, 10, 0, 175, 260);
    halo.addColorStop(0, rgba(colorway.accent, .18));
    halo.addColorStop(1, rgba(colorway.accent, 0));
    ctx.fillStyle = halo;
    ctx.beginPath(); ctx.ellipse(0, 172, 280, 86, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = rgba(colorway.accent, .16); ctx.lineWidth = 1;
    for (const radius of [190, 230, 270]) { ctx.beginPath(); ctx.arc(0, 0, radius, Math.PI * .12, Math.PI * 1.65); ctx.stroke(); }

    // Rear shell shadow.
    ctx.shadowColor = "rgba(0,0,0,.58)"; ctx.shadowBlur = 34; ctx.shadowOffsetY = 20;
    const shellGradient = ctx.createLinearGradient(-210, -190, 190, 170);
    shellGradient.addColorStop(0, shade(colorway.primary, 55));
    shellGradient.addColorStop(.38, colorway.primary);
    shellGradient.addColorStop(.78, shade(colorway.primary, -76));
    shellGradient.addColorStop(1, shade(colorway.primary, -110));
    ctx.fillStyle = shellGradient;
    ctx.strokeStyle = rgba("#FFFFFF", .28); ctx.lineWidth = 2;
    path([[-184,-20],[-166,-109],[-104,-182],[-12,-213],[91,-190],[166,-128],[204,-42],[197,48],[153,123],[92,159],[-14,165],[-106,126],[-165,60]]);
    ctx.fill(); ctx.stroke();
    ctx.shadowColor = "transparent";

    // Rear impact panel.
    const rearOffset = side * 24;
    ctx.fillStyle = colorway.secondary;
    path([[95+rearOffset,-127],[159+rearOffset,-87],[188+rearOffset,-20],[179+rearOffset,48],[125+rearOffset,61],[105+rearOffset,-14]]);
    ctx.fill();
    ctx.strokeStyle = rgba(colorway.accent,.36); ctx.stroke();

    // Face opening and visor.
    ctx.fillStyle = "#060a0e";
    path([[-152,-59],[-87,-112],[23,-129],[103,-101],[126,-55],[112,31],[72,82],[-20,94],[-111,58],[-151,15]]);
    ctx.fill();
    if (recipe.visor) {
      const visor = ctx.createLinearGradient(-120,-100,105,62);
      visor.addColorStop(0,"rgba(96,173,214,.55)"); visor.addColorStop(.34,"rgba(9,26,38,.92)"); visor.addColorStop(1,"rgba(0,4,7,.96)");
      ctx.fillStyle = visor; ctx.strokeStyle = rgba(colorway.accent,.65); ctx.lineWidth = 2;
      path([[-137,-52],[-77,-100],[23,-113],[94,-87],[106,-50],[91,8],[42,28],[-49,27],[-119,2]]);
      ctx.fill(); ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,.24)"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(-98,-63); ctx.quadraticCurveTo(-6,-116,74,-75); ctx.stroke();
    }

    // Brow and lower cheek plates.
    ctx.fillStyle = colorway.secondary;
    path([[-151,-70],[-92,-128],[29,-144],[108,-111],[122,-83],[46,-102],[-66,-93],[-128,-46]]); ctx.fill();
    path([[-152,21],[-101,54],[-75,125],[-21,151],[-76,160],[-139,109],[-170,56]]); ctx.fill();

    // Crown ridges.
    for (let i = 0; i < 5; i++) {
      const x = -55 + i * 27 + side * i * 2;
      ctx.fillStyle = i === 2 ? colorway.accent : shade(colorway.secondary, 18);
      path([[x,-202],[x+14,-207],[x+27,-183],[x+19,-168],[x+2,-173]]); ctx.fill();
    }

    // Ear module.
    const earX = -130 - side * 32;
    ctx.fillStyle = shade(colorway.secondary, 16); ctx.strokeStyle = rgba("#FFFFFF",.2); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(earX,39,55,0,Math.PI*2); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = colorway.accent; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.arc(earX,39,36,0,Math.PI*2); ctx.stroke();
    ctx.fillStyle = colorway.secondary; ctx.beginPath(); ctx.arc(earX,39,24,0,Math.PI*2); ctx.fill();

    // Glow vents.
    if (recipe.luminous_vents) {
      ctx.shadowColor = colorway.accent; ctx.shadowBlur = 14; ctx.strokeStyle = colorway.accent; ctx.lineWidth = 5; ctx.lineCap = "round";
      for (let i=0;i<3;i++) { ctx.beginPath(); ctx.moveTo(124+i*12, -50+i*28); ctx.lineTo(152+i*8,-38+i*28); ctx.stroke(); }
      ctx.shadowBlur = 0;
    }

    // Titanium face cage.
    if (recipe.face_cage) {
      ctx.strokeStyle = "#9aa6ad"; ctx.lineWidth = 10; ctx.lineCap = "round"; ctx.lineJoin = "round";
      ctx.shadowColor = "rgba(0,0,0,.7)"; ctx.shadowBlur = 8;
      ctx.beginPath(); ctx.moveTo(-140,-7); ctx.quadraticCurveTo(-194,69,-129,121); ctx.quadraticCurveTo(1,190,142,123); ctx.quadraticCurveTo(186,78,131,-3); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-137,63); ctx.quadraticCurveTo(-24,137,139,68); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-78,103); ctx.lineTo(-69,156); ctx.moveTo(78,105); ctx.lineTo(72,157); ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,.38)"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(-139,-8); ctx.quadraticCurveTo(-188,66,-126,116); ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Chin guard.
    ctx.fillStyle = colorway.secondary; ctx.strokeStyle = rgba(colorway.accent,.5); ctx.lineWidth = 2;
    path([[-72,132],[-39,113],[45,113],[78,137],[61,175],[-55,175]]); ctx.fill(); ctx.stroke();

    // Technical callouts.
    ctx.strokeStyle = rgba(colorway.accent,.45); ctx.fillStyle = colorway.accent; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(184,-110); ctx.lineTo(240,-148); ctx.lineTo(285,-148); ctx.stroke();
    ctx.font = "700 10px ui-monospace, monospace"; ctx.fillText("IMPACT SHELL", 244, -153);
    ctx.beginPath(); ctx.moveTo(-178,92); ctx.lineTo(-239,126); ctx.lineTo(-286,126); ctx.stroke();
    ctx.textAlign = "right"; ctx.fillText("AIR CHANNEL", -244, 121); ctx.textAlign = "left";

    ctx.restore();
  }

  function updateControlsFromRecipe() {
    $("#itemPrompt").value = recipe.prompt;
    $("#detailRange").value = Math.round(recipe.detail * 100);
    $("#detailValue").value = `${Math.round(recipe.detail * 100)}%`;
    $("#visorToggle").checked = recipe.visor;
    $("#cageToggle").checked = recipe.face_cage;
    $("#ventsToggle").checked = recipe.luminous_vents;
    $("#importPath").value = recipe.import_path;
    $("#profileReadout").textContent = `${recipe.shell_profile.toUpperCase()}—${Math.round(recipe.detail * 100)}`;
  }

  function readControls() {
    recipe.prompt = $("#itemPrompt").value.trim();
    recipe.detail = Number($("#detailRange").value) / 100;
    recipe.visor = $("#visorToggle").checked;
    recipe.face_cage = $("#cageToggle").checked;
    recipe.luminous_vents = $("#ventsToggle").checked;
    recipe.import_path = $("#importPath").value.trim().replace(/^"|"$/g, "");
    recipe = core.normalizeRecipe(recipe);
  }

  function renderColorways() {
    const list = $("#colorwayList");
    list.innerHTML = "";
    recipe.colorways.forEach((colorway, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `colorway${index === selectedColorway ? " active" : ""}`;
      button.style.setProperty("--swatch-primary", colorway.primary);
      button.style.setProperty("--swatch-secondary", colorway.secondary);
      button.style.setProperty("--swatch-accent", colorway.accent);
      button.setAttribute("aria-label", `Apply ${colorway.name} colorway`);
      button.innerHTML = `<span>${escapeHtml(colorway.name)}</span>`;
      button.addEventListener("click", () => { selectedColorway = index; renderAll(); });
      list.appendChild(button);
    });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }

  function generatedScript() {
    if (!templateSource) return "# Blender template is still loading…";
    return core.embedRecipe(templateSource, recipe);
  }

  function renderQA() {
    const checks = core.audit(recipe);
    const passed = checks.filter((check) => check.result === "pass").length;
    $("#qaScore").textContent = `${passed}/${checks.length}`;
    $("#qaList").innerHTML = checks.map((check) => `<li><i class="${check.result === "warn" ? "warn" : ""}">${check.result === "warn" ? "!" : "✓"}</i><div><b>${escapeHtml(check.name)}</b><span>${escapeHtml(check.detail)}</span></div></li>`).join("");
  }

  function renderAll() {
    readControls();
    updateControlsFromRecipe();
    renderColorways();
    $("#triangleMetric").textContent = core.estimate(recipe).toLocaleString();
    $("#scriptPreview").textContent = generatedScript().split("\n").slice(0, 70).join("\n") + "\n\n# … full generator included in download";
    renderQA();
    drawHelmet();
  }

  function downloadText(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function loadTemplate() {
    try {
      const response = await fetch("starter/forge3d_item_factory.py");
      if (!response.ok) throw new Error(`Template request failed (${response.status})`);
      templateSource = await response.text();
      renderAll();
    } catch (error) {
      $("#scriptPreview").textContent = `Could not load the script template: ${error.message}`;
    }
  }

  function setupTabs() {
    $$("[role=tab]").forEach((tab) => tab.addEventListener("click", () => {
      $$("[role=tab]").forEach((other) => other.setAttribute("aria-selected", "false"));
      $$(".tab-panel").forEach((panel) => { panel.hidden = true; panel.classList.remove("active"); });
      tab.setAttribute("aria-selected", "true");
      const panel = document.getElementById(tab.getAttribute("aria-controls"));
      panel.hidden = false; panel.classList.add("active");
    }));
  }

  function setupOrbit() {
    canvas.addEventListener("pointerdown", (event) => {
      dragging = true; dragStart = event.clientX; yawStart = targetYaw; canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      targetYaw = Math.max(-1.28, Math.min(1.28, yawStart + (event.clientX - dragStart) / 240));
    });
    canvas.addEventListener("pointerup", () => { dragging = false; });
    function animate() {
      if (Math.abs(targetYaw - yaw) > .001) { yaw += (targetYaw - yaw) * .12; drawHelmet(); }
      requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
    $$("[data-view]").forEach((button) => button.addEventListener("click", () => {
      $$("[data-view]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      targetYaw = { front: 0, side: 1.22, iso: -.18 }[button.dataset.view];
    }));
  }

  async function checkLocalBridge() {
    const button = $("#localBuildButton");
    const status = $("#localStatus");
    if (!/^(127\.0\.0\.1|localhost)$/.test(location.hostname)) {
      button.disabled = true;
      button.title = "Available after launching the downloaded Windows kit";
      return false;
    }
    try {
      const response = await fetch("/api/health");
      const health = await response.json();
      if (health.blender_found) {
        status.className = "local-status ready";
        status.textContent = "Local Blender detected. Builds remain on this PC.";
        button.disabled = false;
        return true;
      }
      status.className = "local-status error";
      status.textContent = "Local runner is active, but Blender was not found. Install Blender or set FORGE3D_BLENDER.";
    } catch (error) {
      status.textContent = "Local runner unavailable. Download and start the Windows kit.";
    }
    button.disabled = true;
    return false;
  }

  async function buildLocally() {
    readControls();
    const button = $("#localBuildButton");
    const status = $("#localStatus");
    const links = $("#artifactLinks");
    button.disabled = true; links.innerHTML = "";
    status.className = "local-status ready"; status.textContent = "Queuing Blender background build…";
    try {
      const response = await fetch("/api/build", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(recipe) });
      const job = await response.json();
      if (!response.ok) throw new Error(job.error || "Build request failed");
      let snapshot = job;
      while (["queued", "running"].includes(snapshot.status)) {
        status.textContent = snapshot.status === "queued" ? "Build queued…" : "Blender is generating geometry, previews, QA, GLB, and FBX…";
        await new Promise((resolve) => setTimeout(resolve, 1600));
        const poll = await fetch(`/api/jobs/${job.id}`);
        snapshot = await poll.json();
      }
      if (snapshot.status !== "complete") throw new Error(snapshot.error || `Blender exited with code ${snapshot.return_code}. Open blender.log for details.`);
      status.textContent = "Build complete. Download the artifacts below.";
      links.innerHTML = snapshot.files.filter((file) => /\.(blend|glb|fbx|png|json|log)$/i.test(file)).map((file) => `<a href="/artifacts/${job.id}/${encodeURI(file)}" download>${escapeHtml(file.split("/").pop())}</a>`).join("");
      toast("Local Blender build complete");
    } catch (error) {
      status.className = "local-status error"; status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  function setupEvents() {
    $("#generateButton").addEventListener("click", () => {
      readControls();
      recipe = core.recipeFromPrompt(recipe.prompt, recipe);
      selectedColorway = 0;
      updateControlsFromRecipe();
      renderAll();
      toast("Recipe regenerated from your brief");
    });
    $$("[data-prompt]").forEach((button) => button.addEventListener("click", () => {
      const field = $("#itemPrompt"); field.value = `${field.value.replace(/[.\s]+$/, "")}, ${button.dataset.prompt}.`; field.focus();
    }));
    ["#detailRange", "#visorToggle", "#cageToggle", "#ventsToggle"].forEach((selector) => $(selector).addEventListener("input", renderAll));
    $("#importPath").addEventListener("change", renderAll);
    $("#addColorway").addEventListener("click", () => {
      if (recipe.colorways.length >= 6) return toast("Six colorways is the current render limit");
      const index = recipe.colorways.length;
      const additions = [
        { name: "Ultraviolet", primary: "#875CFF", secondary: "#140D24", accent: "#F4C8FF" },
        { name: "Solar", primary: "#FFB000", secondary: "#241300", accent: "#FFF4C2" },
        { name: "Signal", primary: "#FF2B52", secondary: "#151018", accent: "#65F9FF" },
      ];
      recipe.colorways.push(additions[index % additions.length]); selectedColorway = recipe.colorways.length - 1; renderAll();
    });
    $("#downloadScript").addEventListener("click", () => {
      if (!templateSource) return toast("The script template is still loading");
      downloadText("forge3d_helmet.py", generatedScript(), "text/x-python"); toast("Editable Blender script downloaded");
    });
    $("#downloadRecipe").addEventListener("click", () => { readControls(); downloadText("forge3d_helmet_recipe.json", JSON.stringify(recipe, null, 2), "application/json"); toast("Recipe downloaded"); });
    $("#copyScript").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(generatedScript()); toast("Full script copied"); } catch (error) { toast("Clipboard access was blocked; use Download instead"); }
    });
    $("#localBuildButton").addEventListener("click", buildLocally);
    window.addEventListener("resize", drawHelmet);
  }

  setupTabs(); setupOrbit(); setupEvents(); updateControlsFromRecipe(); renderAll(); loadTemplate(); checkLocalBridge();
})();
