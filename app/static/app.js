const KB_ROWS = [
  ["ә", "ө", "ҡ", "ғ", "ҫ", "ҙ", "һ", "ң", "ү"],
  ["ё", "й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ"],
  ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
  ["DEL", "я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "ENTER"],
];

const MAX_ATTEMPTS = 6;
const WORD_LENGTH = 5;
const PRIORITY = { correct: 3, present: 2, absent: 1 };
const ACHIEVEMENTS = [
  { key: "streak_3",   img: "/assets/3_days.png",  label: "3 көн рәттән", desc: "3 көн рәттән дөрөҫ яуап бир" },
  { key: "streak_5",   img: "/assets/5_days.png",  label: "5 көн рәттән", desc: "5 көн рәттән дөрөҫ яуап бир" },
  { key: "streak_10",  img: "/assets/10_days.png", label: "10 көн рәттән", desc: "10 көн рәттән дөрөҫ яуап бир" },
  { key: "streak_25",  img: "/assets/25_days.png", label: "25 көн рәттән", desc: "25 көн рәттән дөрөҫ яуап бир" },
  { key: "streak_50",  img: "/assets/50_days.png", label: "50 көн рәттән", desc: "50 көн рәттән дөрөҫ яуап бир" },
  { key: "first_today", img: "/assets/faster.png", label: "Иң тиҙ", desc: "Иң беренсе булып яуап бир" },
  { key: "tried_30",   img: "/assets/tried.png",   label: "Тәжрибәле", desc: "30 тапҡыр үҙеңде һынап ҡара" },
];

const PWA_DISMISSED_UNTIL_KEY = "pwa_install_dismissed_until";
const PWA_INSTALLED_KEY = "pwa_install_installed";
const PWA_PROMPT_SEEN_KEY = "pwa_install_prompt_seen";
const PWA_REMIND_DELAY_MS = 7 * 24 * 60 * 60 * 1000;

let board = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(""));
let results = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(null));
let keyStates = {};
let currentRow = 0;
let currentCol = 0;
let gameStatus = "in_progress";
let dayAvailable = true;
let isSubmitting = false;
let activeState = null;
let deferredInstallPrompt = null;
let waitInstallUntilHelpClosed = false;

function decodeMask(mask) {
  return mask.split("").map((ch) => {
    if (ch === "C") return "correct";
    if (ch === "P") return "present";
    return "absent";
  });
}

function keyBg(state) {
  if (state === "correct") return "#166534";
  if (state === "present") return "#854d0e";
  if (state === "absent") return "#111118";
  return "#252836";
}

function keyBorder(state) {
  if (state === "correct") return "1px solid #22c55e";
  if (state === "present") return "1px solid #eab308";
  return "1px solid transparent";
}

function keyColor(state) {
  if (state === "absent") return "#555";
  return "#e8e6e3";
}

function showToast(msg) {
  const c = document.getElementById("toast-container");
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 2000);
}

function isStandaloneMode() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function isIosSafari() {
  const ua = window.navigator.userAgent.toLowerCase();
  const isIOS =
    /iphone|ipad|ipod/.test(ua) ||
    (window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1);
  const isSafari = /safari/.test(ua) && !/crios|fxios|edgios|opios/.test(ua);
  return isIOS && isSafari;
}

