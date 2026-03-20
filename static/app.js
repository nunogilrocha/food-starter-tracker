// ── State ──────────────────────────────────────────────────────────────────
let weeks      = [];
let foodGroups = [];
let currentTab = "calendar";
const TAB_IDS   = ["calendar", "groups", "foodlist"];

// ── API ────────────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  return res.json();
}

// ── Boot ───────────────────────────────────────────────────────────────────
async function boot() {
  [foodGroups, weeks] = await Promise.all([
    api("GET", "/api/food_groups"),
    api("GET", "/api/weeks"),
  ]);
  bindModals();
  initTabs();
  switchTab(window.INITIAL_TAB || "calendar");
}

// ══════════════════════════════════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════════════════════════════════

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(name) {
  currentTab = name;

  // slide pill
  const btn  = document.querySelector(`[data-tab="${name}"]`);
  const pill = document.getElementById("tab-pill");
  pill.style.left  = btn.offsetLeft + "px";
  pill.style.width = btn.offsetWidth + "px";

  // text colours
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("text-stone-900", b.dataset.tab === name);
    b.classList.toggle("text-stone-400", b.dataset.tab !== name);
  });

  // panels — toggle Tailwind's hidden class (not the HTML attribute)
  TAB_IDS.forEach(t => {
    document.getElementById(`panel-${t}`).classList.toggle("hidden", t !== name);
  });

  // render
  if      (name === "calendar") renderCalendar();
  else if (name === "groups")   renderGroups();
  else                          renderFoodList();
}

// ══════════════════════════════════════════════════════════════════════════
// CALENDAR TAB
// ══════════════════════════════════════════════════════════════════════════

function renderCalendar() {
  const container = document.getElementById("panel-calendar");
  container.innerHTML = "";
  weeks.forEach(week => container.appendChild(buildWeekCard(week)));

  // "Add week" ghost card at the end
  const addCard = div("flex items-center justify-center min-w-[200px] max-w-[220px] h-32 border-2 border-dashed border-sage-200 rounded-3xl cursor-pointer hover:border-stone-300 hover:bg-white transition-all duration-200 flex-shrink-0 group");
  const addLabel = div("flex flex-col items-center gap-1.5");
  const plus  = span("text-2xl text-stone-300 group-hover:text-stone-500 transition-colors leading-none");
  plus.textContent = "+";
  const lbl = span("text-[0.62rem] font-bold tracking-widest uppercase text-stone-300 group-hover:text-stone-500 transition-colors");
  lbl.textContent = "Add Week";
  addLabel.append(plus, lbl);
  addCard.appendChild(addLabel);
  addCard.addEventListener("click", () => openWeekModal());
  container.appendChild(addCard);
}

