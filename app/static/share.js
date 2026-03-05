function decodeMask(mask) {
  return mask.split("").map((ch) => {
    if (ch === "C") return "correct";
    if (ch === "P") return "present";
    return "absent";
  });
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

function renderGrid(guesses) {
  const rows = guesses
    .map((g) => {
      const states = decodeMask(g.result_mask);
      const letters = g.guess_word.split("");
      const cells = letters
        .map((letter, idx) => `<div class="cell ${states[idx]}">${letter}</div>`)
        .join("");
      return `<div class="row">${cells}</div>`;
    })
    .join("");

  return `<div class="grid">${rows}</div>`;
}

function statusLabel(status) {
  if (status === "won") return "Еңде";
  if (status === "lost") return "Еңелде";
  return status;
}

async function main() {
  const root = document.getElementById("shareRoot");
  const content = document.getElementById("shareContent");
  const token = root.dataset.token;

  const res = await fetch(`/api/share/${token}`, { credentials: "omit" });
  if (!res.ok) {
    content.innerHTML = '<div class="error">һылтанма табылманы йәки иҫкергән.</div>';
    return;
  }

  const data = await res.json();
  const place = data.place != null ? `#${data.place}` : "-";

  content.innerHTML = `
    <div class="small">Көн: ${data.day}</div>
    ${renderGrid(data.guesses)}
    <div class="answer"><strong>Һүҙ:</strong> ${data.word}</div>
    <div class="small">${data.description}</div>
    <div class="answer"><strong>һөҙөмтә:</strong> ${statusLabel(data.status)}</div>
    <div class="answer"><strong>Ынтылыш:</strong> ${data.attempts_used ?? "-"}</div>
    <div class="answer"><strong>Урын:</strong> ${place}</div>
    <div class="answer"><strong>Ваҡыт:</strong> ${formatDuration(data.win_elapsed_seconds)}</div>
  `;
}

main();