function getDismissedUntilMs() {
  const raw = window.localStorage.getItem(PWA_DISMISSED_UNTIL_KEY);
  const parsed = Number(raw || 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function isInstallDismissed() {
  return Date.now() < getDismissedUntilMs();
}

function markInstallDismissed() {
  const until = Date.now() + PWA_REMIND_DELAY_MS;
  window.localStorage.setItem(PWA_DISMISSED_UNTIL_KEY, String(until));
}

function isInstallCompleted() {
  return window.localStorage.getItem(PWA_INSTALLED_KEY) === "1";
}

function hideInstallBanner() {
  const banner = document.getElementById("pwaInstallBanner");
  if (!banner) return;
  banner.classList.remove("open");
}

function setInstallBannerMode({ iosFallback }) {
  const text = document.getElementById("installBannerText");
  const installBtn = document.getElementById("installBannerInstall");

  if (iosFallback) {
    text.textContent =
      "Safari менюнан Бүлешеүҙе баҫығыҙ ҙа, \"Баш экранға өҫтәргә\" тигәнде һайлағыҙ.";
    installBtn.style.display = "none";
    return;
  }

  text.textContent = "Һүҙлене айырым ҡушымта итеп асығыҙ, эҙләп йөрөмәгеҙ.";
  installBtn.style.display = "";
}

function shouldShowInstallPrompt() {
  if (waitInstallUntilHelpClosed) return false;
  if (isStandaloneMode()) return false;
  if (isInstallCompleted()) return false;
  if (isInstallDismissed()) return false;
  return true;
}

function maybeShowInstallBanner() {
  const banner = document.getElementById("pwaInstallBanner");
  if (!banner || !shouldShowInstallPrompt()) return;

  const iosFallback = isIosSafari();
  const nativePromptAvailable = Boolean(deferredInstallPrompt);
  if (!iosFallback && !nativePromptAvailable) return;

  setInstallBannerMode({ iosFallback });
  banner.classList.add("open");
  window.localStorage.setItem(PWA_PROMPT_SEEN_KEY, "1");
}

function buildBoard() {
  const boardEl = document.getElementById("board");
  boardEl.innerHTML = "";
  for (let r = 0; r < MAX_ATTEMPTS; r += 1) {
    const row = document.createElement("div");
    row.className = "row";
    row.id = `row-${r}`;
    for (let c = 0; c < WORD_LENGTH; c += 1) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.id = `tile-${r}-${c}`;
      row.appendChild(tile);
    }
    boardEl.appendChild(row);
  }
}

function buildKeyboard() {
  const kb = document.getElementById("keyboard");
  kb.innerHTML = "";
  KB_ROWS.forEach((row) => {
    const rowEl = document.createElement("div");
    rowEl.className = "kb-row";
    row.forEach((key) => {
      const btn = document.createElement("button");
      btn.className = `key${key === "DEL" || key === "ENTER" ? " wide" : ""}`;
      btn.dataset.key = key;
      btn.textContent = key === "DEL" ? "←" : key === "ENTER" ? "ЕБӘРЕҮ" : key;
      btn.onclick = () => handleKey(key);
      rowEl.appendChild(btn);
    });
    kb.appendChild(rowEl);
  });
}

function refreshBoard() {
  for (let r = 0; r < MAX_ATTEMPTS; r += 1) {
    for (let c = 0; c < WORD_LENGTH; c += 1) {
      const tile = document.getElementById(`tile-${r}-${c}`);
      const letter = board[r][c] || "";
      const st = results[r][c];
      tile.textContent = letter;
      tile.className = "tile";
      if (letter) tile.classList.add("filled");
      if (st) tile.classList.add(st);
    }
  }
}

function updateKeyStatesFromBoard() {
  keyStates = {};
  for (let r = 0; r < MAX_ATTEMPTS; r += 1) {
    for (let c = 0; c < WORD_LENGTH; c += 1) {
      const letter = board[r][c];
      const st = results[r][c];
      if (!letter || !st) continue;
      const current = keyStates[letter];
      if (!current || PRIORITY[st] > PRIORITY[current]) {
        keyStates[letter] = st;
      }
    }
  }

  document.querySelectorAll(".key").forEach((keyEl) => {
    const key = keyEl.dataset.key;
    if (!key || key === "DEL" || key === "ENTER") return;
    const st = keyStates[key];
    keyEl.style.background = keyBg(st);
    keyEl.style.border = keyBorder(st);
    keyEl.style.color = keyColor(st);
  });
}

function shakeCurrentRow() {
  const row = document.getElementById(`row-${currentRow}`);
  row.classList.add("shake");
  setTimeout(() => row.classList.remove("shake"), 500);
}

function setUnavailable(visible) {
  const box = document.getElementById("dayUnavailable");
  box.style.display = visible ? "block" : "none";
}

function renderTotals(totals) {
  const box = document.getElementById("totalsBox");
  box.innerHTML = [
    { n: totals.guesses_total, l: "Индерелгән һүҙ" },
    { n: totals.played_total, l: "Бөтә уйын" },
    { n: totals.wins_total, l: "Бөтә еңеү" },
  ]
    .map(
      (item) =>
        `<div class="kv-item"><div class="num">${item.n}</div><div class="lbl">${item.l}</div></div>`
    )
    .join("");

  document.getElementById("statYourPlayed").textContent = String(totals.your_played);
  document.getElementById("statYourWins").textContent = String(totals.your_wins);
}

function formatDuration(seconds) {
  if (seconds == null) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}с ${m}м ${s}с`;
  if (m > 0) return `${m}м ${s}с`;
  return `${s}с`;
}

function renderLeaderboard(items) {
  const box = document.getElementById("leaderboardBox");
  if (!items.length) {
    box.innerHTML = '<div class="list-item"><div class="row2">Еңеүселәр юҡ әле.</div></div>';
    return;
  }
  box.innerHTML = items
    .map(
      (item) =>
        `<div class="list-item"><div class="row1"><strong>#${item.place} ${item.player_label}</strong><span>${formatDuration(item.win_elapsed_seconds)}</span></div><div class="row2">Ынтылыш: ${item.attempts_used}</div></div>`
    )
    .join("");
}