function buildWeekCard(week) {
  const total = week.entries.length;
  const done  = week.entries.filter(e => e.introduced).length;
  const pct   = total ? Math.round((done / total) * 100) : 0;

  const card = div("bg-white rounded-3xl shadow-sm border border-sage-100 flex flex-col min-w-[288px] max-w-[312px] overflow-hidden flex-shrink-0 group/card");
  card.dataset.weekId = week.id;

  // header
  const hdr = div("px-5 pt-5 pb-0");
  const hdrTop = div("flex items-start justify-between gap-2 mb-3");

  const hdrLeft = div("flex flex-col gap-0.5");
  const weekLbl = span("text-[0.62rem] font-bold tracking-[0.2em] uppercase text-stone-400");
  weekLbl.textContent = week.label;
  const countLbl = span("text-xs text-stone-400 font-normal mt-0.5");
  countLbl.textContent = total
    ? `${done} of ${total} introduced`
    : "No foods yet";
  hdrLeft.append(weekLbl, countLbl);

  const hdrActs = div("flex gap-0 -mr-1 -mt-1 opacity-0 group-hover/card:opacity-100 transition-opacity duration-200 reveal-actions");
  hdrActs.append(
    ghostBtn("✏", "Edit", () => openWeekModal(week)),
    ghostBtn("✕", "Delete", () => deleteWeek(week.id)),
  );
  hdrTop.append(hdrLeft, hdrActs);

  // progress bar
  const track = div("h-[2px] bg-sage-100 rounded-full overflow-hidden");
  const fill  = div("h-full rounded-full bg-stone-800 transition-all duration-500");
  fill.style.width = pct + "%";
  track.appendChild(fill);
  hdr.append(hdrTop, track);

  // body
  const body = div("px-3 pt-3 pb-3 flex flex-col gap-0");
  const activeGroups = foodGroups.filter(g => week.entries.some(e => e.group_id === g.id));

  activeGroups.forEach((group, gi) => {
    const entries = week.entries.filter(e => e.group_id === group.id);

    // group label
    const glabel = div(`flex items-center gap-2 px-2 mb-1 ${gi > 0 ? "mt-3" : "mt-1"}`);
    const dot = span("inline-block w-1.5 h-1.5 rounded-full flex-shrink-0");
    dot.style.background = group.color;
    const name = span("text-[0.58rem] font-bold tracking-[0.14em] uppercase");
    name.style.color = group.color;
    name.textContent = group.name;

    // hover-reveal "+ add" pill
    const addPill = button(`ml-auto text-[0.58rem] font-semibold px-2 py-0.5 rounded-full border opacity-0 transition-opacity cursor-pointer reveal-actions`);
    addPill.textContent = "+ add";
    addPill.style.color       = group.color;
    addPill.style.borderColor = group.color + "50";
    addPill.style.background  = group.color + "12";
    addPill.addEventListener("click", () => openEntryModal(week.id, group.id));
    glabel.addEventListener("mouseenter", () => addPill.style.opacity = "1");
    glabel.addEventListener("mouseleave", () => addPill.style.opacity = "0");

    glabel.append(dot, name, addPill);
    body.appendChild(glabel);
    entries.forEach(entry => body.appendChild(buildEntryRow(week.id, group, entry)));
  });

  // add food button
  const addBtn = button("w-full mt-3 text-[0.62rem] font-semibold tracking-[0.1em] uppercase text-stone-400 border border-dashed border-stone-200 rounded-2xl py-3 hover:border-stone-400 hover:text-stone-700 hover:bg-sage-50 transition-all duration-200 cursor-pointer");
  addBtn.textContent = "+ Add Food";
  addBtn.addEventListener("click", () => openEntryModal(week.id));
  body.appendChild(addBtn);

  card.append(hdr, body);
  return card;
}

function buildEntryRow(weekId, group, entry) {
  const row = div("flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-sage-50 transition-colors duration-150 group/row");

  const chk = document.createElement("input");
  chk.type      = "checkbox";
  chk.className = "food-check";
  chk.checked   = entry.introduced;
  chk.style.setProperty("--chk", group.color);
  chk.addEventListener("change", async () => {
    const date    = chk.checked ? isoToday() : null;
    const updated = await api("PUT", `/api/weeks/${weekId}/entries/${entry.id}`, {
      introduced: chk.checked, introduced_date: date,
    });
    entry.introduced      = updated.introduced;
    entry.introduced_date = updated.introduced_date;
    nameEl.classList.toggle("done", entry.introduced);
    refreshMeta();
  });

  const main   = div("flex flex-col gap-0.5 flex-1 min-w-0");
  const nameEl = span("food-name text-sm font-medium text-stone-700 truncate leading-snug");
  nameEl.textContent = entry.food;
  if (entry.introduced) nameEl.classList.add("done");
  main.appendChild(nameEl);

  let metaRow = null;
  function refreshMeta() {
    if (metaRow) { metaRow.remove(); metaRow = null; }
    if (!entry.introduced) return;
    metaRow = div("flex items-center gap-2 flex-wrap");
    metaRow.appendChild(buildDateChip(weekId, group, entry));
    main.appendChild(metaRow);
  }
  refreshMeta();

  const acts = div("flex gap-0 opacity-0 group-hover/row:opacity-100 transition-opacity flex-shrink-0 reveal-actions");
  acts.append(
    ghostBtn("✏", "Edit",   () => openEntryModal(weekId, group.id, entry)),
    ghostBtn("✕", "Delete", () => deleteEntry(weekId, entry.id)),
  );

  row.append(chk, main, acts);
  return row;
}