function renderHistory(items) {
  const box = document.getElementById("historyBox");
  if (!items.length) {
    box.innerHTML = '<div class="list-item"><div class="row2">Әлегә тарих юҡ.</div></div>';
    return;
  }
  box.innerHTML = "";
  items.forEach((item) => {
    const statusLabel =
      item.user_status === "won"
        ? "Еңде"
        : item.user_status === "lost"
        ? "Еңелдe"
        : "Уйналманы";
    const el = document.createElement("div");
    el.className = "list-item" + (item.user_status !== "not_played" ? " clickable" : "");
    el.innerHTML = `<div class="row1"><strong>${item.day}</strong><span class="badge ${item.user_status}">${statusLabel}</span></div><div class="row2"><strong>${item.word.toUpperCase()}</strong> — ${item.description}</div>`;
    if (item.user_status !== "not_played" && item.guesses && item.guesses.length) {
      el.onclick = () => openHistoryDetail(item);
    }
    box.appendChild(el);
  });
}

function openHistoryDetail(item) {
  const titleEl = document.getElementById("historyDetailTitle");
  const wordEl = document.getElementById("historyDetailWord");
  const descEl = document.getElementById("historyDetailDesc");
  const boardEl = document.getElementById("historyDetailBoard");
  const placeEl = document.getElementById("historyDetailPlace");
  const attemptsEl = document.getElementById("historyDetailAttempts");
  const shareLinkBox = document.getElementById("historyShareLinkBox");

  titleEl.textContent = item.user_status === "won" ? "🎉 Еңеү!" : "Еңелеү";
  wordEl.textContent = item.word.toUpperCase();
  descEl.textContent = item.description;
  placeEl.textContent = item.place != null ? `#${item.place}` : "-";
  attemptsEl.textContent = item.attempts_used != null ? String(item.attempts_used) : "-";
  shareLinkBox.innerHTML = "";

  // Build mini board
  boardEl.innerHTML = "";
  for (let r = 0; r < MAX_ATTEMPTS; r++) {
    const row = document.createElement("div");
    row.className = "history-row";
    const guess = item.guesses[r];
    for (let c = 0; c < WORD_LENGTH; c++) {
      const tile = document.createElement("div");
      tile.className = "history-tile";
      if (guess) {
        tile.textContent = guess.guess_word[c].toUpperCase();
        const mask = decodeMask(guess.result_mask);
        tile.classList.add(mask[c]);
      }
      row.appendChild(tile);
    }
    boardEl.appendChild(row);
  }

  // Store for sharing
  historyDetailItem = item;

  document.getElementById("historyDetailModal").classList.add("open");
}

let historyDetailItem = null;

function drawHistoryResultImage(item) {
  if (!item || !item.guesses || !item.guesses.length) return;

  const hBoard = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(""));
  const hResults = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(null));

  item.guesses.forEach((g, idx) => {
    const letters = g.guess_word.split("");
    const mask = decodeMask(g.result_mask);
    for (let i = 0; i < WORD_LENGTH; i++) {
      hBoard[idx][i] = letters[i];
      hResults[idx][i] = mask[i];
    }
  });

  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const ctx = canvas.getContext("2d");

  const tileSize = 110;
  const gap = 16;
  const startX = (canvas.width - (WORD_LENGTH * tileSize + (WORD_LENGTH - 1) * gap)) / 2;
  const startY = 320;

  ctx.fillStyle = "#0f1117";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const grad = ctx.createLinearGradient(0, 0, canvas.width, 0);
  grad.addColorStop(0, "#22c55e");
  grad.addColorStop(1, "#60a5fa");
  ctx.fillStyle = grad;
  ctx.font = "900 88px Noto Sans";
  ctx.textAlign = "center";
  ctx.fillText("ҺҮҘЛЕ", canvas.width / 2, 140);

  ctx.fillStyle = "#8b8d97";
  ctx.font = "600 34px Noto Sans";
  ctx.fillText(item.day, canvas.width / 2, 195);

  for (let r = 0; r < MAX_ATTEMPTS; r++) {
    for (let c = 0; c < WORD_LENGTH; c++) {
      const x = startX + c * (tileSize + gap);
      const y = startY + r * (tileSize + gap);
      const letter = hBoard[r][c] || "";
      const st = hResults[r][c];

      let fill = "#1a1d27";
      let stroke = "#3a3d4a";
      if (st === "correct") { fill = "#166534"; stroke = "#22c55e"; }
      else if (st === "present") { fill = "#854d0e"; stroke = "#eab308"; }
      else if (st === "absent") { fill = "#1e2028"; stroke = "#3a3d4a"; }

      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.roundRect(x, y, tileSize, tileSize, 12);
      ctx.fill();
      ctx.stroke();

      if (letter) {
        ctx.fillStyle = "#e8e6e3";
        ctx.font = "800 52px Noto Sans";
        ctx.fillText(letter.toUpperCase(), x + tileSize / 2, y + 72);
      }
    }
  }

  ctx.fillStyle = "#e8e6e3";
  ctx.font = "700 40px Noto Sans";
  ctx.fillText("https://һүҙле.рф", canvas.width / 2, 1110);

  ctx.fillStyle = "#8b8d97";
  ctx.font = "600 28px Noto Sans";
  const placeTxt = item.place != null ? `Урын: #${item.place}` : "Урын: -";
  const elapsedTxt = item.win_elapsed_seconds != null ? `Ваҡыт: ${formatDuration(item.win_elapsed_seconds)}` : "Ваҡыт: -";
  ctx.fillText(`${placeTxt}  •  ${elapsedTxt}`, canvas.width / 2, 1160);

  const link = document.createElement("a");
  link.download = `wordle-${item.day}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

async function createHistoryShareLink(item) {
  if (!item || !item.game_id) return;
  const box = document.getElementById("historyShareLinkBox");
  box.textContent = "...";
  const res = await fetch(`/api/share/game/${item.game_id}`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Хата" }));
    box.textContent = err.detail || "Хата";
    return;
  }
  const payload = await res.json();
  box.innerHTML = `<a href="${payload.url}" target="_blank" rel="noopener">${payload.url}</a>`;
  try {
    await navigator.clipboard.writeText(payload.url);
    showToast("Һылтанма күсерелде");
  } catch (_e) {
    showToast("Һылтанма әҙер");
  }
}

function renderAchievements(achievements) {
  const row = document.getElementById("achievementsRow");
  row.innerHTML = "";
  ACHIEVEMENTS.forEach((a) => {
    const unlocked = achievements[a.key] === true;
    const img = document.createElement("img");
    img.src = a.img;
    img.alt = a.label;
    img.className = "achievement-icon" + (unlocked ? "" : " locked");
    img.onclick = () => openAchievementsModal(achievements);
    row.appendChild(img);
  });
}

function openAchievementsModal(achievements) {
  const grid = document.getElementById("achievementsGrid");
  grid.innerHTML = "";
  ACHIEVEMENTS.forEach((a) => {
    const unlocked = achievements[a.key] === true;
    const item = document.createElement("div");
    item.className = "achievement-item";
    item.innerHTML =
      `<img src="${a.img}" alt="${a.label}" class="${unlocked ? "" : "locked"}">` +
      `<div class="achievement-info">` +
        `<div class="achievement-name">${a.label}</div>` +
        `<div class="achievement-desc">${a.desc}</div>` +
      `</div>` +
      `<div class="achievement-check">${unlocked ? "✅" : "🔒"}</div>`;
    grid.appendChild(item);
  });
  document.getElementById("achievementsModal").classList.add("open");
}

function hydrateState(payload) {
  activeState = payload;
  dayAvailable = payload.day_available;
  setUnavailable(!dayAvailable);

  board = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(""));
  results = Array.from({ length: MAX_ATTEMPTS }, () => Array(WORD_LENGTH).fill(null));

  const g = payload.game_state;
  gameStatus = g.status;

  g.guesses.forEach((item, idx) => {
    const letters = item.guess_word.split("");
    const mask = decodeMask(item.result_mask);
    for (let i = 0; i < WORD_LENGTH; i += 1) {
      board[idx][i] = letters[i];
      results[idx][i] = mask[i];
    }
  });

  currentRow = g.guesses.length;
  currentCol = 0;

  if (!dayAvailable || g.status !== "in_progress") {
    currentRow = Math.min(g.guesses.length, MAX_ATTEMPTS - 1);
    currentCol = WORD_LENGTH;
  }

  refreshBoard();
  updateKeyStatesFromBoard();
  renderLeaderboard(payload.leaderboard_top);
  renderHistory(payload.history_last_10_days);
  renderTotals(payload.totals);
  if (payload.achievements) renderAchievements(payload.achievements);

  if (g.status === "won" || g.status === "lost") {
    fillEndModal(g);
  }
}

function fillEndModal(gameState) {
  document.getElementById("endTitle").textContent =
    gameState.status === "won" ? "🎉 Тәбрик!" : "Ҡыҙғаныс...";
  if (gameState.status === "lost") {
    document.getElementById("endWord").textContent = "Иртәгә дөрөҫ яуапты күрерһегеҙ";
    document.getElementById("endDesc").textContent = "Бөгөн дөрөҫ һүҙ күрһәтелмәй.";
  } else {
    document.getElementById("endWord").textContent = (gameState.answer || "").toUpperCase();
    document.getElementById("endDesc").textContent = gameState.description || "";
  }
  document.getElementById("statPlace").textContent =
    gameState.place != null ? `#${gameState.place}` : "-";
  document.getElementById("endElapsed").textContent =
    gameState.win_elapsed_seconds != null
      ? `һүҙ асылғандан һуң: ${formatDuration(gameState.win_elapsed_seconds)}`
      : "";
}