function buildDateChip(weekId, group, entry) {
  const chip = span("date-chip text-[0.6rem] font-semibold px-2 py-0.5 rounded-full cursor-pointer transition-opacity hover:opacity-70 select-none");
  chip.style.background = group.color + "18";
  chip.style.color      = group.color;
  chip.textContent      = "📅 " + formatDate(entry.introduced_date);
  chip.title            = "Click to edit date";

  chip.addEventListener("click", () => {
    const inp = document.createElement("input");
    inp.type      = "date";
    inp.value     = entry.introduced_date || isoToday();
    inp.className = "text-[0.62rem] font-semibold border border-stone-200 rounded-lg px-1.5 py-0.5 outline-none focus:border-stone-800 bg-white";
    async function commit() {
      const updated = await api("PUT", `/api/weeks/${weekId}/entries/${entry.id}`, {
        introduced_date: inp.value || null,
      });
      entry.introduced_date = updated.introduced_date;
      chip.textContent = "📅 " + formatDate(entry.introduced_date);
      inp.replaceWith(chip);
    }
    inp.addEventListener("change", commit);
    inp.addEventListener("blur",   commit);
    inp.addEventListener("keydown", e => { if (e.key === "Escape") inp.replaceWith(chip); });
    chip.replaceWith(inp);
    inp.focus();
  });
  return chip;
}

// ══════════════════════════════════════════════════════════════════════════
// GROUPS TAB
// ══════════════════════════════════════════════════════════════════════════

function renderGroups() {
  const container = document.getElementById("groups-content");
  container.innerHTML = "";

  // page header row
  const pageHdr = div("flex items-center justify-between mb-6");
  const pageTitle = div("flex flex-col gap-0.5");
  const pt1 = span("text-[0.62rem] font-bold tracking-[0.2em] uppercase text-stone-400");
  pt1.textContent = "Food Groups";
  const pt2 = span("text-xs text-stone-400");
  pt2.textContent = `${foodGroups.length} group${foodGroups.length !== 1 ? "s" : ""}`;
  pageTitle.append(pt1, pt2);

  const addBtn = button("text-[0.68rem] font-bold tracking-wider uppercase bg-stone-900 text-white px-4 py-2 rounded-full hover:bg-stone-700 transition-colors cursor-pointer");
  addBtn.textContent = "+ New Group";
  addBtn.addEventListener("click", () => openGroupModal());
  pageHdr.append(pageTitle, addBtn);
  container.appendChild(pageHdr);

  if (!foodGroups.length) {
    const empty = div("text-center py-20 flex flex-col items-center gap-3");
    const emptyIcon = div("text-4xl opacity-20");
    emptyIcon.textContent = "🥦";
    const emptyMsg = span("text-sm text-stone-400");
    emptyMsg.textContent = "No food groups yet. Create one to get started.";
    empty.append(emptyIcon, emptyMsg);
    container.appendChild(empty);
    return;
  }

  // group cards
  const cards = div("flex flex-col gap-3");
  foodGroups.forEach(group => cards.appendChild(buildGroupCard(group)));
  container.appendChild(cards);
}