async function loadState() {
  const res = await fetch("/api/state", { credentials: "same-origin" });
  if (!res.ok) {
    showToast("Сервер хатаһы");
    return;
  }
  const payload = await res.json();
  hydrateState(payload);
}

function addLetter(letter) {
  if (currentCol >= WORD_LENGTH) return;
  board[currentRow][currentCol] = letter;
  currentCol += 1;
  refreshBoard();
}

function deleteLetter() {
  if (currentCol <= 0) return;
  currentCol -= 1;
  board[currentRow][currentCol] = "";
  refreshBoard();
}

async function submitGuess() {
  if (!dayAvailable) {
    showToast("Бөгөн һүҙ юҡ");
    return;
  }
  if (gameStatus !== "in_progress") {
    showToast("Бөгөнгө уйын тамамланған");
    return;
  }
  if (currentCol < WORD_LENGTH) {
    shakeCurrentRow();
    showToast("5 хәреф яҙығыҙ!");
    return;
  }

  const guess = board[currentRow].join("");
  isSubmitting = true;
  try {
    const res = await fetch("/api/guess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guess }),
      credentials: "same-origin",
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Хата" }));
      shakeCurrentRow();
      showToast(err.detail || "Хата");
      return;
    }

    const payload = await res.json();
    const maskStates = decodeMask(payload.guess.result_mask);

    for (let i = 0; i < WORD_LENGTH; i += 1) {
      const tile = document.getElementById(`tile-${currentRow}-${i}`);
      const delay = i * 220;
      setTimeout(() => {
        tile.classList.add("reveal");
        setTimeout(() => {
          results[currentRow][i] = maskStates[i];
          refreshBoard();
          updateKeyStatesFromBoard();
        }, 240);
      }, delay);
    }

    const endDelay = WORD_LENGTH * 220 + 380;
    setTimeout(() => {
      gameStatus = payload.game_state.status;
      renderLeaderboard(payload.leaderboard_top);
      renderTotals(payload.totals);
      if (payload.achievements) renderAchievements(payload.achievements);

      if (gameStatus === "in_progress") {
        currentRow += 1;
        currentCol = 0;
      } else {
        activeState.game_state = payload.game_state;
        fillEndModal(payload.game_state);
        document.getElementById("endModal").classList.add("open");
      }
    }, endDelay);
  } finally {
    setTimeout(() => {
      isSubmitting = false;
    }, WORD_LENGTH * 220 + 420);
  }
}