function buildGroupCard(group) {
  const foods = group.foods || [];
  const allEntries = weeks.flatMap(w => w.entries.filter(e => e.group_id === group.id));
  const introduced = allEntries.filter(e => e.introduced).length;

  const card = div("bg-white rounded-2xl border border-sage-100 shadow-sm overflow-hidden group/gcard");

  // colored top strip
  const strip = div("h-1 w-full");
  strip.style.background = group.color;

  const cardBody = div("px-5 py-4 flex flex-col gap-4");

  // ── top row: swatch + name + meta + actions ──
  const topRow = div("flex items-start gap-3");

  const swatch = div("w-9 h-9 rounded-xl flex-shrink-0 mt-0.5 flex items-center justify-center");
  swatch.style.background = group.color + "20";
  swatch.style.border     = `2px solid ${group.color}40`;
  const swatchDot = div("w-3 h-3 rounded-full");
  swatchDot.style.background = group.color;
  swatch.appendChild(swatchDot);

  const nameBlock = div("flex flex-col gap-0.5 flex-1 min-w-0");
  const gName = span("text-base font-semibold text-stone-800");
  gName.textContent = group.name;

  const meta = div("flex items-center gap-2 flex-wrap");
  const countPill = span("text-[0.6rem] font-semibold px-2 py-0.5 rounded-full");
  countPill.style.background = group.color + "15";
  countPill.style.color      = group.color;
  countPill.textContent      = `${foods.length} food${foods.length !== 1 ? "s" : ""}`;

  const introPill = span("text-[0.6rem] font-semibold px-2 py-0.5 rounded-full bg-sage-100 text-stone-500");
  introPill.textContent = `${introduced} introduced`;

  meta.append(countPill, introPill);
  nameBlock.append(gName, meta);

  const acts = div("flex gap-1 opacity-0 group-hover/gcard:opacity-100 transition-opacity flex-shrink-0 reveal-actions");
  acts.append(
    ghostBtn("✏", "Edit group", () => openGroupModal(group)),
    ghostBtn("✕", "Delete group", () => deleteGroup(group.id).then(renderGroups)),
  );

  topRow.append(swatch, nameBlock, acts);
  cardBody.appendChild(topRow);

  // ── food list ──
  const foodSection = div("flex flex-col gap-1 border-t border-sage-100 pt-3");

  if (foods.length === 0) {
    const empty = span("text-xs text-stone-400 italic px-1");
    empty.textContent = "No foods yet — add one below";
    foodSection.appendChild(empty);
  } else {
    foods.forEach(food => {
      const row = div("flex items-center gap-2 px-1 py-1 rounded-lg hover:bg-sage-50 transition-colors group/frow");
      const dot = span("inline-block w-1.5 h-1.5 rounded-full flex-shrink-0");
      dot.style.background = group.color;
      const fname = span("text-sm text-stone-700 flex-1");
      fname.textContent = food.name;

      const delBtn = ghostBtn("✕", "Remove food", async () => {
        if (!confirm(`Remove "${food.name}" from ${group.name}?`)) return;
        await api("DELETE", `/api/food_groups/${group.id}/foods/${food.id}`);
        group.foods = group.foods.filter(f => f.id !== food.id);
        renderGroups();
      });
      delBtn.className += " opacity-0 group-hover/frow:opacity-100 transition-opacity reveal-actions";

      row.append(dot, fname, delBtn);
      foodSection.appendChild(row);
    });
  }

  // ── inline add-food row ──
  const addRow = div("flex items-center gap-2 mt-1");
  const inp = document.createElement("input");
  inp.type        = "text";
  inp.placeholder = "Add a food…";
  inp.className   = "flex-1 text-sm border border-sage-200 rounded-xl px-3 py-2 outline-none focus:border-stone-800 transition-colors placeholder:text-stone-300 bg-white";

  const addFoodBtn = button("text-[0.65rem] font-bold tracking-wider uppercase px-3 py-2 rounded-xl transition-colors cursor-pointer whitespace-nowrap");
  addFoodBtn.textContent = "Add";
  addFoodBtn.style.background = group.color + "18";
  addFoodBtn.style.color      = group.color;

  async function submitNewFood() {
    const name = inp.value.trim();
    if (!name) return;
    const created = await api("POST", `/api/food_groups/${group.id}/foods`, { name });
    if (!group.foods) group.foods = [];
    group.foods.push(created);
    inp.value = "";
    renderGroups();
  }
  addFoodBtn.addEventListener("click", submitNewFood);
  inp.addEventListener("keydown", e => { if (e.key === "Enter") submitNewFood(); });

  addRow.append(inp, addFoodBtn);
  foodSection.appendChild(addRow);

  cardBody.append(foodSection);
  card.append(strip, cardBody);
  return card;
}