function handleKey(key) {
  if (isSubmitting) return;
  if (key === "DEL") {
    deleteLetter();
    return;
  }
  if (key === "ENTER") {
    submitGuess();
    return;
  }

  if (gameStatus !== "in_progress" || !dayAvailable) return;
  addLetter(key);
}

function attachKeyboardListener() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleKey("ENTER");
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      handleKey("DEL");
      return;
    }
    const l = e.key.toLowerCase();
    const all = KB_ROWS.flat().filter((k) => k !== "DEL" && k !== "ENTER");
    if (all.includes(l)) handleKey(l);
  });
}

function setupModals() {
  const helpModal = document.getElementById("helpModal");
  const closeHelpModal = () => {
    helpModal.classList.remove("open");
    if (waitInstallUntilHelpClosed) {
      waitInstallUntilHelpClosed = false;
      maybeShowInstallBanner();
    }
  };

  document.getElementById("helpBtn").onclick = () => helpModal.classList.add("open");
  document.getElementById("closeHelp").onclick = () => closeHelpModal();
  helpModal.onclick = (e) => {
    if (e.target === e.currentTarget) closeHelpModal();
  };

  document.getElementById("newGameBtn").onclick = () => {
    document.getElementById("endModal").classList.remove("open");
  };

  document.getElementById("endModal").onclick = (e) => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove("open");
  };

  const historyDetailModal = document.getElementById("historyDetailModal");
  document.getElementById("closeHistoryDetail").onclick = () =>
    historyDetailModal.classList.remove("open");
  historyDetailModal.onclick = (e) => {
    if (e.target === e.currentTarget) historyDetailModal.classList.remove("open");
  };
  document.getElementById("historyDownloadBtn").onclick = () => {
    if (historyDetailItem) drawHistoryResultImage(historyDetailItem);
  };
  document.getElementById("historyShareBtn").onclick = () => {
    if (historyDetailItem) createHistoryShareLink(historyDetailItem);
  };

  const achievementsModal = document.getElementById("achievementsModal");
  document.getElementById("closeAchievements").onclick = () =>
    achievementsModal.classList.remove("open");
  achievementsModal.onclick = (e) => {
    if (e.target === e.currentTarget) achievementsModal.classList.remove("open");
  };

  if (!localStorage.getItem("bashWordle_visited")) {
    waitInstallUntilHelpClosed = true;
    helpModal.classList.add("open");
    localStorage.setItem("bashWordle_visited", "1");
  } else {
    maybeShowInstallBanner();
  }
}