// ══════════════════════════════════════════════════════════════════════════
// FOOD LIST TAB
// ══════════════════════════════════════════════════════════════════════════

function renderFoodList() {
  const container = document.getElementById("foodlist-content");
  container.innerHTML = "";

  // build index: group → [{entry, weekLabel}]
  const byGroup = foodGroups.map(group => {
    const foods = [];
    weeks.forEach(week => {
      week.entries
        .filter(e => e.group_id === group.id)
        .forEach(entry => foods.push({ entry, week }));
    });
    return { group, foods };
  }).filter(g => g.foods.length > 0);

  // summary bar
  const allEntries   = weeks.flatMap(w => w.entries);
  const totalFoods   = allEntries.length;
  const totalDone    = allEntries.filter(e => e.introduced).length;
  const pct          = totalFoods ? Math.round((totalDone / totalFoods) * 100) : 0;

  const summary = div("flex items-center gap-4 mb-8 flex-wrap");

  [
    { label: "Total Foods",  value: totalFoods },
    { label: "Introduced",   value: totalDone  },
    { label: "Planned",      value: totalFoods - totalDone },
  ].forEach(({ label, value }) => {
    const stat = div("flex flex-col gap-0.5");
    const v = span("text-2xl font-bold text-stone-800 leading-none");
    v.textContent = value;
    const l = span("text-[0.6rem] font-semibold tracking-widest uppercase text-stone-400 mt-1");
    l.textContent = label;
    stat.append(v, l);
    summary.appendChild(stat);

    // divider
    const sep = div("w-px h-8 bg-sage-200 self-center");
    summary.appendChild(sep);
  });

  // progress bar row
  const pbar = div("flex flex-col gap-1.5 flex-1 min-w-[140px]");
  const ptrack = div("h-1.5 bg-sage-200 rounded-full overflow-hidden");
  const pfill  = div("h-full bg-stone-800 rounded-full transition-all duration-700");
  pfill.style.width = pct + "%";
  ptrack.appendChild(pfill);
  const plbl = span("text-[0.6rem] font-semibold tracking-widest uppercase text-stone-400");
  plbl.textContent = pct + "% complete";
  pbar.append(plbl, ptrack);
  summary.appendChild(pbar);

  container.appendChild(summary);

  // groups
  byGroup.forEach(({ group, foods }) => {
    const section = div("mb-8");

    // group header
    const ghdr = div("flex items-center gap-2.5 mb-1");
    const gdot = span("inline-block w-2 h-2 rounded-full flex-shrink-0");
    gdot.style.background = group.color;
    const gname = span("text-[0.62rem] font-bold tracking-[0.16em] uppercase");
    gname.style.color = group.color;
    gname.textContent = group.name;
    const gsep  = div("flex-1 h-px bg-sage-200");
    const gcount = span("text-[0.6rem] font-semibold text-stone-400 tracking-wide");
    const gdone = foods.filter(f => f.entry.introduced).length;
    gcount.textContent = `${gdone}/${foods.length}`;
    ghdr.append(gdot, gname, gsep, gcount);

    // food rows
    const rows = div("flex flex-col");
    foods.forEach(({ entry, week }) => {
      const row = div("flex items-center gap-4 py-2.5 px-3 rounded-xl hover:bg-white transition-colors duration-150");

      // status dot
      const sdot = span("inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 mt-0.5");
      sdot.style.background = entry.introduced ? group.color : "#d4ccc8";

      // food name
      const fname = span(`text-sm font-medium ${entry.introduced ? "text-stone-400 line-through" : "text-stone-700"} flex-1 truncate`);
      fname.textContent = entry.food;

      // week pill
      const wpill = span("text-[0.6rem] font-semibold tracking-wide text-stone-400 bg-sage-100 px-2 py-0.5 rounded-full whitespace-nowrap");
      wpill.textContent = week.label;

      // status badge
      let badge;
      if (entry.introduced) {
        badge = span("text-[0.6rem] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap");
        badge.style.background = group.color + "18";
        badge.style.color      = group.color;
        badge.textContent      = "✓ " + formatDate(entry.introduced_date);
      } else {
        badge = span("text-[0.6rem] font-semibold px-2 py-0.5 rounded-full bg-sage-100 text-stone-400 whitespace-nowrap");
        badge.textContent = "Planned";
      }

      row.append(sdot, fname, wpill, badge);
      rows.appendChild(row);
    });

    section.append(ghdr, rows);
    container.appendChild(section);
  });

  if (!totalFoods) {
    const empty = div("text-center py-16 text-stone-400");
    const msg = span("text-sm");
    msg.textContent = "No foods tracked yet. Add some in the Calendar tab.";
    empty.appendChild(msg);
    container.appendChild(empty);
  }
}

// ══════════════════════════════════════════════════════════════════════════
// MODALS
// ══════════════════════════════════════════════════════════════════════════

function bindModals() {
  // Entry
  document.getElementById("btn-entry-cancel").addEventListener("click", () => closeModal("modal-entry"));
  document.getElementById("btn-entry-save").addEventListener("click", saveEntry);

  // Week
  document.getElementById("btn-week-cancel").addEventListener("click", () => closeModal("modal-week"));
  document.getElementById("btn-week-save").addEventListener("click", saveWeek);

  // Group
  document.getElementById("btn-group-cancel").addEventListener("click", () => closeModal("modal-group"));
  document.getElementById("btn-group-save").addEventListener("click", saveGroup);

  // Dismiss on backdrop
  document.querySelectorAll("[id^='modal-']").forEach(m => {
    m.addEventListener("click", e => { if (e.target === m) m.hidden = true; });
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape")
      document.querySelectorAll("[id^='modal-']").forEach(m => m.hidden = true);
  });
}

function closeModal(id) { document.getElementById(id).hidden = true; }

// ── Week modal ─────────────────────────────────────────────────────────────
function openWeekModal(week) {
  document.getElementById("modal-week-title").textContent = week ? "Edit Week" : "New Week";
  document.getElementById("week-id").value    = week ? week.id : "";
  document.getElementById("week-label").value = week ? week.label : `Week ${weeks.length + 1}`;
  document.getElementById("modal-week").hidden = false;
  setTimeout(() => document.getElementById("week-label").focus(), 50);
}
async function saveWeek() {
  const id    = document.getElementById("week-id").value;
  const label = document.getElementById("week-label").value.trim();
  if (!label) return;
  if (id) {
    const updated = await api("PUT", `/api/weeks/${id}`, { label });
    const w = weeks.find(w => w.id == id);
    if (w) w.label = updated.label;
  } else {
    const created = await api("POST", "/api/weeks", { label });
    created.entries = [];
    weeks.push(created);
  }
  closeModal("modal-week");
  renderCalendar();
}
async function deleteWeek(id) {
  if (!confirm("Delete this week and all its entries?")) return;
  await api("DELETE", `/api/weeks/${id}`);
  weeks = weeks.filter(w => w.id !== id);
  renderCalendar();
}

// ── Group modal ────────────────────────────────────────────────────────────
function openGroupModal(group) {
  document.getElementById("modal-group-title").textContent = group ? "Edit Group" : "New Group";
  document.getElementById("group-id").value    = group ? group.id : "";
  document.getElementById("group-name").value  = group ? group.name : "";
  document.getElementById("group-color").value = group ? group.color : "#868e96";
  document.getElementById("modal-group").hidden = false;
  setTimeout(() => document.getElementById("group-name").focus(), 50);
}
async function saveGroup() {
  const id    = document.getElementById("group-id").value;
  const name  = document.getElementById("group-name").value.trim();
  const color = document.getElementById("group-color").value;
  if (!name) return;
  if (id) {
    const updated = await api("PUT", `/api/food_groups/${id}`, { name, color });
    const g = foodGroups.find(g => g.id == id);
    if (g) { g.name = updated.name; g.color = updated.color; }
  } else {
    const created = await api("POST", "/api/food_groups", { name, color });
    created.foods = [];
    foodGroups.push(created);
  }
  closeModal("modal-group");
  renderGroups();
}
async function deleteGroup(id) {
  const g = foodGroups.find(g => g.id == id);
  if (!confirm(`Delete "${g?.name}" and all its entries?`)) return;
  await api("DELETE", `/api/food_groups/${id}`);
  foodGroups = foodGroups.filter(x => x.id !== id);
  weeks.forEach(w => { w.entries = w.entries.filter(e => e.group_id !== id); });
}