async function createShareLink() {
  const box = document.getElementById("shareLinkBox");
  box.textContent = "...";
  const res = await fetch("/api/share", {
    method: "POST",
    credentials: "same-origin",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Хата" }));
    box.textContent = err.detail || "Хата";
    return;
  }
  const payload = await res.json();
  box.innerHTML = `<a href="${payload.url}" target="_blank" rel="noopener">${payload.url}</a>`;
  try {
    await navigator.clipboard.writeText(payload.url);
    showToast("Һылтанма күсерелде");
  } catch (_e) {
    showToast("Һылтанма әҙер");
  }
}

function drawResultImage() {
  if (!activeState || !activeState.game_state) return;
  const g = activeState.game_state;
  if (g.status !== "won" && g.status !== "lost") {
    showToast("Файл тик тамамланған уйын өсөн");
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const ctx = canvas.getContext("2d");

  const tileSize = 110;
  const gap = 16;
  const startX = (canvas.width - (WORD_LENGTH * tileSize + (WORD_LENGTH - 1) * gap)) / 2;
  const startY = 320;

  ctx.fillStyle = "#0f1117";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const grad = ctx.createLinearGradient(0, 0, canvas.width, 0);
  grad.addColorStop(0, "#22c55e");
  grad.addColorStop(1, "#60a5fa");
  ctx.fillStyle = grad;
  ctx.font = "900 88px Noto Sans";
  ctx.textAlign = "center";
  ctx.fillText("ҺҮҘЛЕ", canvas.width / 2, 140);

  ctx.fillStyle = "#8b8d97";
  ctx.font = "600 34px Noto Sans";
  ctx.fillText(activeState.today, canvas.width / 2, 195);

  for (let r = 0; r < MAX_ATTEMPTS; r += 1) {
    for (let c = 0; c < WORD_LENGTH; c += 1) {
      const x = startX + c * (tileSize + gap);
      const y = startY + r * (tileSize + gap);
      const letter = board[r][c] || "";
      const st = results[r][c];

      let fill = "#1a1d27";
      let stroke = "#3a3d4a";
      if (st === "correct") {
        fill = "#166534";
        stroke = "#22c55e";
      } else if (st === "present") {
        fill = "#854d0e";
        stroke = "#eab308";
      } else if (st === "absent") {
        fill = "#1e2028";
        stroke = "#3a3d4a";
      }

      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.roundRect(x, y, tileSize, tileSize, 12);
      ctx.fill();
      ctx.stroke();

      if (letter) {
        ctx.fillStyle = "#e8e6e3";
        ctx.font = "800 52px Noto Sans";
        ctx.fillText(letter.toUpperCase(), x + tileSize / 2, y + 72);
      }
    }
  }

  ctx.fillStyle = "#e8e6e3";
  ctx.font = "700 40px Noto Sans";
  ctx.fillText("https://һүҙле.рф", canvas.width / 2, 1110);

  ctx.fillStyle = "#8b8d97";
  ctx.font = "600 28px Noto Sans";
  const placeTxt = g.place != null ? `Урын: #${g.place}` : "Урын: -";
  const elapsedTxt =
    g.win_elapsed_seconds != null
      ? `Ваҡыт: ${formatDuration(g.win_elapsed_seconds)}`
      : "Ваҡыт: -";
  ctx.fillText(`${placeTxt}  •  ${elapsedTxt}`, canvas.width / 2, 1160);

  const link = document.createElement("a");
  link.download = `wordle-${activeState.today}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function setupActions() {
  document.getElementById("shareResultBtn").onclick = () => {
    createShareLink();
  };
  document.getElementById("downloadResultBtn").onclick = () => {
    drawResultImage();
  };
}

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  try {
    await navigator.serviceWorker.register("/sw.js");
  } catch (_e) {
    // PWA is optional; failure should not block gameplay.
  }
}

function setupInstallFlow() {
  const installBtn = document.getElementById("installBannerInstall");
  const laterBtn = document.getElementById("installBannerLater");
  const closeBtn = document.getElementById("installBannerClose");

  const dismissInstallBanner = () => {
    markInstallDismissed();
    hideInstallBanner();
  };

  installBtn.onclick = async () => {
    const installPrompt = deferredInstallPrompt;
    if (!installPrompt) {
      hideInstallBanner();
      return;
    }

    try {
      await installPrompt.prompt();
      const result = await installPrompt.userChoice;
      if (result && result.outcome !== "accepted") {
        markInstallDismissed();
      }
    } catch (_e) {
      markInstallDismissed();
    } finally {
      deferredInstallPrompt = null;
      hideInstallBanner();
    }
  };

  laterBtn.onclick = () => dismissInstallBanner();
  closeBtn.onclick = () => dismissInstallBanner();

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    maybeShowInstallBanner();
  });

  window.addEventListener("appinstalled", () => {
    window.localStorage.setItem(PWA_INSTALLED_KEY, "1");
    deferredInstallPrompt = null;
    hideInstallBanner();
  });
}

registerServiceWorker();
buildBoard();
buildKeyboard();
setupInstallFlow();
setupModals();
setupActions();
attachKeyboardListener();
loadState();