// ── Entry modal ────────────────────────────────────────────────────────────
function populateFoodSelect(groupId, selectedFood) {
  const foodSel = document.getElementById("entry-food-select");
  foodSel.innerHTML = "";
  const group = foodGroups.find(g => g.id == groupId);
  const foods = group?.foods || [];
  if (!foods.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No foods — add some in the Groups tab";
    opt.disabled = true;
    foodSel.appendChild(opt);
  } else {
    foods.forEach(f => {
      const opt = document.createElement("option");
      opt.value = f.name;
      opt.textContent = f.name;
      foodSel.appendChild(opt);
    });
    if (selectedFood) foodSel.value = selectedFood;
  }
}

function openEntryModal(weekId, preselectedGroupId, entry) {
  const grpSel = document.getElementById("entry-group");
  grpSel.innerHTML = "";
  foodGroups.forEach(g => {
    const opt = document.createElement("option");
    opt.value = g.id; opt.textContent = g.name;
    grpSel.appendChild(opt);
  });

  document.getElementById("modal-entry-title").textContent = entry ? "Edit Food" : "Add Food";
  document.getElementById("entry-week-id").value = weekId;
  document.getElementById("entry-id").value      = entry ? entry.id : "";

  const groupId = entry ? entry.group_id : (preselectedGroupId || foodGroups[0]?.id);
  grpSel.value = groupId;

  grpSel.onchange = () => populateFoodSelect(grpSel.value);
  populateFoodSelect(groupId, entry?.food);

  document.getElementById("modal-entry").hidden = false;
}

async function saveEntry() {
  const weekId  = document.getElementById("entry-week-id").value;
  const entryId = document.getElementById("entry-id").value;
  const food    = document.getElementById("entry-food-select").value;
  const groupId = parseInt(document.getElementById("entry-group").value);
  if (!food) return;

  const week = weeks.find(w => w.id == weekId);
  if (entryId) {
    const updated = await api("PUT", `/api/weeks/${weekId}/entries/${entryId}`, { food, group_id: groupId });
    const idx = week.entries.findIndex(e => e.id == entryId);
    if (idx >= 0) week.entries[idx] = { ...week.entries[idx], ...updated };
  } else {
    const created = await api("POST", `/api/weeks/${weekId}/entries`, { food, group_id: groupId });
    week.entries.push(created);
  }
  closeModal("modal-entry");
  if (currentTab === "calendar") renderCalendar();
  else renderFoodList();
}

async function deleteEntry(weekId, entryId) {
  await api("DELETE", `/api/weeks/${weekId}/entries/${entryId}`);
  const week = weeks.find(w => w.id == weekId);
  if (week) week.entries = week.entries.filter(e => e.id !== entryId);
  if (currentTab === "calendar") renderCalendar();
  else renderFoodList();
}

// ══════════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════════

function div(cls)    { const n = document.createElement("div");    n.className = cls; return n; }
function span(cls)   { const n = document.createElement("span");   n.className = cls; return n; }
function button(cls) { const n = document.createElement("button"); n.className = cls; return n; }

function ghostBtn(icon, title, onClick) {
  const b = button("w-7 h-7 flex items-center justify-center text-stone-400 hover:text-stone-700 hover:bg-sage-100 rounded-lg transition-colors text-xs cursor-pointer");
  b.textContent = icon; b.title = title;
  b.addEventListener("click", onClick);
  return b;
}

function isoToday() { return new Date().toISOString().split("T")[0]; }

function formatDate(iso) {
  if (!iso) return "set date";
  const [, m, d] = iso.split("-");
  return `${parseInt(d)} ${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][parseInt(m)-1]}`;
}

// ── Start ──────────────────────────────────────────────────────────────────
boot();
